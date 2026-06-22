from pydantic import BaseModel
from datetime import datetime
from typing import Optional
import uuid


class AnomalyReviewUpdate(BaseModel):
    status: str  # reviewed, dismissed, confirmed
    review_notes: Optional[str] = None


class AnomalyResponse(BaseModel):
    id: uuid.UUID
    event_ref: Optional[uuid.UUID] = None
    person_id: Optional[str] = None
    anomaly_type: str
    score: float
    status: str
    reviewer_id: Optional[str] = None
    review_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime

    model_config = {"from_attributes": True}