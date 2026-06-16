from pydantic import BaseModel, field_validator
from datetime import datetime
from typing import Optional
import pytz

IST = pytz.timezone("Asia/Kolkata")

class AccessEventIn(BaseModel):
    badge_code: Optional[str] = None
    person_id: str
    event_ts: datetime
    direction: str
    location: Optional[str] = None

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v.upper() not in {"IN", "OUT"}:
            raise ValueError("direction must be IN or OUT")
        return v.upper()

    @field_validator("badge_code")
    @classmethod
    def validate_badge_code(cls, v):
        if v is not None:
            return str(v).strip().upper()
        return v

class IngestResponse(BaseModel):
    message: str
    total_rows: int
    ingested: int
    skipped: int
    