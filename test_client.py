import json
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    print("1. Testing Health Endpoint...")
    res = client.get("/health")
    assert res.status_code == 200, f"Expected 200, got {res.status_code}"
    print("Health check response:", res.json())
    print(" PASS\n")


def test_scrape_virat_kohli():
    sample_url = "https://www.instagram.com/virat.kohli/"
    print(f"2. Testing Scrape for Sample Link: {sample_url}")

    payload = {
        "url": sample_url,
        "max_posts": 3,
        "max_comments_per_post": 2,
        "fallback_sample_data": True
    }

    res = client.post("/api/v1/scrape", json=payload)
    print("Status code:", res.status_code)
    assert res.status_code == 200, f"Failed with {res.status_code}: {res.text}"

    data = res.json()
    print("\n--- Scraped JSON Result Overview ---")
    print("Status:", data.get("status"))
    print("Source:", data.get("source"))
    print("Profile Name:", data.get("profile", {}).get("full_name"))
    print("Username:", data.get("profile", {}).get("username"))
    print("Bio:", data.get("profile", {}).get("biography"))
    print("Followers:", data.get("profile", {}).get("followers"))
    print("Total Posts Scraped:", len(data.get("posts", [])))

    posts = data.get("posts", [])
    for idx, post in enumerate(posts):
        print(f"\n--- Post #{idx + 1} ---")
        print(f"Post ID: {post.get('post_id')}")
        print(f"URL: {post.get('url')}")
        print(f"Date: {post.get('date')}")
        print(f"Location: {post.get('location')}")
        print(f"Caption: {post.get('caption')[:80] if post.get('caption') else 'None'}...")
        print(f"Likes: {post.get('likes_count')}")
        print(f"Comments Count: {post.get('comments_count')}")
        print("Comments Scraped:")
        for comment in post.get("comments", []):
            print(f"  - @{comment.get('author')}: {comment.get('text')} (Date: {comment.get('created_at')})")

    # Save output to a JSON file for inspection
    output_filename = "sample_virat_kohli_output.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"\n Full JSON output successfully saved to '{output_filename}'")
    print(" PASS\n")


if __name__ == "__main__":
    try:
        test_health()
        test_scrape_virat_kohli()
        print("All tests passed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
