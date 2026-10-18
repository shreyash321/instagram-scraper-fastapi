import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    APP_NAME: str = "Instagram Scraper FastAPI"
    APP_VERSION: str = "1.0.0"
    APP_HOST: str = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT: int = int(os.getenv("APP_PORT", "8000"))
    
    # Instagram Session ID from cookie (optional, but recommended to prevent rate limits)
    INSTAGRAM_SESSION_ID: str = os.getenv("INSTAGRAM_SESSION_ID", "")
    
    # Default limits
    DEFAULT_MAX_POSTS: int = int(os.getenv("DEFAULT_MAX_POSTS", "10"))
    DEFAULT_MAX_COMMENTS: int = int(os.getenv("DEFAULT_MAX_COMMENTS", "5"))

settings = Settings()
