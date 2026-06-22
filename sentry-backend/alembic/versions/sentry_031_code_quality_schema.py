"""SENTRY-31: Code quality schema — complexity, churn, lint findings, secret scan alerts

Revision ID: sentry_031
Revises: e17812dbce47
Create Date: 2026-06-22
"""

from alembic import op
import sqlalchemy as sa

revision = "sentry_031"
down_revision = "e17812dbce47"
branch_labels = None
depends_on = None


def upgrade() -> None:

    # ------------------------------------------------------------------ #
    # 1. code_file_metric — per-file complexity & churn snapshot          #
    # ------------------------------------------------------------------ #
    op.create_table(
        "code_file_metric",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("commit_sha", sa.CHAR(40), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=True),
        sa.Column("complexity_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("cognitive_complexity", sa.Numeric(10, 4), nullable=True),
        sa.Column("loc", sa.Integer(), nullable=True),
        sa.Column("loc_comment", sa.Integer(), nullable=True),
        sa.Column("functions_count", sa.Integer(), nullable=True),
        sa.Column("classes_count", sa.Integer(), nullable=True),
        sa.Column("churn_30d", sa.Integer(), nullable=True),
        sa.Column("churn_90d", sa.Integer(), nullable=True),
        sa.Column("commit_count_30d", sa.Integer(), nullable=True),
        sa.Column("commit_count_90d", sa.Integer(), nullable=True),
        sa.Column("distinct_authors_30d", sa.Integer(), nullable=True),
        sa.Column("churn_complexity_score", sa.Numeric(10, 4), nullable=True),
        sa.Column("snapshotted_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_code_file_metric_repository_id", "code_file_metric", ["repository_id"])
    op.create_index("ix_code_file_metric_commit_sha", "code_file_metric", ["commit_sha"])
    op.create_index("ix_code_file_metric_filename", "code_file_metric", ["filename"])
    op.create_index("ix_code_file_metric_snapshotted_at", "code_file_metric", ["snapshotted_at"])
    op.create_index("uq_code_file_metric_repo_file_commit", "code_file_metric",
                    ["repository_id", "filename", "commit_sha"], unique=True)
    op.create_index("ix_code_file_metric_hotspot", "code_file_metric",
                    ["repository_id", "churn_complexity_score"],
                    postgresql_where=sa.text("churn_complexity_score IS NOT NULL"))

    # ------------------------------------------------------------------ #
    # 2. lint_finding — individual lint rule violations                   #
    # ------------------------------------------------------------------ #
    op.create_table(
        "lint_finding",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("commit_sha", sa.CHAR(40), nullable=False),
        sa.Column("check_run_id", sa.BigInteger(), nullable=True,
                  comment="Ref to github_check_run.id — no FK since table may not exist yet"),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("line_start", sa.Integer(), nullable=True),
        sa.Column("line_end", sa.Integer(), nullable=True),
        sa.Column("col_start", sa.Integer(), nullable=True),
        sa.Column("col_end", sa.Integer(), nullable=True),
        sa.Column("tool", sa.Text(), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("category", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="open"),
        sa.Column("first_seen_sha", sa.CHAR(40), nullable=True),
        sa.Column("resolved_sha", sa.CHAR(40), nullable=True),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_lint_finding_repository_id", "lint_finding", ["repository_id"])
    op.create_index("ix_lint_finding_commit_sha", "lint_finding", ["commit_sha"])
    op.create_index("ix_lint_finding_filename", "lint_finding", ["filename"])
    op.create_index("ix_lint_finding_tool_rule", "lint_finding", ["tool", "rule_id"])
    op.create_index("ix_lint_finding_severity", "lint_finding", ["severity"])
    op.create_index("ix_lint_finding_status", "lint_finding", ["status"])
    op.create_index("ix_lint_finding_open", "lint_finding",
                    ["repository_id", "severity", "ingested_at"],
                    postgresql_where=sa.text("status = 'open'"))

    # ------------------------------------------------------------------ #
    # 3. secret_scan_alert — secret / credential leak alerts              #
    # ------------------------------------------------------------------ #
    op.create_table(
        "secret_scan_alert",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("github_alert_number", sa.Integer(), nullable=True),
        sa.Column("repository_id", sa.BigInteger(), nullable=False),
        sa.Column("author_id", sa.BigInteger(), nullable=True,
                  comment="Ref to dim_person.id"),
        sa.Column("secret_type", sa.Text(), nullable=False),
        sa.Column("secret_type_display", sa.Text(), nullable=True),
        sa.Column("tool", sa.Text(), nullable=False, server_default="github"),
        sa.Column("filename", sa.Text(), nullable=True),
        sa.Column("commit_sha", sa.CHAR(40), nullable=True),
        sa.Column("blob_sha", sa.CHAR(40), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=True),
        sa.Column("validity", sa.Text(), nullable=True),
        sa.Column("state", sa.Text(), nullable=False, server_default="open"),
        sa.Column("resolution", sa.Text(), nullable=True),
        sa.Column("resolved_by_id", sa.BigInteger(), nullable=True,
                  comment="Ref to dim_person.id"),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("push_protection_bypassed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("push_protection_bypassed_by_id", sa.BigInteger(), nullable=True,
                  comment="Ref to dim_person.id"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column("ingested_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_secret_scan_alert_repository_id", "secret_scan_alert", ["repository_id"])
    op.create_index("ix_secret_scan_alert_author_id", "secret_scan_alert", ["author_id"])
    op.create_index("ix_secret_scan_alert_secret_type", "secret_scan_alert", ["secret_type"])
    op.create_index("ix_secret_scan_alert_state", "secret_scan_alert", ["state"])
    op.create_index("ix_secret_scan_alert_created_at", "secret_scan_alert", ["created_at"])
    op.create_index("ix_secret_scan_alert_open", "secret_scan_alert",
                    ["repository_id", "created_at"],
                    postgresql_where=sa.text("state = 'open'"))
    op.create_index("uq_secret_scan_alert_github", "secret_scan_alert",
                    ["repository_id", "github_alert_number"], unique=True,
                    postgresql_where=sa.text("github_alert_number IS NOT NULL"))


def downgrade() -> None:
    op.drop_table("secret_scan_alert")
    op.drop_table("lint_finding")
    op.drop_table("code_file_metric")