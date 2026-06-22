import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class AnomalyReviewQueue(Base):
    __tablename__ = "anomaly_review_queue"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_ref: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=True)  # -> fact_access_event.id
    person_id: Mapped[str] = mapped_column(String, nullable=True)
    anomaly_type: Mapped[str] = mapped_column(String, nullable=False)  # denied_access, entry_exit_imbalance, etc.
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    status: Mapped[str] = mapped_column(String, nullable=False, default="pending")  # pending, reviewed, dismissed, confirmed
    reviewer_id: Mapped[str] = mapped_column(String, nullable=True)  # -> users.id
    review_notes: Mapped[str] = mapped_column(String, nullable=True)
    reviewed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())