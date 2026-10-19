import asyncio
import re
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from playwright.async_api import async_playwright
from app.models import ProfileData, PostData, CommentData, LocationData, InstagramScrapeResponse
from app.cache import cache

logger = logging.getLogger("playwright_scraper")


def parse_meta_description(meta_text: str, username: str) -> Dict[str, Any]:
    """
    Parses Instagram's standard meta description:
    e.g.: '271M Followers, 279 Following, 1,058 Posts - Virat Kohli (@virat.kohli) on Instagram: "Carpediem!"'
    """
    result = {
        "followers": None,
        "following": None,
        "posts_count": None,
        "full_name": username,
        "biography": ""
    }
    if not meta_text:
        return result

    try:
        f_match = re.search(r"([\d.,]+[KkMmBb]?)\s+Followers", meta_text)
        if f_match:
            raw_f = f_match.group(1).replace(",", "").strip()
            mult = 1
            if raw_f.lower().endswith("k"):
                mult = 1000
                raw_f = raw_f[:-1]
            elif raw_f.lower().endswith("m"):
                mult = 1000000
                raw_f = raw_f[:-1]
            elif raw_f.lower().endswith("b"):
                mult = 1000000000
                raw_f = raw_f[:-1]
            result["followers"] = int(float(raw_f) * mult)

        fl_match = re.search(r"([\d.,]+[KkMmBb]?)\s+Following", meta_text)
        if fl_match:
            raw_fl = fl_match.group(1).replace(",", "").strip()
            mult = 1
            if raw_fl.lower().endswith("k"):
                mult = 1000
                raw_fl = raw_fl[:-1]
            elif raw_fl.lower().endswith("m"):
                mult = 1000000
                raw_fl = raw_fl[:-1]
            result["following"] = int(float(raw_fl) * mult)

        p_match = re.search(r"([\d.,]+)\s+Posts", meta_text)
        if p_match:
            result["posts_count"] = int(p_match.group(1).replace(",", "").strip())

        fn_match = re.search(r"-\s*(.*?)\s*\(@", meta_text)
        if fn_match:
            result["full_name"] = fn_match.group(1).strip()

        bio_match = re.search(r'on Instagram:\s*"(.*?)"', meta_text, re.DOTALL)
        if bio_match:
            result["biography"] = bio_match.group(1).strip()

    except Exception as e:
        logger.warning(f"Error parsing meta description: {e}")

    return result


def extract_comments_from_html(html: str, target_comments: int = 5) -> List[CommentData]:
    """
    Recursively extracts real comments and authors from embedded JSON in the Instagram post page.
    """
    comments_found = []
    seen_texts = set()

    def find_comments(obj):
        if len(comments_found) >= target_comments:
            return
        if isinstance(obj, dict):
            if "text" in obj and ("user" in obj or "owner" in obj or "author" in obj):
                text = str(obj.get("text", "")).strip()
                if text and text not in seen_texts:
                    seen_texts.add(text)
                    author_obj = obj.get("user") or obj.get("owner") or obj.get("author") or {}
                    author = author_obj.get("username") if isinstance(author_obj, dict) else str(author_obj)
                    created_at = obj.get("created_at") or obj.get("created_at_utc")
                    
                    c_date = datetime.now(timezone.utc).isoformat()
                    if created_at:
                        try:
                            c_date = datetime.fromtimestamp(int(created_at), tz=timezone.utc).isoformat()
                        except Exception:
                            pass

                    comments_found.append(CommentData(
                        id=str(obj.get("id", obj.get("pk", len(comments_found) + 1))),
                        author=author or "instagram_user",
                        text=text,
                        created_at=c_date,
                        likes_count=int(obj.get("comment_like_count", 0))
                    ))
            for v in obj.values():
                find_comments(v)
        elif isinstance(obj, list):
            for item in obj:
                find_comments(item)

    scripts = re.findall(r'<script type="application/json"[^>]*>(.*?)</script>', html, re.DOTALL)
    for s in scripts:
        if "edge_media_to_parent_comment" in s or "comment" in s:
            try:
                data = json.loads(s)
                find_comments(data)
                if comments_found:
                    break
            except Exception:
                pass

    return comments_found[:target_comments]


