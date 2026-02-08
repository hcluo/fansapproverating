import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.entities import Player, PlayerAlias
from app.services.text import normalize_text
from app.services.wikidata.normalize import build_aliases, load_alias_denylist
from app.services.wikidata.snapshot import default_snapshot_path


def _resolve_players_payload(payload: dict | list) -> list[dict]:
    if isinstance(payload, list):
        return payload
    return payload.get("players", [])


def _compute_active(entry: dict, existing_active: bool | None) -> bool:
    if entry.get("retired") is True:
        return False
    if entry.get("retired") is False:
        return True
    if entry.get("active") is not None:
        return bool(entry.get("active"))
    return existing_active if existing_active is not None else True


def upsert_players_from_payload(db: Session, payload: dict | list, denylist_path: Path | None = None) -> dict:
    players = _resolve_players_payload(payload)
    denylist = load_alias_denylist(denylist_path) if denylist_path else set()

    created = 0
    updated = 0
    aliases_added = 0

    for entry in players:
        full_name = entry.get("full_name") or ""
        if not full_name:
            continue
        normalized_name = entry.get("normalized_name") or normalize_text(full_name)
        wikidata_qid = entry.get("wikidata_qid")

        player = None
        if wikidata_qid:
            player = db.execute(select(Player).where(Player.wikidata_qid == wikidata_qid)).scalar_one_or_none()
        if not player:
            player = db.execute(select(Player).where(Player.normalized_name == normalized_name)).scalar_one_or_none()

        if not player:
            player = Player(
                full_name=full_name,
                normalized_name=normalized_name,
                team=entry.get("team"),
                active=_compute_active(entry, None),
                wikidata_qid=wikidata_qid,
            )
            db.add(player)
            db.flush()
            created += 1
        else:
            player.full_name = full_name
            player.normalized_name = normalized_name
            player.team = entry.get("team", player.team)
            player.active = _compute_active(entry, player.active)
            if wikidata_qid and not player.wikidata_qid:
                player.wikidata_qid = wikidata_qid
            updated += 1

        aliases = build_aliases(full_name, entry.get("aliases", []), denylist)
        existing_aliases = {
            row[0]
            for row in db.execute(
                select(PlayerAlias.normalized_alias).where(PlayerAlias.player_id == player.id)
            ).all()
        }
        for alias in aliases:
            norm_alias = normalize_text(alias)
            if norm_alias in existing_aliases:
                continue
            db.add(PlayerAlias(player_id=player.id, alias_text=alias, normalized_alias=norm_alias))
            existing_aliases.add(norm_alias)
            aliases_added += 1

    db.commit()
    return {"created": created, "updated": updated, "aliases_added": aliases_added}


def upsert_players_from_snapshot_path(db: Session, snapshot_path: Path | None = None, denylist_path: Path | None = None) -> dict:
    path = snapshot_path or default_snapshot_path()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return upsert_players_from_payload(db, payload, denylist_path=denylist_path)
