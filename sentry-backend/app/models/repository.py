import uuid
from datetime import datetime
from sqlalchemy import BigInteger, String, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class Repository(Base):
    __tablename__ = "repository"
    __table_args__ = (
        UniqueConstraint("user_id", "github_full_name", name="uq_repo_user_fullname"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    github_full_name: Mapped[str] = mapped_column(String, nullable=False)  # "owner/repo"
    default_branch: Mapped[str] = mapped_column(String, default="main")
    clone_path: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="pending")
    # status: pending | cloning | syncing | analyzing | ready | failed
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
