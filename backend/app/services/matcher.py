import re
from collections import defaultdict
from dataclasses import dataclass
from uuid import UUID

from app.services.text import normalize_text


@dataclass(frozen=True)
class AliasEntry:
    player_id: UUID
    alias_text: str
    normalized_alias: str


class PlayerMentionMatcher:
    def __init__(self, aliases: list[AliasEntry], denylist: set[str] | None = None):
        self.alias_map: dict[str, list[AliasEntry]] = defaultdict(list)
        self.denylist = denylist or set()
        for alias in aliases:
            if alias.normalized_alias in self.denylist:
                continue
            self.alias_map[alias.normalized_alias].append(alias)
        pattern = "|".join(sorted((re.escape(k) for k in self.alias_map.keys()), key=len, reverse=True))
        self.regex = re.compile(rf"\b({pattern})\b") if pattern else None

    def find_mentions(self, text: str) -> list[tuple[UUID, str]]:
        if not self.regex:
            return []
        normalized = normalize_text(text)
        matches = self.regex.findall(normalized)
        results: list[tuple[UUID, str]] = []
        seen = set()
        for match in matches:
            for alias in self.alias_map.get(match, []):
                key = (alias.player_id, match)
                if key not in seen:
                    seen.add(key)
                    results.append((alias.player_id, match))
        return results
