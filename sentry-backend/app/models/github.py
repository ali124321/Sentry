import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class GitFileChange(Base):
    __tablename__ = "git_file_change"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    author_id: Mapped[str] = mapped_column(String, nullable=True)  # -> dim_person.person_id
    filename: Mapped[str] = mapped_column(String, nullable=False)
    additions: Mapped[int] = mapped_column(Integer, default=0)
    deletions: Mapped[int] = mapped_column(Integer, default=0)
    complexity: Mapped[int] = mapped_column(Integer, default=0)
    committed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PullRequest(Base):
    __tablename__ = "pull_request"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pr_number: Mapped[int] = mapped_column(Integer, nullable=False)
    repo: Mapped[str] = mapped_column(String, nullable=False)
    title: Mapped[str] = mapped_column(String, nullable=True)
    author_id: Mapped[str] = mapped_column(String, nullable=True)  # -> dim_person.person_id
    state: Mapped[str] = mapped_column(String, nullable=True)  # open, closed, merged
    merged: Mapped[bool] = mapped_column(Boolean, default=False)
    opened_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    merged_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class PRReview(Base):
    __tablename__ = "pr_review"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    pr_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("pull_request.id"), nullable=False)
    reviewer_id: Mapped[str] = mapped_column(String, nullable=True)  # -> dim_person.person_id
    state: Mapped[str] = mapped_column(String, nullable=True)  # approved, changes_requested, commented
    submitted_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class CICheckRun(Base):
    __tablename__ = "ci_check_run"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String, nullable=True)  # queued, in_progress, completed
    conclusion: Mapped[str] = mapped_column(String, nullable=True)  # success, failure, skipped
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Deployment(Base):
    __tablename__ = "deployment"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    sha: Mapped[str] = mapped_column(String, nullable=False, index=True)
    repo: Mapped[str] = mapped_column(String, nullable=True, index=True)  # e.g. "ali124321/Sentry"
    environment: Mapped[str] = mapped_column(String, nullable=False)  # production, staging, dev
    deployer_id: Mapped[str] = mapped_column(String, nullable=True)  # -> dim_person.person_id
    status: Mapped[str] = mapped_column(String, nullable=True)  # pending, success, failure
    deployed_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())