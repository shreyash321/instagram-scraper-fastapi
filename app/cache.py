import time
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger("scraper_cache")


class SimpleTTLCache:
    """
    In-memory thread-safe TTL cache.
    Prevents repeated scraping of the same profile within a short time window.
    """
    def __init__(self, default_ttl_seconds: int = 600):
        self.default_ttl = default_ttl_seconds
        self._cache: Dict[str, Dict[str, Any]] = {}

    def get(self, key: str) -> Optional[Any]:
        entry = self._cache.get(key)
        if not entry:
            return None
        
        # Check expiry
        if time.time() > entry["expires_at"]:
            del self._cache[key]
            return None

        logger.info(f"Cache HIT for key: '{key}' (saves live rate-limit)")
        return entry["value"]

    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        self._cache[key] = {
            "value": value,
            "expires_at": time.time() + ttl
        }
        logger.info(f"Cached key: '{key}' for {ttl} seconds")

    def clear(self) -> None:
        self._cache.clear()


# Global cache instance (10-minute default TTL)
cache = SimpleTTLCache(default_ttl_seconds=600)

