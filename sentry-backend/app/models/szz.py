import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class SZZTrace(Base):
    __tablename__ = "szz_trace"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    fix_sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    bug_introducing_sha: Mapped[str] = mapped_column(String, nullable=True)
    filename: Mapped[str] = mapped_column(String, nullable=False)
    fix_author_id: Mapped[str] = mapped_column(String, nullable=True)
    bug_author_id: Mapped[str] = mapped_column(String, nullable=True)
    fix_committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    bug_committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())