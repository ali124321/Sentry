"""add defect risk score column

Revision ID: 02a36eb17423
Revises: 4dd10d9572ef
Create Date: 2026-06-23 11:01:36.797367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '02a36eb17423'
down_revision: Union[str, Sequence[str], None] = '4dd10d9572ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('code_file_metric', sa.Column('defect_risk_score', sa.Numeric(5, 4), nullable=True))
    op.add_column('code_file_metric', sa.Column('defect_risk_label', sa.Boolean(), nullable=True))
    op.add_column('code_file_metric', sa.Column('defect_risk_scored_at', sa.TIMESTAMP(timezone=True), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('code_file_metric', 'defect_risk_scored_at')
    op.drop_column('code_file_metric', 'defect_risk_label')
    op.drop_column('code_file_metric', 'defect_risk_score')