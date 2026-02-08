"""add wikidata qid

Revision ID: 0002_wikidata_qid
Revises: 0001_initial
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_wikidata_qid"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("players", sa.Column("wikidata_qid", sa.String(length=32), nullable=True))
    op.create_unique_constraint("uq_players_wikidata_qid", "players", ["wikidata_qid"])
    op.create_index("ix_players_wikidata_qid", "players", ["wikidata_qid"], unique=False)
    op.create_index("ix_players_normalized_name", "players", ["normalized_name"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_players_normalized_name", table_name="players")
    op.drop_index("ix_players_wikidata_qid", table_name="players")
    op.drop_constraint("uq_players_wikidata_qid", "players", type_="unique")
    op.drop_column("players", "wikidata_qid")
