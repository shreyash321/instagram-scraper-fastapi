from fastapi import FastAPI, Query, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional

from app.models import InstagramScrapeRequest, InstagramScrapeResponse
from app.scraper import scrape_instagram_profile
from app.config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=(
        "FastAPI service that takes an Instagram profile link/handle as input "
        "and scrapes profile name, bio, captions for all posts, dates, locations, "
        "and post comments, returning everything in clean JSON format."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS Middleware to allow frontend/mobile/Postman clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def root():
    return {
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "endpoints": {
            "POST /api/v1/scrape": "Scrapes profile & posts given a JSON request body with Instagram URL",
            "GET /api/v1/scrape": "Scrapes profile & posts via query parameters (?url=...)",
            "GET /api/v1/profile/{username}": "Direct scrape via username path parameter",
            "GET /health": "Health check endpoint"
        },
        "sample_usage": {
            "url": "https://www.instagram.com/virat.kohli/",
            "max_posts": 5,
            "max_comments_per_post": 3
        }
    }


@app.get("/health", tags=["General"])
def health_check():
    return {"status": "healthy"}


@app.post(
    "/api/v1/scrape",
    response_model=InstagramScrapeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scraper"],
    summary="Scrape Instagram profile by URL (JSON Body)"
)
def scrape_profile_post(request: InstagramScrapeRequest):
    """
    Scrapes an Instagram profile using a JSON request body:
    - **url**: Full profile link (e.g. `https://www.instagram.com/virat.kohli/`) or handle
    - **max_posts**: Maximum number of posts to scrape (default: 10)
    - **max_comments_per_post**: Maximum comments to fetch per post (default: 5)
    - **session_id**: Optional Instagram sessionid cookie value
    - **fallback_sample_data**: If True, returns rich schema if Instagram throws 401
    """
    try:
        response = scrape_instagram_profile(
            url_or_handle=request.url,
            max_posts=request.max_posts,
            max_comments_per_post=request.max_comments_per_post,
            session_id=request.session_id,
            fallback_sample_data=request.fallback_sample_data
        )
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while scraping: {str(e)}"
        )


@app.get(
    "/api/v1/scrape",
    response_model=InstagramScrapeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scraper"],
    summary="Scrape Instagram profile by URL (Query Params)"
)
def scrape_profile_get(
    url: str = Query(..., description="Instagram profile URL (e.g. https://www.instagram.com/virat.kohli/)"),
    max_posts: Optional[int] = Query(5, description="Max posts to scrape"),
    max_comments: Optional[int] = Query(3, description="Max comments per post"),
    session_id: Optional[str] = Query(None, description="Optional sessionid cookie"),
    fallback_sample_data: bool = Query(True, description="Fallback if Instagram rate limits")
):
    """
    Convenient GET endpoint for quick browser or webhook testing.
    """
    return scrape_instagram_profile(
        url_or_handle=url,
        max_posts=max_posts,
        max_comments_per_post=max_comments,
        session_id=session_id,
        fallback_sample_data=fallback_sample_data
    )


@app.get(
    "/api/v1/profile/{username}",
    response_model=InstagramScrapeResponse,
    status_code=status.HTTP_200_OK,
    tags=["Scraper"],
    summary="Scrape Instagram profile by username"
)
def scrape_by_username(
    username: str,
    max_posts: Optional[int] = Query(5, description="Max posts to scrape"),
    max_comments: Optional[int] = Query(3, description="Max comments per post"),
    session_id: Optional[str] = Query(None, description="Optional sessionid cookie")
):
    """
    Convenient endpoint to fetch directly by username handle (e.g. /api/v1/profile/virat.kohli).
    """
    return scrape_instagram_profile(
        url_or_handle=username,
        max_posts=max_posts,
        max_comments_per_post=max_comments,
        session_id=session_id,
        fallback_sample_data=True
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.APP_HOST, port=settings.APP_PORT, reload=True)
