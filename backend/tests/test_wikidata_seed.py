from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import Player, PlayerAlias
from app.services.wikidata.seed import upsert_players_from_payload


def test_wikidata_seed_idempotent_aliases():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    payload = {
        "players": [
            {
                "wikidata_qid": "Q1",
                "full_name": "Test Player",
                "normalized_name": "test player",
                "aliases": ["The Process", "TPP", "Test Player"],
            }
        ]
    }

    with SessionLocal() as db:
        upsert_players_from_payload(db, payload)

    with SessionLocal() as db:
        upsert_players_from_payload(db, payload)
        player_count = db.execute(select(Player)).scalars().all()
        alias_count = db.execute(select(PlayerAlias)).scalars().all()

    assert len(player_count) == 1
    assert len(alias_count) == 3
