from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from app.models.entities import Comment, PlayerDailyMetric, SentimentScore


def _weight(score: int) -> float:
    return max(1, min(score, 20))


def recompute_day(db: Session, target_date: date) -> None:
    start_dt = datetime.combine(target_date, time.min)
    end_dt = start_dt + timedelta(days=1)

    query = (
        select(SentimentScore, Comment)
        .join(Comment, Comment.id == SentimentScore.comment_id)
        .where(and_(Comment.created_utc >= start_dt, Comment.created_utc < end_dt))
    )
    rows = db.execute(query).all()

    bucket = defaultdict(list)
    terms = defaultdict(Counter)
    for sentiment, comment in rows:
        w = _weight(comment.score)
        bucket[sentiment.player_id].append((sentiment, w))
        for token in comment.body.lower().split():
            if len(token) > 4:
                terms[sentiment.player_id][token] += 1

    for player_id, vals in bucket.items():
        total_w = sum(w for _, w in vals)
        comment_count = len(vals)
        avg_compound = sum(s.compound * w for s, w in vals) / total_w
        pos_share = sum((1 if s.compound > 0.05 else 0) for s, _ in vals) / comment_count
        neg_share = sum((1 if s.compound < -0.05 else 0) for s, _ in vals) / comment_count
        top_terms = dict(terms[player_id].most_common(10))

        existing = db.execute(
            select(PlayerDailyMetric).where(
                PlayerDailyMetric.player_id == player_id,
                PlayerDailyMetric.date == target_date,
            )
        ).scalar_one_or_none()
        if existing:
            existing.comment_count = comment_count
            existing.avg_compound = avg_compound
            existing.pos_share = pos_share
            existing.neg_share = neg_share
            existing.top_terms_json = top_terms
            existing.updated_at = datetime.utcnow()
        else:
            db.add(
                PlayerDailyMetric(
                    player_id=player_id,
                    date=target_date,
                    comment_count=comment_count,
                    avg_compound=avg_compound,
                    pos_share=pos_share,
                    neg_share=neg_share,
                    top_terms_json=top_terms,
                    updated_at=datetime.utcnow(),
                )
            )
    db.commit()
