"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-02-08
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("players",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("normalized_name", sa.String(255), nullable=False, unique=True),
        sa.Column("team", sa.String(255), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_table("player_aliases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("players.id", ondelete="CASCADE"), nullable=False),
        sa.Column("alias_text", sa.String(255), nullable=False),
        sa.Column("normalized_alias", sa.String(255), nullable=False),
    )
    op.create_table("sources",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_type", "name", name="uq_source_type_name"),
    )
    op.create_table("threads",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_threads_source_external_id"),
    )
    op.create_table("comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("source_id", sa.Integer(), sa.ForeignKey("sources.id"), nullable=False),
        sa.Column("thread_id", sa.Integer(), sa.ForeignKey("threads.id"), nullable=False),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("parent_external_id", sa.String(255), nullable=True),
        sa.Column("author_hash", sa.String(64), nullable=True),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_utc", sa.DateTime(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("source_id", "external_id", name="uq_comments_source_external_id"),
    )
    op.create_table("comment_entities",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.Integer(), sa.ForeignKey("comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("mention_text", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("comment_id", "player_id", "mention_text", name="uq_comment_entity_uniq"),
    )
    op.create_table("sentiment_scores",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.Integer(), sa.ForeignKey("comments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("model_name", sa.String(255), nullable=False),
        sa.Column("compound", sa.Float(), nullable=False),
        sa.Column("pos", sa.Float(), nullable=False),
        sa.Column("neu", sa.Float(), nullable=False),
        sa.Column("neg", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("comment_id", "player_id", "model_name", name="uq_sentiment_comment_player_model"),
    )
    op.create_table("player_daily_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("comment_count", sa.Integer(), nullable=False),
        sa.Column("avg_compound", sa.Float(), nullable=False),
        sa.Column("pos_share", sa.Float(), nullable=False),
        sa.Column("neg_share", sa.Float(), nullable=False),
        sa.Column("top_terms_json", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("player_id", "date", name="uq_player_daily_player_date"),
    )


def downgrade() -> None:
    op.drop_table("player_daily_metrics")
    op.drop_table("sentiment_scores")
    op.drop_table("comment_entities")
    op.drop_table("comments")
    op.drop_table("threads")
    op.drop_table("sources")
    op.drop_table("player_aliases")
    op.drop_table("players")
