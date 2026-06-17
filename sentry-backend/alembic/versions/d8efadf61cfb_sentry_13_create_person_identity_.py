"""SENTRY-13_create_person_identity_dimension

Revision ID: d8efadf61cfb
Revises: 94ef18da50ea
Create Date: 2026-06-16
"""
from alembic import op
import sqlalchemy as sa

revision = 'd8efadf61cfb'
down_revision = '94ef18da50ea'
branch_labels = None
depends_on = None


def upgrade():
    # -------------------------------------------------------
    # 1. dim_person — person identity dimension
    #    Join key for every downstream metric
    # -------------------------------------------------------
    op.create_table(
        'dim_person',
        sa.Column('person_id', sa.UUID(as_uuid=True), primary_key=True),
        sa.Column('full_name', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=False),
        sa.Column('github_login', sa.String(100), nullable=True),
        sa.Column('is_employee', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )

    # UNIQUE on email
    op.create_unique_constraint(
        'uq_dim_person_email',
        'dim_person',
        ['email']
    )

    # Index on email for fast lookups
    op.create_index(
        'ix_dim_person_email',
        'dim_person',
        ['email']
    )

    # -------------------------------------------------------
    # 2. person_allowlist — bots and shared accounts
    #    Excludes these from downstream metrics
    # -------------------------------------------------------
    op.create_table(
        'person_allowlist',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('person_id', sa.UUID(as_uuid=True),
                  sa.ForeignKey('dim_person.person_id'), nullable=True),
        sa.Column('identifier', sa.String(255), nullable=False),  # email or github_login
        sa.Column('account_type', sa.String(50), nullable=False),  # 'bot' or 'shared'
        sa.Column('reason', sa.String(255), nullable=True),        # e.g. "CI bot", "team account"
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )

    # UNIQUE on identifier
    op.create_unique_constraint(
        'uq_person_allowlist_identifier',
        'person_allowlist',
        ['identifier']
    )


def downgrade():
    op.drop_constraint('uq_person_allowlist_identifier', 'person_allowlist')
    op.drop_table('person_allowlist')
    op.drop_index('ix_dim_person_email', table_name='dim_person')
    op.drop_constraint('uq_dim_person_email', 'dim_person')
    op.drop_table('dim_person')