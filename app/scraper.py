import re
import logging
from typing import Optional, List
from datetime import datetime, timezone, timedelta

import instaloader
from fastapi import HTTPException

from app.models import (
    ProfileData,
    PostData,
    CommentData,
    LocationData,
    InstagramScrapeResponse,
)
from app.config import settings

logger = logging.getLogger("instagram_scraper")
logging.basicConfig(level=logging.INFO)


def extract_username(url_or_handle: str) -> str:
    """
    Extract clean Instagram username from a URL, handle, or string.
    Examples:
        - https://www.instagram.com/virat.kohli/ -> virat.kohli
        - https://instagram.com/virat.kohli?igsh=123 -> virat.kohli
        - @virat.kohli -> virat.kohli
        - virat.kohli -> virat.kohli
    """
    cleaned = url_or_handle.strip().strip("/")
    match = re.search(r"instagram\.com/([^/?#]+)", cleaned)
    if match:
        username = match.group(1)
    else:
        username = cleaned.lstrip("@").split("?")[0].split("/")[0]

    if not username or username in ["p", "reel", "stories", "explore"]:
        raise ValueError(f"Invalid Instagram profile URL or username: {url_or_handle}")

    return username


def create_instaloader_instance(session_id: Optional[str] = None) -> instaloader.Instaloader:
    """
    Creates an Instaloader instance configured for metadata scraping,
    injecting session credentials if provided.
    """
    loader = instaloader.Instaloader(
        download_pictures=False,
        download_videos=False,
        download_video_thumbnails=False,
        download_geotags=False,
        download_comments=False,
        save_metadata=False,
        compress_json=False,
        max_connection_attempts=3,
        request_timeout=20.0,
    )

    # Use session_id if supplied in request, or fall back to environment variable
    active_session_id = session_id or settings.INSTAGRAM_SESSION_ID
    if active_session_id:
        active_session_id = active_session_id.strip()
        logger.info("Applying Instagram sessionid cookie for authenticated live request")
        loader.context._session.cookies.set("sessionid", active_session_id, domain=".instagram.com")
        loader.context._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        })

    return loader


def build_dynamic_demo_posts(
    username: str,
    count: int = 10,
    max_comments: int = 3
) -> List[PostData]:
    """
    Generates dynamic demo post records up to the exact requested 'count'
    ONLY when the user explicitly enables demo/offline fallback mode.
    """
    base_captions = [
        "Focused on the journey ahead. Great session in the nets today! 🏏 #NeverSettle",
        "Refueling with healthy greens after an intense workout. Health is true wealth! 🥗💪",
        "Grateful for all the love and support from everyone around the globe. Keep believing. 🌟",
        "Match day ready! Bringing 100% intensity to the field today. Let's go! ⚡",
        "Quiet moments before the storm. Consistency and hard work beats talent when talent fails to work hard.",
        "Quality family time back home. Nothing recharges the soul like being with loved ones. ❤️",
        "Excited to announce our new brand collaboration! Stay tuned for something huge dropping this week.",
        "Back to the basics. Footwork drills and technique practice under the morning sun.",
        "Champions aren't made in the gym. They are made from something deep inside them: a desire, a dream, a vision.",
        "Great win with the squad today! Proud of every single teammate who stepped up when it counted."
    ]

    sample_locations = [
        "M. Chinnaswamy Stadium", "Wankhede Stadium, Mumbai", "Eden Gardens, Kolkata",
        "Melbourne Cricket Ground", "Lord's Cricket Ground, London", "New Delhi, India",
        "Dubai International Stadium", "Sydney Cricket Ground", "Cape Town, South Africa", None
    ]

    posts: List[PostData] = []
    base_time = datetime.now(timezone.utc) - timedelta(days=1)

    for i in range(count):
        post_time = base_time - timedelta(days=i * 2 + 1)
        cap = base_captions[i % len(base_captions)]
        loc_name = sample_locations[i % len(sample_locations)]
        shortcode = f"C{i:02d}vTest{i:04d}"

        comments: List[CommentData] = []
        for c_idx in range(max_comments):
            comments.append(CommentData(
                id=f"1800000{i:04d}{c_idx:03d}",
                author=f"fan_{username}_{c_idx+1}",
                text=f"Great post #{i+1}! Keep inspiring us!",
                created_at=(post_time + timedelta(minutes=15 * (c_idx + 1))).isoformat(),
                likes_count=1500 * (c_idx + 1)
            ))

        posts.append(PostData(
            post_id=f"33481234567890{i:05d}",
            shortcode=shortcode,
            url=f"https://www.instagram.com/p/{shortcode}/",
            date=post_time.isoformat(),
            timestamp=int(post_time.timestamp()),
            caption=f"[{i+1}/{count}] {cap}",
            location=LocationData(name=loc_name) if loc_name else None,
            likes_count=1500000 - (i * 12000),
            comments_count=25000 - (i * 200),
            comments=comments
        ))

    return posts


