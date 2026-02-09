import time
from pathlib import Path

from app.core.config import get_settings
from app.services.text import normalize_text
from app.services.wikidata.client import WikidataClient
from app.services.wikidata.normalize import build_aliases, load_alias_denylist
from app.services.wikidata.queries import SPARQL_PLAYERS_QUERY


def _extract_qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    return value.split("T")[0]


def _parse_year(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value.split("-")[0])
    except ValueError:
        return None


def fetch_players(limit: int, sleep_s: float, max_rows: int | None, denylist_path: Path) -> list[dict]:
    settings = get_settings()
    client = WikidataClient(user_agent=f"{settings.app_name}/0.1 (Wikidata fetch)")
    players: dict[str, dict] = {}

    try:
        offset = 0
        fetched = 0
        while True:
            query = SPARQL_PLAYERS_QUERY.replace("__LIMIT__", str(limit)).replace("__OFFSET__", str(offset))
            result = client.query(query).data
            rows = result.get("results", {}).get("bindings", [])
            if not rows:
                break

            for row in rows:
                qid = _extract_qid(row["player"]["value"])
                player = players.setdefault(
                    qid,
                    {
                        "wikidata_qid": qid,
                        "full_name": row.get("playerLabel", {}).get("value", "").strip(),
                        "aliases": [],
                        "positions": [],
                        "birth_date": None,
                        "nba_debut_year": None,
                        "retired": None,
                    },
                )

                alias = row.get("alias", {}).get("value")
                if alias:
                    player["aliases"].append(alias)

                position = row.get("positionLabel", {}).get("value")
                if position:
                    player["positions"].append(position)

                birth_date = _parse_date(row.get("birthDate", {}).get("value"))
                if birth_date and not player["birth_date"]:
                    player["birth_date"] = birth_date

                nba_start_year = _parse_year(row.get("nbaStart", {}).get("value"))
                if nba_start_year:
                    current = player.get("nba_debut_year")
                    if not current or nba_start_year < current:
                        player["nba_debut_year"] = nba_start_year

            fetched += len(rows)
            offset += limit
            if max_rows and fetched >= max_rows:
                break
            time.sleep(sleep_s)
    finally:
        client.close()

    denylist = load_alias_denylist(denylist_path)
    cleaned_players: list[dict] = []

    for player in players.values():
        full_name = player["full_name"] or ""
        if not full_name:
            continue
        player["normalized_name"] = normalize_text(full_name)
        player["aliases"] = build_aliases(full_name, player.get("aliases", []), denylist)
        player["positions"] = sorted(set(player.get("positions", [])))
        cleaned_players.append(player)

    return cleaned_players
