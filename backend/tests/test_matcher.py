import uuid

from app.services.matcher import AliasEntry, PlayerMentionMatcher
from app.services.text import normalize_text


def test_matcher_finds_aliases_and_avoids_denylist():
    player_id = uuid.uuid4()
    aliases = [
        AliasEntry(player_id=player_id, alias_text="LeBron", normalized_alias=normalize_text("LeBron")),
        AliasEntry(player_id=player_id, alias_text="King", normalized_alias=normalize_text("King")),
    ]
    matcher = PlayerMentionMatcher(aliases, denylist={"king"})
    mentions = matcher.find_mentions("LeBron was incredible. king mentality")
    assert mentions == [(player_id, "lebron")]
