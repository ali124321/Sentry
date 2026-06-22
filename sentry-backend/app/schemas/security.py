from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from uuid import UUID

class AnomalyQueueItem(BaseModel):
    id: UUID
    event_ref: str
    score: float
    status: str
    reviewer: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}

class AnomalyAction(BaseModel):
    reviewer: str
    note: Optional[str] = None

class DeniedAccessMetric(BaseModel):
    total_events: int
    denied_count: int
    denied_rate_pct: float

class ImbalanceMetric(BaseModel):
    person_id: str
    entry_count: int
    exit_count: int
    imbalance: int