import json
from datetime import datetime, timezone
from pathlib import Path


def default_snapshot_path() -> Path:
    return Path(__file__).resolve().parents[3] / "data" / "wikidata_players_snapshot.json"


def write_snapshot(players: list[dict], output_path: Path) -> None:
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": "wikidata",
        "players": players,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_snapshot(path: Path | None = None) -> dict:
    snapshot_path = path or default_snapshot_path()
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def snapshot_status(path: Path | None = None) -> dict:
    snapshot_path = path or default_snapshot_path()
    if not snapshot_path.exists():
        return {"exists": False, "generated_at": None, "player_count": 0, "alias_count": 0}

    payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    players = payload.get("players", [])
    alias_count = sum(len(p.get("aliases", [])) for p in players)
    return {
        "exists": True,
        "generated_at": payload.get("generated_at"),
        "player_count": len(players),
        "alias_count": alias_count,
    }
