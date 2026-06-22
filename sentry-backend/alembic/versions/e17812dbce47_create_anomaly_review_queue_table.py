"""create anomaly review queue table

Revision ID: e17812dbce47
Revises: 139baed8dcc5
Create Date: 2026-06-22 10:42:22.318676

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e17812dbce47'
down_revision: Union[str, Sequence[str], None] = '139baed8dcc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table('anomaly_review_queue',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('event_ref', sa.UUID(), nullable=True),
    sa.Column('person_id', sa.String(), nullable=True),
    sa.Column('anomaly_type', sa.String(), nullable=False),
    sa.Column('score', sa.Float(), nullable=False),
    sa.Column('status', sa.String(), nullable=False),
    sa.Column('reviewer_id', sa.String(), nullable=True),
    sa.Column('review_notes', sa.String(), nullable=True),
    sa.Column('reviewed_at', sa.DateTime(), nullable=True),
    sa.Column('created_at', sa.DateTime(), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table('anomaly_review_queue')