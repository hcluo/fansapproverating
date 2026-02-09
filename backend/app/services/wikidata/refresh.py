from pathlib import Path

from app.db.session import SessionLocal
from app.services.wikidata.fetch import fetch_players
from app.services.wikidata.seed import upsert_players_from_snapshot_path
from app.services.wikidata.snapshot import write_snapshot


def refresh_players_from_wikidata_sync(limit: int = 500, sleep_s: float = 1.0, max_rows: int | None = None) -> dict:
    base_dir = Path(__file__).resolve().parents[3]
    snapshot_path = base_dir / "data" / "wikidata_players_snapshot.json"
    denylist_path = base_dir / "data" / "alias_denylist.txt"

    players = fetch_players(limit=limit, sleep_s=sleep_s, max_rows=max_rows, denylist_path=denylist_path)
    write_snapshot(players, snapshot_path)

    db = SessionLocal()
    try:
        result = upsert_players_from_snapshot_path(db, snapshot_path=snapshot_path, denylist_path=denylist_path)
    finally:
        db.close()

    result.update({"player_count": len(players), "snapshot_path": str(snapshot_path)})
    return result
