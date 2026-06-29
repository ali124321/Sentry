"""sentry_032 add repo column to deployment

Revision ID: sentry_032_repo_deployment
Revises: b2c3d4e5f6a7
Create Date: 2026-06-24
"""
from alembic import op
import sqlalchemy as sa

revision = "sentry_032_repo_deployment"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("deployment", sa.Column("repo", sa.String(), nullable=True))
    op.create_index("ix_deployment_repo", "deployment", ["repo"])


def downgrade():
    op.drop_index("ix_deployment_repo", table_name="deployment")
    op.drop_column("deployment", "repo")
