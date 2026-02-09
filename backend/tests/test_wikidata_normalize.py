from app.services.text import normalize_text
from app.services.wikidata.normalize import build_aliases


def test_build_aliases_normalizes_and_filters():
    denylist = {"king", "mr"}
    aliases = ["LeBron", " King ", "LBJ", "A", "LeBron!!!", "Mr"]
    result = build_aliases("LeBron James", aliases, denylist)

    normalized = [normalize_text(a) for a in result]
    assert "lebron james" in normalized
    assert "lebron" in normalized
    assert "lbj" in normalized
    assert "king" not in normalized
    assert "mr" not in normalized
    assert "a" not in normalized
    assert len(normalized) == len(set(normalized))