def scrape_instagram_profile(
    url_or_handle: str,
    max_posts: Optional[int] = 10,
    max_comments_per_post: Optional[int] = 5,
    session_id: Optional[str] = None,
    fallback_sample_data: bool = False
) -> InstagramScrapeResponse:
    """
    Main scraping function.
    - If session_id is provided: scrapes REAL live posts, captions, timestamps, locations, and comments.
    - If unauthenticated and Instagram blocks timeline:
      - By default (fallback_sample_data=False): returns REAL profile data + empty posts list + clear instructions to supply session_id.
      - If fallback_sample_data=True: returns dynamic demo posts up to max_posts.
    """
    username = extract_username(url_or_handle)
    loader = create_instaloader_instance(session_id)

    partial_profile = {}
    profile_data = None

    try:
        logger.info(f"Fetching real Instagram profile metadata for '@{username}'...")
        profile = instaloader.Profile.from_username(loader.context, username)
        
        # Extract profile fields
        try:
            partial_profile["full_name"] = profile.full_name
            partial_profile["biography"] = profile.biography
            partial_profile["followers"] = profile.followers
            partial_profile["following"] = profile.followees
            partial_profile["posts_count"] = profile.mediacount
            partial_profile["is_verified"] = profile.is_verified
            partial_profile["profile_pic_url"] = profile.profile_pic_url
            partial_profile["external_url"] = profile.external_url
        except Exception as attr_err:
            logger.warning(f"Attribute access warning: {attr_err}")

        profile_data = ProfileData(
            username=profile.username,
            full_name=partial_profile.get("full_name") or profile.username,
            biography=partial_profile.get("biography") or "",
            followers=partial_profile.get("followers"),
            following=partial_profile.get("following"),
            posts_count=partial_profile.get("posts_count"),
            is_verified=partial_profile.get("is_verified"),
            profile_pic_url=partial_profile.get("profile_pic_url"),
            external_url=partial_profile.get("external_url")
        )

        posts_data: List[PostData] = []
        target_posts = max_posts if max_posts is not None else 10
        target_comments = max_comments_per_post if max_comments_per_post is not None else 5

        logger.info(f"Fetching real posts and comments for '@{username}' (target: {target_posts} posts)...")
        
        # Iterate live posts
        for post_idx, post in enumerate(profile.get_posts()):
            if max_posts is not None and post_idx >= max_posts:
                break

            post_date = post.date_utc.replace(tzinfo=timezone.utc).isoformat()
            post_timestamp = int(post.date_utc.timestamp())

            location_data = None
            if post.location:
                location_data = LocationData(
                    name=post.location.name,
                    id=str(post.location.id) if post.location.id else None,
                    latitude=post.location.lat,
                    longitude=post.location.lng
                )

            comments_data: List[CommentData] = []
            try:
                for comment_idx, comment in enumerate(post.get_comments()):
                    if max_comments_per_post is not None and comment_idx >= max_comments_per_post:
                        break

                    comment_created = (
                        comment.created_at_utc.replace(tzinfo=timezone.utc).isoformat()
                        if comment.created_at_utc else ""
                    )
                    
                    comments_data.append(CommentData(
                        id=str(comment.id),
                        author=comment.owner.username if comment.owner else "anonymous",
                        text=comment.text,
                        created_at=comment_created,
                        likes_count=comment.likes_count if hasattr(comment, "likes_count") else 0
                    ))
            except Exception as comment_err:
                logger.warning(f"Error fetching comments for post {post.shortcode}: {comment_err}")

            posts_data.append(PostData(
                post_id=str(post.mediaid),
                shortcode=post.shortcode,
                url=f"https://www.instagram.com/p/{post.shortcode}/",
                date=post_date,
                timestamp=post_timestamp,
                caption=post.caption,
                location=location_data,
                likes_count=post.likes,
                comments_count=post.comments,
                comments=comments_data
            ))

        return InstagramScrapeResponse(
            status="success",
            message=f"Successfully scraped {len(posts_data)} real posts from @{username}",
            source="live",
            auth_required_for_posts=False,
            profile=profile_data,
            posts=posts_data,
            total_posts_scraped=len(posts_data)
        )

    except instaloader.exceptions.ProfileNotExistsException:
        raise HTTPException(status_code=404, detail=f"Instagram profile '{username}' does not exist.")

    except instaloader.exceptions.PrivateProfileNotFollowedException:
        raise HTTPException(
            status_code=403,
            detail=f"Instagram profile '{username}' is private. Log in with an account that follows this user."
        )

    except instaloader.exceptions.ConnectionException as conn_err:
        err_msg = str(conn_err)
        logger.error(f"Instaloader connection exception: {err_msg}")
        
        # Instagram blocks unauthenticated timeline requests (401 / require_login)
        if "401" in err_msg or "Please wait" in err_msg or "redirect" in err_msg or "login" in err_msg.lower():
            # If user explicitly requested offline demo fallback
            if fallback_sample_data:
                logger.info(f"Fallback demo requested: generating {max_posts or 10} demo posts.")
                demo_posts = build_dynamic_demo_posts(
                    username=username,
                    count=max_posts if max_posts is not None else 10,
                    max_comments=max_comments_per_post if max_comments_per_post is not None else 3
                )
                safe_profile = profile_data or ProfileData(
                    username=username,
                    full_name=partial_profile.get("full_name") or username,
                    biography=partial_profile.get("biography") or "",
                    followers=partial_profile.get("followers"),
                    following=partial_profile.get("following"),
                    posts_count=partial_profile.get("posts_count"),
                    is_verified=partial_profile.get("is_verified")
                )
                return InstagramScrapeResponse(
                    status="success",
                    message=f"Serving {len(demo_posts)} demo sample posts (Demo mode explicitly enabled).",
                    source="demo_sample",
                    auth_required_for_posts=True,
                    instructions="To fetch REAL live posts, provide your Instagram 'sessionid' cookie and turn off demo mode.",
                    profile=safe_profile,
                    posts=demo_posts,
                    total_posts_scraped=len(demo_posts)
                )

            # Default: Real data only. Return real profile, 0 fake posts, clear explanation
            safe_profile = profile_data or ProfileData(
                username=username,
                full_name=partial_profile.get("full_name") or username,
                biography=partial_profile.get("biography") or "",
                followers=partial_profile.get("followers"),
                following=partial_profile.get("following"),
                posts_count=partial_profile.get("posts_count"),
                is_verified=partial_profile.get("is_verified")
            )
            return InstagramScrapeResponse(
                status="partial_success",
                message=(
                    f"Real profile metadata for @{username} was fetched successfully! "
                    f"However, Instagram returned 401 Unauthorized for posts and comments because Meta strictly requires an active login session. "
                    f"No fake sample posts were returned."
                ),
                source="live_profile_only",
                auth_required_for_posts=True,
                instructions=(
                    "How to get real posts & comments: (1) Open instagram.com and log in. "
                    "(2) Press F12 -> Application tab -> Cookies -> Copy the value of 'sessionid'. "
                    "(3) Paste it into the 'Instagram Session ID' input field or configure INSTAGRAM_SESSION_ID in .env."
                ),
                profile=safe_profile,
                posts=[],
                total_posts_scraped=0
            )

        raise HTTPException(status_code=502, detail=f"Instagram connection error: {err_msg}")

    except Exception as exc:
        logger.exception(f"Unexpected error while scraping @{username}: {exc}")
        raise HTTPException(status_code=500, detail=f"Internal scraping error: {str(exc)}")
