from datetime import date
from uuid import UUID
from pydantic import BaseModel


class PlayerOut(BaseModel):
    id: UUID
    full_name: str
    team: str | None
    active: bool


class PlayerMetricOut(BaseModel):
    date: date
    comment_count: int
    avg_compound: float
    pos_share: float
    neg_share: float


class NarrativeOut(BaseModel):
    date: date
    top_terms_json: dict
    summary: str
