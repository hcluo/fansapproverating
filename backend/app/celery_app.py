from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "fansapprove",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.jobs"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=settings.celery_task_eager_propagates,
)

celery_app.conf.beat_schedule = {
    "reddit-ingest-every-10-min": {
        "task": "app.tasks.jobs.reddit_ingest_task",
        "schedule": crontab(minute="*/10"),
    },
    "aggregate-yesterday": {
        "task": "app.tasks.jobs.aggregate_daily_task",
        "schedule": crontab(hour=1, minute=5),
    },
    "aggregate-today": {
        "task": "app.tasks.jobs.aggregate_daily_task",
        "schedule": crontab(hour=1, minute=15),
        "args": ("today",),
    },
}

if settings.enable_wikidata_refresh:
    celery_app.conf.beat_schedule["wikidata-refresh-monthly"] = {
        "task": "app.tasks.jobs.refresh_players_from_wikidata",
        "schedule": crontab(day_of_month="1", hour=2, minute=0),
    }
