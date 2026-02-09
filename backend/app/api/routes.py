from datetime import date
from fastapi import APIRouter, Depends, Query, Request, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_db
from app.models.entities import Player, PlayerDailyMetric
from app.schemas.player import NarrativeOut, PlayerMetricOut, PlayerOut
from app.services.text import normalize_text
from app.services.wikidata.refresh import refresh_players_from_wikidata_sync
from app.services.wikidata.snapshot import default_snapshot_path, snapshot_status
from app.tasks.jobs import aggregate_daily_task, reddit_ingest_task, refresh_players_from_wikidata

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _require_admin(request: Request) -> None:
    settings = get_settings()
    if not settings.admin_token:
        return
    token = request.headers.get("X-Admin-Token", "")
    if token != settings.admin_token:
        raise HTTPException(status_code=401, detail="invalid admin token")


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


@router.post("/admin/players/refresh-wikidata")
def refresh_wikidata(request: Request):
    _require_admin(request)
    settings = get_settings()
    if settings.celery_task_always_eager:
        result = refresh_players_from_wikidata_sync()
        return {"mode": "sync", **result}
    task = refresh_players_from_wikidata.delay()
    return {"mode": "async", "task_id": task.id}


@router.get("/admin/players/source-status")
def wikidata_source_status(request: Request):
    _require_admin(request)
    status = snapshot_status()
    status["snapshot_path"] = str(default_snapshot_path())
    return status
