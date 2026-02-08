import logging
import time
import praw

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class RedditRateLimiter:
    def __init__(self, min_interval_seconds: float = 1.0):
        self.min_interval_seconds = min_interval_seconds
        self._last = 0.0

    def wait(self) -> None:
        now = time.time()
        delta = now - self._last
        if delta < self.min_interval_seconds:
            time.sleep(self.min_interval_seconds - delta)
        self._last = time.time()


def get_reddit() -> tuple[praw.Reddit, RedditRateLimiter]:
    settings = get_settings()
    reddit = praw.Reddit(
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        user_agent=settings.reddit_user_agent,
        ratelimit_seconds=30,
    )
    return reddit, RedditRateLimiter(min_interval_seconds=1.0)
