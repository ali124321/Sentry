"""create repository table

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-24 12:01:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create repository table."""
    op.create_table(
        'repository',
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('user_id', UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('github_full_name', sa.String(), nullable=False),
        sa.Column('default_branch', sa.String(), server_default='main', nullable=True),
        sa.Column('clone_path', sa.String(), nullable=True),
        sa.Column('status', sa.String(), server_default='pending', nullable=True),
        sa.Column('error_message', sa.String(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'github_full_name', name='uq_repo_user_fullname'),
    )
    op.create_index('ix_repository_user_id', 'repository', ['user_id'])


def downgrade() -> None:
    """Drop repository table."""
    op.drop_index('ix_repository_user_id', table_name='repository')
    op.drop_table('repository')
