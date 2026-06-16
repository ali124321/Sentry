import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, UniqueConstraint, Index, func, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class RawAccessEvent(Base):
    __tablename__ = "raw_access_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    received_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class FactAccessEvent(Base):
    __tablename__ = "fact_access_event"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    person_id: Mapped[str] = mapped_column(String, nullable=False)
    event_ts: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    direction: Mapped[str] = mapped_column(String, nullable=False)  # "IN" or "OUT"
    location: Mapped[str] = mapped_column(String, nullable=True)
    raw_event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("person_id", "event_ts", "direction", name="uq_fact_access_event"),
        Index("ix_fact_access_event_person_ts", "person_id", "event_ts"),
    )