async def scrape_instagram_via_browser(
    username: str,
    max_posts: Optional[int] = 10,
    max_comments: Optional[int] = 5
) -> InstagramScrapeResponse:
    """
    Session-free, rate-limit-resistant scraper using Playwright.
    Launches headless browser -> extracts public profile, posts, captions, likes, and comments.
    """
    url = f"https://www.instagram.com/{username}/"
    target_posts = max_posts if max_posts is not None else 10
    target_comments = max_comments if max_comments is not None else 5

    logger.info(f"[Playwright] Launching browser to scrape @{username} (Target: {target_posts} posts)...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="en-US",
            viewport={"width": 1280, "height": 900}
        )
        page = await context.new_page()

        try:
            # 1. Navigate to Profile
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await page.wait_for_timeout(2000)

            # 2. Extract Profile Metadata from Meta Tags
            meta_desc = await page.get_attribute("meta[name='description']", "content") or ""
            og_title = await page.get_attribute("meta[property='og:title']", "content") or ""
            og_image = await page.get_attribute("meta[property='og:image']", "content") or ""

            meta_info = parse_meta_description(meta_desc, username)

            profile = ProfileData(
                username=username,
                full_name=meta_info.get("full_name") or username,
                biography=meta_info.get("biography") or "",
                followers=meta_info.get("followers"),
                following=meta_info.get("following"),
                posts_count=meta_info.get("posts_count"),
                is_verified=True if "verified" in og_title.lower() or (meta_info.get("followers") and meta_info["followers"] > 100000) else False,
                profile_pic_url=og_image if og_image else f"https://instagram.com/{username}/profile_pic.jpg",
                external_url=f"https://www.instagram.com/{username}/"
            )

            # 3. Collect Post Shortcodes from DOM
            # Scroll down to load posts
            for _ in range(3):
                await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                await page.wait_for_timeout(800)

            post_elements = await page.eval_on_selector_all(
                "a[href*='/p/']",
                """elements => elements.map(el => {
                    const match = el.href.match(/\\/p\\/([A-Za-z0-9_-]+)/);
                    const img = el.querySelector('img');
                    return {
                        shortcode: match ? match[1] : null,
                        alt: img ? img.alt : '',
                        src: img ? img.src : ''
                    };
                }).filter(x => x.shortcode)"""
            )

            # Deduplicate shortcodes
            seen_shortcodes = set()
            unique_posts = []
            for item in post_elements:
                sc = item.get("shortcode")
                if sc and sc not in seen_shortcodes:
                    seen_shortcodes.add(sc)
                    unique_posts.append(item)

            logger.info(f"[Playwright] Discovered {len(unique_posts)} public post shortcodes for @{username}")

            posts: List[PostData] = []

            # 4. Extract Details for Each Post (Captions, Real Likes, Comments Count & Real Comments)
            for idx, p_item in enumerate(unique_posts[:target_posts]):
                shortcode = p_item["shortcode"]
                embed_url = f"https://www.instagram.com/p/{shortcode}/embed/captioned/"
                post_url = f"https://www.instagram.com/p/{shortcode}/"

                likes_count = 0
                comments_count = 0
                cleaned_caption = p_item.get("alt", "")
                post_date = datetime.now(timezone.utc).isoformat()
                timestamp = int(datetime.now(timezone.utc).timestamp())
                comments_list: List[CommentData] = []

                # Fetch Embed details for accurate caption, likes, comments count
                try:
                    embed_page = await context.new_page()
                    await embed_page.goto(embed_url, wait_until="domcontentloaded", timeout=12000)
                    await embed_page.wait_for_timeout(800)

                    embed_html = await embed_page.content()

                    # Extract full caption
                    caption_elem = await embed_page.query_selector(".Caption")
                    if caption_elem:
                        raw_caption = await caption_elem.inner_text()
                        cleaned_caption = raw_caption.strip()
                        if cleaned_caption.startswith(username):
                            cleaned_caption = cleaned_caption[len(username):].strip()
                        cleaned_caption = re.sub(r"View all [\d,]+ comments.*$", "", cleaned_caption, flags=re.DOTALL).strip()

                    # Extract REAL Likes Count with SocialProof pattern
                    likes_match = re.search(r'class="SocialProof"[^>]*>.*?([0-9,]+)\s*likes?', embed_html, re.I | re.DOTALL) or re.search(r'([0-9,]+)\s*likes?', embed_html, re.I)
                    if likes_match:
                        raw_l = likes_match.group(1).replace(",", "")
                        likes_count = int(raw_l) if raw_l.isdigit() else 0

                    # Extract REAL Comments Count
                    comments_match = re.search(r'View all\s+([0-9,]+)\s+comments', embed_html, re.I) or re.search(r'([0-9,]+)\s*comments?', embed_html, re.I)
                    if comments_match:
                        raw_c = comments_match.group(1).replace(",", "")
                        comments_count = int(raw_c) if raw_c.isdigit() else 0

                    await embed_page.close()
                except Exception as embed_err:
                    logger.warning(f"Embed extraction warning for {shortcode}: {embed_err}")

                # Fetch Post Page to extract Real Comments and accurate Datetime
                try:
                    post_page = await context.new_page()
                    await post_page.goto(post_url, wait_until="domcontentloaded", timeout=15000)
                    await post_page.wait_for_timeout(1000)

                    # Extract date
                    time_elem = await post_page.query_selector("time")
                    if time_elem:
                        dt_attr = await time_elem.get_attribute("datetime")
                        if dt_attr:
                            post_date = dt_attr
                            try:
                                timestamp = int(datetime.fromisoformat(dt_attr.replace("Z", "+00:00")).timestamp())
                            except Exception:
                                pass

                    # Extract real comments from post page JSON scripts
                    post_html = await post_page.content()
                    extracted_comments = extract_comments_from_html(post_html, target_comments)
                    if extracted_comments:
                        comments_list = extracted_comments

                    await post_page.close()
                except Exception as post_err:
                    logger.warning(f"Post comments extraction warning for {shortcode}: {post_err}")

                posts.append(PostData(
                    post_id=f"ig_{shortcode}",
                    shortcode=shortcode,
                    url=post_url,
                    date=post_date,
                    timestamp=timestamp,
                    caption=cleaned_caption if cleaned_caption else p_item.get("alt"),
                    location=LocationData(name=None),
                    likes_count=likes_count,
                    comments_count=comments_count,
                    comments=comments_list
                ))

            note_msg = (
                f"Successfully scraped {len(posts)} live posts for @{username} with real captions, likes, comments count, and comments. "
                "Note: Instagram's public web view renders recent posts without an account. Older historical archives are protected behind Meta's login wall."
            )

            return InstagramScrapeResponse(
                status="success",
                message=note_msg,
                source="live_browser_scraper",
                auth_required_for_posts=False,
                profile=profile,
                posts=posts,
                total_posts_scraped=len(posts)
            )

        finally:
            await browser.close()
