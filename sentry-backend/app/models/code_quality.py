from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger, Boolean, CHAR, CheckConstraint,
    ForeignKey, Index, Integer, Numeric, Text, TIMESTAMP, UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base


# --------------------------------------------------------------------------- #
# code_file_metric                                                             #
# --------------------------------------------------------------------------- #

class CodeFileMetric(Base):
    __tablename__ = "code_file_metric"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commit_sha: Mapped[str] = mapped_column(CHAR(40), nullable=False)
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # complexity
    complexity_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    cognitive_complexity: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    loc: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    loc_comment: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    functions_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    classes_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # churn windows
    churn_30d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    churn_90d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    commit_count_30d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    commit_count_90d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    distinct_authors_30d: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # composite risk signal
    churn_complexity_score: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    snapshotted_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_code_file_metric_repository_id", "repository_id"),
        Index("ix_code_file_metric_commit_sha", "commit_sha"),
        Index("ix_code_file_metric_filename", "filename"),
        Index("ix_code_file_metric_snapshotted_at", "snapshotted_at"),
        Index("uq_code_file_metric_repo_file_commit", "repository_id", "filename", "commit_sha", unique=True),
        Index("ix_code_file_metric_hotspot", "repository_id", "churn_complexity_score",
              postgresql_where="churn_complexity_score IS NOT NULL"),
    )


# --------------------------------------------------------------------------- #
# lint_finding                                                                 #
# --------------------------------------------------------------------------- #

class LintFinding(Base):
    __tablename__ = "lint_finding"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    commit_sha: Mapped[str] = mapped_column(CHAR(40), nullable=False)
    check_run_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("github_check_run.id", ondelete="SET NULL"), nullable=True
    )
    # location
    filename: Mapped[str] = mapped_column(Text, nullable=False)
    line_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    line_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    col_start: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    col_end: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # finding details
    tool: Mapped[str] = mapped_column(Text, nullable=False)
    rule_id: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    category: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # lifecycle
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    first_seen_sha: Mapped[Optional[str]] = mapped_column(CHAR(40), nullable=True)
    resolved_sha: Mapped[Optional[str]] = mapped_column(CHAR(40), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    check_run: Mapped[Optional["GithubCheckRun"]] = relationship("GithubCheckRun")

    __table_args__ = (
        CheckConstraint("severity IN ('error','warning','info','hint')", name="ck_lint_finding_severity"),
        CheckConstraint("status IN ('open','resolved','suppressed')", name="ck_lint_finding_status"),
        Index("ix_lint_finding_repository_id", "repository_id"),
        Index("ix_lint_finding_commit_sha", "commit_sha"),
        Index("ix_lint_finding_filename", "filename"),
        Index("ix_lint_finding_tool_rule", "tool", "rule_id"),
        Index("ix_lint_finding_severity", "severity"),
        Index("ix_lint_finding_status", "status"),
        Index("ix_lint_finding_open", "repository_id", "severity", "ingested_at",
              postgresql_where="status = 'open'"),
    )


# --------------------------------------------------------------------------- #
# secret_scan_alert                                                            #
# --------------------------------------------------------------------------- #

class SecretScanAlert(Base):
    __tablename__ = "secret_scan_alert"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    github_alert_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    repository_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    author_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("dim_person.id", ondelete="SET NULL"), nullable=True
    )
    # what was found
    secret_type: Mapped[str] = mapped_column(Text, nullable=False)
    secret_type_display: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    tool: Mapped[str] = mapped_column(Text, nullable=False, server_default="github")
    # location
    filename: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    commit_sha: Mapped[Optional[str]] = mapped_column(CHAR(40), nullable=True)
    blob_sha: Mapped[Optional[str]] = mapped_column(CHAR(40), nullable=True)
    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # validity
    validity: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    # lifecycle
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default="open")
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_by_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("dim_person.id", ondelete="SET NULL"), nullable=True
    )
    resolved_at: Mapped[Optional[datetime]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    push_protection_bypassed: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    push_protection_bypassed_by_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("dim_person.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now(), nullable=False)

    author: Mapped[Optional["DimPerson"]] = relationship("DimPerson", foreign_keys=[author_id])
    resolved_by: Mapped[Optional["DimPerson"]] = relationship("DimPerson", foreign_keys=[resolved_by_id])
    push_protection_bypassed_by: Mapped[Optional["DimPerson"]] = relationship("DimPerson", foreign_keys=[push_protection_bypassed_by_id])

    __table_args__ = (
        CheckConstraint("state IN ('open','resolved','dismissed')", name="ck_secret_scan_alert_state"),
        CheckConstraint("validity IN ('active','inactive','unknown') OR validity IS NULL", name="ck_secret_scan_alert_validity"),
        Index("ix_secret_scan_alert_repository_id", "repository_id"),
        Index("ix_secret_scan_alert_author_id", "author_id"),
        Index("ix_secret_scan_alert_secret_type", "secret_type"),
        Index("ix_secret_scan_alert_state", "state"),
        Index("ix_secret_scan_alert_created_at", "created_at"),
        Index("ix_secret_scan_alert_open", "repository_id", "created_at",
              postgresql_where="state = 'open'"),
        Index("uq_secret_scan_alert_github", "repository_id", "github_alert_number",
              unique=True, postgresql_where="github_alert_number IS NOT NULL"),
    )