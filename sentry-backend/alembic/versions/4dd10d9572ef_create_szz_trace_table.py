"""create szz trace table

Revision ID: 4dd10d9572ef
Revises: sentry_031
Create Date: 2026-06-22 16:22:50.114023

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4dd10d9572ef'
down_revision: Union[str, Sequence[str], None] = 'sentry_031'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('szz_trace',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('fix_sha', sa.String(), nullable=False),
    sa.Column('bug_introducing_sha', sa.String(), nullable=True),
    sa.Column('filename', sa.String(), nullable=False),
    sa.Column('fix_author_id', sa.String(), nullable=True),
    sa.Column('bug_author_id', sa.String(), nullable=True),
    sa.Column('fix_committed_at', sa.DateTime(), nullable=True),
    sa.Column('bug_committed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_szz_trace_fix_sha'), 'szz_trace', ['fix_sha'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_szz_trace_fix_sha'), table_name='szz_trace')
    op.drop_table('szz_trace')