from typing import List, Optional
from pydantic import BaseModel, Field


class LocationData(BaseModel):
    name: Optional[str] = Field(None, description="Location name or landmark")
    id: Optional[str] = Field(None, description="Location ID if available")
    latitude: Optional[float] = Field(None, description="Latitude coordinate")
    longitude: Optional[float] = Field(None, description="Longitude coordinate")


class CommentData(BaseModel):
    id: str = Field(..., description="Unique comment ID")
    author: str = Field(..., description="Instagram username of the comment author")
    text: str = Field(..., description="Comment content/body text")
    created_at: str = Field(..., description="ISO 8601 formatted datetime of comment")
    likes_count: Optional[int] = Field(0, description="Number of likes on the comment")


class PostData(BaseModel):
    post_id: str = Field(..., description="Instagram post ID")
    shortcode: str = Field(..., description="Instagram post shortcode (e.g., CxY123)")
    url: str = Field(..., description="Direct link to the Instagram post")
    date: str = Field(..., description="ISO 8601 datetime of post creation")
    timestamp: int = Field(..., description="Unix timestamp of post creation")
    caption: Optional[str] = Field(None, description="Post caption text")
    location: Optional[LocationData] = Field(None, description="Location details if tagged")
    likes_count: Optional[int] = Field(0, description="Number of likes on post")
    comments_count: Optional[int] = Field(0, description="Total comments count on post")
    comments: List[CommentData] = Field(default_factory=list, description="List of comments scraped for this post")


class ProfileData(BaseModel):
    username: str = Field(..., description="Instagram username (handle)")
    full_name: Optional[str] = Field(None, description="Profile full display name")
    biography: Optional[str] = Field(None, description="Account bio text")
    followers: Optional[int] = Field(None, description="Number of followers")
    following: Optional[int] = Field(None, description="Number of accounts followed")
    posts_count: Optional[int] = Field(None, description="Total media/posts published")
    is_verified: Optional[bool] = Field(None, description="Whether the account is verified (blue badge)")
    profile_pic_url: Optional[str] = Field(None, description="URL of the profile picture")
    external_url: Optional[str] = Field(None, description="External link in bio if present")


class InstagramScrapeRequest(BaseModel):
    url: str = Field(
        ...,
        description="Instagram profile URL (e.g. 'https://www.instagram.com/virat.kohli/') or username",
        example="https://www.instagram.com/virat.kohli/"
    )
    max_posts: Optional[int] = Field(
        10,
        description="Maximum posts to scrape (use None for all available posts, or integer like 5, 10, 50)"
    )
    max_comments_per_post: Optional[int] = Field(
        5,
        description="Maximum comments to scrape per post (use None for all comments, or integer)"
    )
    session_id: Optional[str] = Field(
        None,
        description="Optional Instagram 'sessionid' cookie value to bypass Instagram 401/login walls"
    )
    fallback_sample_data: Optional[bool] = Field(
        True,
        description="If True and Instagram requires login (401), falls back to rich sample schema for testing"
    )


class InstagramScrapeResponse(BaseModel):
    status: str = Field("success", description="Status string: success or error")
    message: str = Field("", description="Human-readable status or informational message")
    source: str = Field("live", description="'live' (direct Instagram scrape) or 'sample_fallback'")
    profile: ProfileData = Field(..., description="Scraped profile information")
    posts: List[PostData] = Field(default_factory=list, description="Scraped posts with captions, dates, locations, comments")
    total_posts_scraped: int = Field(0, description="Count of posts scraped")
