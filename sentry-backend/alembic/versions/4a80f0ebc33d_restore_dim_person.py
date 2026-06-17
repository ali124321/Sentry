"""restore dim_person

Revision ID: 4a80f0ebc33d
Revises: b6166f98fcc5
Create Date: 2026-06-17 13:18:18.051455

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4a80f0ebc33d'
down_revision: Union[str, Sequence[str], None] = 'b6166f98fcc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Restore identity tables required by Identity QA."""

    op.create_table(
        'dim_person',
        sa.Column('person_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('github_login', sa.String(100), nullable=True),
        sa.Column('is_employee', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
        sa.Column(
            'updated_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
    )

    op.create_unique_constraint(
        'uq_dim_person_email',
        'dim_person',
        ['email']
    )

    op.create_index(
        'ix_dim_person_email',
        'dim_person',
        ['email']
    )

    op.create_table(
        'person_allowlist',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column(
            'person_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('dim_person.person_id'),
            nullable=True
        ),
        sa.Column('identifier', sa.String(255), nullable=False),
        sa.Column('account_type', sa.String(50), nullable=False),
        sa.Column('reason', sa.String(255), nullable=True),
        sa.Column(
            'created_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('NOW()'),
            nullable=False,
        ),
    )

    op.create_unique_constraint(
        'uq_person_allowlist_identifier',
        'person_allowlist',
        ['identifier']
    )


def downgrade() -> None:
    """Remove restored identity tables."""

    op.drop_constraint(
        'uq_person_allowlist_identifier',
        'person_allowlist',
        type_='unique'
    )

    op.drop_table('person_allowlist')

    op.drop_index(
        'ix_dim_person_email',
        table_name='dim_person'
    )

    op.drop_constraint(
        'uq_dim_person_email',
        'dim_person',
        type_='unique'
    )

    op.drop_table('dim_person')