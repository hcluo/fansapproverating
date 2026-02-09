import nltk
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.entities import Comment, CommentEntity, Player, PlayerAlias, SentimentScore, Source, Thread
from app.services.forum_ingest import parse_thread_html
from app.services.matcher import AliasEntry, PlayerMentionMatcher
from app.services.sentiment import MODEL_NAME, score_text


def test_forum_post_to_mentions_and_sentiment():
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    html = """
    <html>
      <body>
        <article class="message" id="post-333">
          <time datetime="2026-02-08T12:00:00Z"></time>
          <div class="message-body">
            <div class="bbWrapper">Jalen Green was electric tonight.</div>
          </div>
        </article>
      </body>
    </html>
    """
    posts, _ = parse_thread_html(html, "https://bbs.clutchfans.net/threads/test.123/")
    assert len(posts) == 1
    body = posts[0].body

    with SessionLocal() as db:
        player = Player(full_name="Jalen Green", normalized_name="jalen green", team="Houston Rockets")
        db.add(player)
        db.commit()
        db.refresh(player)

        alias = PlayerAlias(player_id=player.id, alias_text="Jalen Green", normalized_alias="jalen green")
        db.add(alias)
        source = Source(source_type="forum", name="clutchfans-rockets")
        db.add(source)
        db.commit()
        db.refresh(source)

        thread = Thread(
            source_id=source.id,
            external_id="123",
            title="Test thread",
            url="https://bbs.clutchfans.net/threads/test.123/",
            created_at=posts[0].created_at.replace(tzinfo=None),
            fetched_at=posts[0].created_at.replace(tzinfo=None),
        )
        db.add(thread)
        db.commit()
        db.refresh(thread)

        comment = Comment(
            source_id=source.id,
            thread_id=thread.id,
            external_id=posts[0].external_id,
            parent_external_id=None,
            author_hash=None,
            body=body,
            created_utc=posts[0].created_at.replace(tzinfo=None),
            score=0,
            url=posts[0].url,
            fetched_at=posts[0].created_at.replace(tzinfo=None),
        )
        db.add(comment)
        db.commit()
        db.refresh(comment)

        aliases = db.execute(select(PlayerAlias)).scalars().all()
        matcher = PlayerMentionMatcher(
            aliases=[AliasEntry(player_id=a.player_id, alias_text=a.alias_text, normalized_alias=a.normalized_alias) for a in aliases],
            denylist=set(),
        )
        mentions = matcher.find_mentions(body)
        assert mentions == [(player.id, "jalen green")]

        nltk.download("vader_lexicon", quiet=True)
        sentiment = score_text(body)

        for player_id, mention_text in mentions:
            db.add(CommentEntity(comment_id=comment.id, player_id=player_id, mention_text=mention_text))
            db.add(
                SentimentScore(
                    comment_id=comment.id,
                    player_id=player_id,
                    model_name=MODEL_NAME,
                    compound=sentiment["compound"],
                    pos=sentiment["pos"],
                    neu=sentiment["neu"],
                    neg=sentiment["neg"],
                )
            )
        db.commit()

    with SessionLocal() as db:
        entities = db.execute(select(CommentEntity)).scalars().all()
        scores = db.execute(select(SentimentScore)).scalars().all()

    assert len(entities) == 1
    assert len(scores) == 1
