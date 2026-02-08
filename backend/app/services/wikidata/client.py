import time
from dataclasses import dataclass

import httpx

WIKIDATA_ENDPOINT = "https://query.wikidata.org/sparql"
DEFAULT_TIMEOUT_S = 60


@dataclass(frozen=True)
class SparqlResult:
    data: dict


class WikidataClient:
    def __init__(self, user_agent: str, timeout_s: int = DEFAULT_TIMEOUT_S):
        self._client = httpx.Client(timeout=timeout_s, follow_redirects=True)
        self._user_agent = user_agent

    def close(self) -> None:
        self._client.close()

    def query(self, sparql: str) -> SparqlResult:
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": self._user_agent,
            "Cache-Control": "max-age=3600",
        }
        payload = {"query": sparql}

        last_exc: Exception | None = None
        for attempt in range(3):
            try:
                response = self._client.post(WIKIDATA_ENDPOINT, data=payload, headers=headers)
                if response.status_code == 429:
                    retry_after = int(response.headers.get("Retry-After", "5"))
                    time.sleep(retry_after)
                    continue
                response.raise_for_status()
                return SparqlResult(response.json())
            except Exception as exc:
                last_exc = exc
                time.sleep(2 + attempt)
        raise RuntimeError("Failed to query Wikidata") from last_exc
