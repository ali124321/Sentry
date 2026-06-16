"""SENTRY-9_access_data_pipeline_schema

Revision ID: b0242b689ea2
Revises: <your_previous_revision_id>
Create Date: 2026-06-15
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

# revision identifiers
revision = 'b0242b689ea2'
down_revision = 'd05a437cd489'  # we'll fix this next
branch_labels = None
depends_on = None


def upgrade():
    # -------------------------------------------------------
    # 1. LANDING ZONE — raw_access_events (append-only)
    # -------------------------------------------------------
    op.create_table(
        'raw_access_events',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('received_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
        sa.Column('payload', JSONB(), nullable=False),
        sa.Column('source', sa.String(100), nullable=True),
    )

    op.execute("""
        CREATE RULE raw_access_events_no_delete AS
            ON DELETE TO raw_access_events DO INSTEAD NOTHING;
    """)
    op.execute("""
        CREATE RULE raw_access_events_no_update AS
            ON UPDATE TO raw_access_events DO INSTEAD NOTHING;
    """)

    # -------------------------------------------------------
    # 2. CLEAN FACT TABLE — fact_access_event
    # -------------------------------------------------------
    op.create_table(
        'fact_access_event',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('person_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('event_ts', sa.DateTime(timezone=True), nullable=False),
        sa.Column('direction', sa.String(10), nullable=False),
        sa.Column('location', sa.String(255), nullable=True),
        sa.Column('device_id', sa.String(100), nullable=True),
        sa.Column('raw_event_id', sa.BigInteger(),
                  sa.ForeignKey('raw_access_events.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('NOW()'), nullable=False),
    )

    op.create_unique_constraint(
        'uq_fact_access_event_person_ts_direction',
        'fact_access_event',
        ['person_id', 'event_ts', 'direction']
    )

    op.create_index(
        'ix_fact_access_event_person_ts',
        'fact_access_event',
        ['person_id', 'event_ts']
    )


def downgrade():
    op.drop_index('ix_fact_access_event_person_ts', table_name='fact_access_event')
    op.drop_constraint('uq_fact_access_event_person_ts_direction', 'fact_access_event')
    op.drop_table('fact_access_event')
    op.execute("DROP RULE IF EXISTS raw_access_events_no_update ON raw_access_events;")
    op.execute("DROP RULE IF EXISTS raw_access_events_no_delete ON raw_access_events;")
    op.drop_table('raw_access_events')