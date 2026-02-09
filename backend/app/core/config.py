from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "fansapprove-rating-backend"
    environment: str = "dev"
    database_url: str = "postgresql+psycopg://postgres:postgres@postgres:5432/fansapproverating"
    redis_url: str = "redis://redis:6379/0"

    reddit_client_id: str = ""
    reddit_client_secret: str = ""
    reddit_user_agent: str = "fansapprove-rating/0.1"
    ingest_subreddits: str = "nba"

    forum_ingest_enabled: bool = True
    forum_rss_urls: str = "https://bbs.clutchfans.net/forums/houston-rockets-game-action-roster-moves.9/index.rss"
    forum_rate_limit_seconds: float = 1.0
    forum_backfill_days: int = 7
    forum_player_scope: str = "rockets"

    celery_task_always_eager: bool = False
    celery_task_eager_propagates: bool = False

    admin_token: str = ""
    enable_wikidata_refresh: bool = False

    match_denylist: str = "king"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
