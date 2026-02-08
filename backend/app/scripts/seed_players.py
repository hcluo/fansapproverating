import json
from pathlib import Path

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.entities import Player, PlayerAlias
from app.services.text import normalize_text


def run() -> None:
    db = SessionLocal()
    seed_path = Path(__file__).resolve().parents[2] / "data" / "players_seed.json"
    payload = json.loads(seed_path.read_text())

    for entry in payload:
        normalized_name = normalize_text(entry["full_name"])
        player = db.execute(select(Player).where(Player.normalized_name == normalized_name)).scalar_one_or_none()
        if not player:
            player = Player(
                full_name=entry["full_name"],
                normalized_name=normalized_name,
                team=entry.get("team"),
                active=entry.get("active", True),
            )
            db.add(player)
            db.commit()
            db.refresh(player)

        aliases = set(entry.get("aliases", [])) | {entry["full_name"]}
        for alias in aliases:
            norm_alias = normalize_text(alias)
            exists = db.execute(
                select(PlayerAlias).where(PlayerAlias.player_id == player.id, PlayerAlias.normalized_alias == norm_alias)
            ).scalar_one_or_none()
            if not exists:
                db.add(PlayerAlias(player_id=player.id, alias_text=alias, normalized_alias=norm_alias))
    db.commit()
    db.close()


if __name__ == "__main__":
    run()
