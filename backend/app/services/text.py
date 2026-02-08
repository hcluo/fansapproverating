import re

PUNCT_RE = re.compile(r"[^\w\s]")
SPACE_RE = re.compile(r"\s+")


def normalize_text(value: str) -> str:
    value = value.lower().strip()
    value = PUNCT_RE.sub(" ", value)
    value = SPACE_RE.sub(" ", value)
    return value.strip()
