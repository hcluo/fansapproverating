import hashlib
import logging
from datetime import datetime, timedelta, timezone

import httpx

from celery.utils.log import get_task_logger
from sqlalchemy import select

from app.celery_app import celery_app
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.entities import Comment, CommentEntity, Player, PlayerAlias, SentimentScore, Source, Thread
from app.services.aggregation import recompute_day
from app.services.matcher import AliasEntry, PlayerMentionMatcher
from app.services.forum_ingest import (
    ForumRateLimiter,
    fetch_thread_posts,
    forum_source_name,
    iterate_recent_threads,
    parse_feed_urls,
)
from app.services.reddit_client import get_reddit
from app.services.sentiment import MODEL_NAME, score_text
from app.services.wikidata.refresh import refresh_players_from_wikidata_sync

logger = get_task_logger(__name__)


def _author_hash(name: str | None) -> str | None:
    if not name:
        return None
    return hashlib.sha256(name.encode("utf-8")).hexdigest()


def _get_or_create_source(db, name: str, source_type: str = "reddit") -> Source:
    source = db.execute(select(Source).where(Source.source_type == source_type, Source.name == name)).scalar_one_or_none()
    if source:
        return source
    source = Source(source_type=source_type, name=name)
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def reddit_ingest_task(self, subreddits: list[str] | None = None, limit_posts: int = 20, limit_comments_per_post: int = 100):
    settings = get_settings()
    subreddit_list = subreddits or [s.strip() for s in settings.ingest_subreddits.split(",") if s.strip()]

    db = SessionLocal()
    aliases = db.execute(select(PlayerAlias)).scalars().all()
    matcher = PlayerMentionMatcher(
        aliases=[AliasEntry(player_id=a.player_id, alias_text=a.alias_text, normalized_alias=a.normalized_alias) for a in aliases],
        denylist=set([w.strip() for w in settings.match_denylist.split(",") if w.strip()]),
    )

    reddit, limiter = get_reddit()

    for subreddit_name in subreddit_list:
        source = _get_or_create_source(db, subreddit_name)
        limiter.wait()
        for sub in reddit.subreddit(subreddit_name).new(limit=limit_posts):
            thread = db.execute(select(Thread).where(Thread.source_id == source.id, Thread.external_id == sub.id)).scalar_one_or_none()
            if not thread:
                thread = Thread(
                    source_id=source.id,
                    external_id=sub.id,
                    title=sub.title,
                    url=getattr(sub, "url", None),
                    created_at=datetime.utcfromtimestamp(sub.created_utc),
                    fetched_at=datetime.utcnow(),
                )
                db.add(thread)
                db.commit()
                db.refresh(thread)

            sub.comments.replace_more(limit=0)
            for c in sub.comments.list()[:limit_comments_per_post]:
                existing = db.execute(select(Comment).where(Comment.source_id == source.id, Comment.external_id == c.id)).scalar_one_or_none()
                if existing:
                    continue
                body = c.body or ""
                comment = Comment(
                    source_id=source.id,
                    thread_id=thread.id,
                    external_id=c.id,
                    parent_external_id=getattr(c, "parent_id", None),
                    author_hash=_author_hash(str(c.author) if c.author else None),
                    body=body,
                    created_utc=datetime.utcfromtimestamp(c.created_utc),
                    score=int(getattr(c, "score", 0) or 0),
                    url=f"https://reddit.com{getattr(c, 'permalink', '')}",
                    fetched_at=datetime.utcnow(),
                )
                db.add(comment)
                db.commit()
                db.refresh(comment)

                mentions = matcher.find_mentions(body)
                if not mentions:
                    continue
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

    db.close()
    return {"status": "ok", "subreddits": subreddit_list}


def _load_aliases(db, scope: str) -> list[PlayerAlias]:
    if scope == "rockets":
        return db.execute(
            select(PlayerAlias).join(Player, PlayerAlias.player_id == Player.id).where(Player.team == "Houston Rockets")
        ).scalars().all()
    return db.execute(select(PlayerAlias)).scalars().all()


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def forum_ingest_task(self):
    settings = get_settings()
    if not settings.forum_ingest_enabled:
        return {"status": "skipped", "reason": "forum ingestion disabled"}

    cutoff = datetime.now(timezone.utc) - timedelta(days=settings.forum_backfill_days)
    feed_urls = parse_feed_urls(settings.forum_rss_urls)
    limiter = ForumRateLimiter(min_interval_seconds=settings.forum_rate_limit_seconds)

    db = SessionLocal()
    aliases = _load_aliases(db, settings.forum_player_scope)
    matcher = PlayerMentionMatcher(
        aliases=[AliasEntry(player_id=a.player_id, alias_text=a.alias_text, normalized_alias=a.normalized_alias) for a in aliases],
        denylist=set([w.strip() for w in settings.match_denylist.split(",") if w.strip()]),
    )

    headers = {"User-Agent": f"{settings.reddit_user_agent} (forum-ingest)"}
    with httpx.Client(headers=headers, timeout=30) as client:
        for feed_url in feed_urls:
            source = _get_or_create_source(db, forum_source_name(feed_url), source_type="forum")
            for thread in iterate_recent_threads(client, limiter, feed_url, cutoff):
                thread_row = db.execute(
                    select(Thread).where(Thread.source_id == source.id, Thread.external_id == thread.external_id)
                ).scalar_one_or_none()
                if not thread_row:
                    thread_row = Thread(
                        source_id=source.id,
                        external_id=thread.external_id,
                        title=thread.title,
                        url=thread.url,
                        created_at=thread.created_at.replace(tzinfo=None),
                        fetched_at=datetime.utcnow(),
                    )
                    db.add(thread_row)
                    db.commit()
                    db.refresh(thread_row)
                else:
                    thread_row.fetched_at = datetime.utcnow()
                    db.commit()

                posts = fetch_thread_posts(client, limiter, thread, cutoff, max_pages=10)
                for post in posts:
                    existing = db.execute(
                        select(Comment).where(Comment.source_id == source.id, Comment.external_id == post.external_id)
                    ).scalar_one_or_none()
                    if existing:
                        continue
                    body = post.body or ""
                    comment = Comment(
                        source_id=source.id,
                        thread_id=thread_row.id,
                        external_id=post.external_id,
                        parent_external_id=None,
                        author_hash=_author_hash(post.author),
                        body=body,
                        created_utc=post.created_at.replace(tzinfo=None),
                        score=int(post.score or 0),
                        url=post.url,
                        fetched_at=datetime.utcnow(),
                    )
                    db.add(comment)
                    db.commit()
                    db.refresh(comment)

                    mentions = matcher.find_mentions(body)
                    if not mentions:
                        continue
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

    db.close()
    return {"status": "ok", "feeds": feed_urls}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def aggregate_daily_task(self, day: str = "yesterday"):
    target = datetime.utcnow().date()
    if day == "yesterday":
        target = target - timedelta(days=1)
    db = SessionLocal()
    recompute_day(db, target)
    db.close()
    return {"status": "ok", "date": str(target)}


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=5, retry_kwargs={"max_retries": 3})
def refresh_players_from_wikidata(self):
    result = refresh_players_from_wikidata_sync()
    return {"status": "ok", **result}
