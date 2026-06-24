"""add github fields to users

Revision ID: a1b2c3d4e5f6
Revises: 02a36eb17423
Create Date: 2026-06-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '02a36eb17423'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add github_access_token and github_username to users table."""
    op.add_column('users', sa.Column('github_access_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('github_username', sa.String(), nullable=True))


def downgrade() -> None:
    """Remove github fields from users table."""
    op.drop_column('users', 'github_username')
    op.drop_column('users', 'github_access_token')
