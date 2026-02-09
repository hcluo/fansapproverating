import json
from pathlib import Path

from app.db.session import SessionLocal
from app.services.text import normalize_text
from app.services.wikidata.rockets import fetch_current_rockets_roster
from app.services.wikidata.seed import upsert_players_from_payload


def run() -> None:
    base_dir = Path(__file__).resolve().parents[2]
    denylist_path = base_dir / "data" / "alias_denylist.txt"
    roster_path = base_dir / "data" / "rockets_roster_2025_26.json"

    roster_payload: list[dict] = []
    if roster_path.exists():
        names = json.loads(roster_path.read_text(encoding="utf-8"))
        for name in names:
            last_name = normalize_text(name).split(" ")[-1]
            aliases = [last_name] if len(last_name) >= 4 else []
            roster_payload.append(
                {
                    "full_name": name,
                    "normalized_name": normalize_text(name),
                    "aliases": aliases,
                    "team": "Houston Rockets",
                }
            )
    else:
        roster_payload = fetch_current_rockets_roster()
        for entry in roster_payload:
            entry["team"] = "Houston Rockets"

    db = SessionLocal()
    try:
        result = upsert_players_from_payload(db, roster_payload, denylist_path=denylist_path)
    finally:
        db.close()

    print(result)


if __name__ == "__main__":
    run()
