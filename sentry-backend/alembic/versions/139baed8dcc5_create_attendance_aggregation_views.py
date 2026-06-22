from alembic import op

revision = '139baed8dcc5'
down_revision = '4a80f0ebc33d'
branch_labels = None
depends_on = None


def upgrade():
    # View: first entry per person per day
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_first_entry_per_day AS
        SELECT
            person_id,
            DATE(event_ts) AS day,
            MIN(event_ts) AS first_entry
        FROM fact_access_event
        WHERE direction = 'IN'
        GROUP BY person_id, DATE(event_ts);
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_first_entry_person_day
        ON mv_first_entry_per_day (person_id, day);
    """)

    # View: days present per person per month
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_days_present AS
        SELECT
            person_id,
            DATE_TRUNC('month', event_ts) AS month,
            COUNT(DISTINCT DATE(event_ts)) AS days_present
        FROM fact_access_event
        WHERE direction = 'IN'
        GROUP BY person_id, DATE_TRUNC('month', event_ts);
    """)

    op.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS ix_mv_days_present_person_month
        ON mv_days_present (person_id, month);
    """)

    # View: session duration per person per day
    op.execute("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_sessions AS
        SELECT
            e_in.person_id,
            DATE(e_in.event_ts) AS day,
            e_in.event_ts AS entry_time,
            e_out.event_ts AS exit_time,
            EXTRACT(EPOCH FROM (e_out.event_ts - e_in.event_ts)) / 3600.0 AS hours_spent
        FROM fact_access_event e_in
        LEFT JOIN LATERAL (
            SELECT event_ts
            FROM fact_access_event e_out
            WHERE e_out.person_id = e_in.person_id
              AND e_out.direction = 'OUT'
              AND e_out.event_ts > e_in.event_ts
              AND DATE(e_out.event_ts) = DATE(e_in.event_ts)
            ORDER BY e_out.event_ts ASC
            LIMIT 1
        ) e_out ON true
        WHERE e_in.direction = 'IN';
    """)

    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_mv_daily_sessions_person_day
        ON mv_daily_sessions (person_id, day);
    """)


def downgrade():
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_daily_sessions;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_days_present;")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS mv_first_entry_per_day;")