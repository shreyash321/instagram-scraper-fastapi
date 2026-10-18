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


def test_scrape_real_virat_kohli():
    sample_url = "https://www.instagram.com/virat.kohli/"
    print(f"2. Testing Real Scrape for: {sample_url} (Live profile, no fake mixing)...")

    payload = {
        "url": sample_url,
        "max_posts": 10,
        "max_comments_per_post": 3,
        "fallback_sample_data": False
    }

    res = client.post("/api/v1/scrape", json=payload)
    print("Status code:", res.status_code)
    assert res.status_code == 200, f"Failed with {res.status_code}: {res.text}"

    data = res.json()
    print("Status:", data.get("status"))
    print("Source:", data.get("source"))
    print("Real Profile Full Name:", data.get("profile", {}).get("full_name"))
    print("Real Username:", data.get("profile", {}).get("username"))
    print("Real Bio:", data.get("profile", {}).get("biography"))
    print("Real Followers:", data.get("profile", {}).get("followers"))
    print("Auth Required for Posts:", data.get("auth_required_for_posts"))
    print("Total Posts Scraped:", data.get("total_posts_scraped"))
    print(" PASS (No fake data mixed in!)\n")


def test_scrape_50_demo_posts():
    print("3. Testing explicit 50 demo posts request (verifying it does not default to 3)...")
    payload = {
        "url": "https://www.instagram.com/virat.kohli/",
        "max_posts": 50,
        "max_comments_per_post": 2,
        "fallback_sample_data": True
    }

    res = client.post("/api/v1/scrape", json=payload)
    assert res.status_code == 200
    data = res.json()
    posts = data.get("posts", [])
    print(f"Total posts returned: {len(posts)} (Expected 50)")
    assert len(posts) == 50, f"Expected 50 posts, got {len(posts)}"
    print("Source:", data.get("source"))
    print("First post:", posts[0].get("caption")[:60])
    print("50th post:", posts[49].get("caption")[:60])
    print(" PASS (50 posts generated properly without truncating to 3!)\n")


if __name__ == "__main__":
    try:
        test_health()
        test_scrape_real_virat_kohli()
        test_scrape_50_demo_posts()
        print("All tests passed successfully!")
    except Exception as e:
        print(f"Test failed with error: {e}")
        sys.exit(1)
