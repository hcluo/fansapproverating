from app.core.config import get_settings
from app.services.text import normalize_text
from app.services.wikidata.client import WikidataClient
from app.services.wikidata.queries import SPARQL_ROCKETS_CURRENT_QUERY


def _extract_qid(uri: str) -> str:
    return uri.rsplit("/", 1)[-1]


def fetch_current_rockets_roster() -> list[dict]:
    settings = get_settings()
    client = WikidataClient(user_agent=f"{settings.app_name}/0.1 (Wikidata rockets roster)")
    try:
        result = client.query(SPARQL_ROCKETS_CURRENT_QUERY).data
    finally:
        client.close()

    rows = result.get("results", {}).get("bindings", [])
    players: dict[str, dict] = {}
    for row in rows:
        qid = _extract_qid(row["player"]["value"])
        entry = players.setdefault(
            qid,
            {
                "wikidata_qid": qid,
                "full_name": row.get("playerLabel", {}).get("value", "").strip(),
                "aliases": [],
            },
        )
        alias = row.get("alias", {}).get("value")
        if alias:
            entry["aliases"].append(alias)

    cleaned: list[dict] = []
    for entry in players.values():
        if not entry["full_name"]:
            continue
        entry["normalized_name"] = normalize_text(entry["full_name"])
        cleaned.append(entry)
    return cleaned
