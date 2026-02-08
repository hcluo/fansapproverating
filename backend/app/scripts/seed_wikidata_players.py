import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.wikidata.seed import upsert_players_from_payload, upsert_players_from_snapshot_path

# Repo inspection (Feb 8, 2026): players are seeded from backend/data/players_seed.json
# via app.scripts.seed_players, Player/PlayerAlias models in app/models/entities.py,
# Makefile seed target calls python -m app.scripts.seed_players, and /players API routes
# live in app/api/routes.py.


def run() -> None:
    base_dir = Path(__file__).resolve().parents[2]
    snapshot_path = base_dir / "data" / "wikidata_players_snapshot.json"
    denylist_path = base_dir / "data" / "alias_denylist.txt"
    fallback_seed_path = base_dir / "data" / "players_seed.json"

    db = SessionLocal()
    try:
        if snapshot_path.exists():
            result = upsert_players_from_snapshot_path(db, snapshot_path=snapshot_path, denylist_path=denylist_path)
        else:
            payload = json.loads(fallback_seed_path.read_text(encoding="utf-8"))
            result = upsert_players_from_payload(db, payload, denylist_path=denylist_path)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    run()
