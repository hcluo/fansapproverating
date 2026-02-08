from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import Player, PlayerDailyMetric
from app.schemas.player import NarrativeOut, PlayerMetricOut, PlayerOut
from app.services.text import normalize_text
from app.tasks.jobs import aggregate_daily_task, reddit_ingest_task

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/players", response_model=list[PlayerOut])
def list_players(query: str | None = None, db: Session = Depends(get_db)):
    stmt = select(Player)
    if query:
        stmt = stmt.where(Player.normalized_name.contains(normalize_text(query)))
    return db.execute(stmt.order_by(Player.full_name).limit(100)).scalars().all()


@router.get("/players/{player_id}", response_model=PlayerOut)
def get_player(player_id: str, db: Session = Depends(get_db)):
    return db.get(Player, player_id)


@router.get("/players/{player_id}/metrics", response_model=list[PlayerMetricOut])
def metrics(player_id: str, from_date: date = Query(alias="from"), to_date: date = Query(alias="to"), db: Session = Depends(get_db)):
    stmt = (
        select(PlayerDailyMetric)
        .where(
            PlayerDailyMetric.player_id == player_id,
            PlayerDailyMetric.date >= from_date,
            PlayerDailyMetric.date <= to_date,
        )
        .order_by(PlayerDailyMetric.date)
    )
    return db.execute(stmt).scalars().all()


@router.get("/players/{player_id}/narratives", response_model=NarrativeOut)
def narratives(player_id: str, date_value: date = Query(alias="date"), db: Session = Depends(get_db)):
    metric = db.execute(
        select(PlayerDailyMetric).where(PlayerDailyMetric.player_id == player_id, PlayerDailyMetric.date == date_value)
    ).scalar_one()
    summary = f"Top discussion terms include: {', '.join(list(metric.top_terms_json.keys())[:5]) or 'n/a'}"
    return NarrativeOut(date=date_value, top_terms_json=metric.top_terms_json, summary=summary)


@router.post("/admin/ingest/reddit")
def trigger_ingest(subreddits: list[str] | None = None, limit_posts: int = 20, limit_comments_per_post: int = 100):
    task = reddit_ingest_task.delay(subreddits, limit_posts, limit_comments_per_post)
    return {"task_id": task.id}


@router.post("/admin/recompute")
def trigger_recompute(day: str = "yesterday"):
    task = aggregate_daily_task.delay(day)
    return {"task_id": task.id}
