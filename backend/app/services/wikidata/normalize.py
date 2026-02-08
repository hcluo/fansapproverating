from pathlib import Path

from app.services.text import normalize_text


def load_alias_denylist(path: Path) -> set[str]:
    if not path.exists():
        return set()
    denylist = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        value = raw.strip()
        if not value or value.startswith("#"):
            continue
        denylist.add(normalize_text(value))
    return denylist


def build_aliases(full_name: str, aliases: list[str] | None, denylist: set[str]) -> list[str]:
    candidates = list(aliases or []) + [full_name]
    seen = set()
    cleaned: list[str] = []

    for alias in candidates:
        alias_text = alias.strip()
        if not alias_text:
            continue
        normalized = normalize_text(alias_text)
        if not normalized or len(normalized) <= 2:
            continue
        if normalized in denylist:
            continue
        if normalized in seen:
            continue
        seen.add(normalized)
        cleaned.append(alias_text)

    return cleaned
