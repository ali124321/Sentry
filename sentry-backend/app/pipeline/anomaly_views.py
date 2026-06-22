from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def create_anomaly_views(db: AsyncSession):
    """Create views for denied-access and entry/exit imbalance detection."""

    # 1. Denied access view (placeholder — assumes a 'denied' direction or status exists)
    # Since current schema only has IN/OUT, this looks for unusual patterns:
    # rapid repeated swipes at same location without alternating direction (possible denial pattern)
    await db.execute(text("""
        CREATE OR REPLACE VIEW vw_denied_access AS
        SELECT
            f1.id AS event_id,
            f1.person_id,
            f1.event_ts,
            f1.direction,
            f1.location,
            'repeated_same_direction' AS denial_reason
        FROM fact_access_event f1
        JOIN fact_access_event f2
            ON f1.person_id = f2.person_id
            AND f1.direction = f2.direction
            AND f1.location = f2.location
            AND f2.event_ts > f1.event_ts
            AND f2.event_ts <= f1.event_ts + INTERVAL '2 minutes'
            AND f1.id != f2.id
        ORDER BY f1.event_ts DESC;
    """))

    # 2. Entry/exit imbalance view — people with mismatched IN/OUT counts
    await db.execute(text("""
        CREATE OR REPLACE VIEW vw_entry_exit_imbalance AS
        SELECT
            person_id,
            DATE(event_ts) AS day,
            COUNT(*) FILTER (WHERE direction = 'IN') AS entry_count,
            COUNT(*) FILTER (WHERE direction = 'OUT') AS exit_count,
            COUNT(*) FILTER (WHERE direction = 'IN') - COUNT(*) FILTER (WHERE direction = 'OUT') AS imbalance,
            ABS(COUNT(*) FILTER (WHERE direction = 'IN') - COUNT(*) FILTER (WHERE direction = 'OUT')) AS abs_imbalance
        FROM fact_access_event
        GROUP BY person_id, DATE(event_ts)
        HAVING ABS(COUNT(*) FILTER (WHERE direction = 'IN') - COUNT(*) FILTER (WHERE direction = 'OUT')) > 0
        ORDER BY abs_imbalance DESC, day DESC;
    """))

    await db.commit()
    logger.info("Anomaly views created successfully")


async def seed_anomaly_queue_from_imbalance(db: AsyncSession):
    """Populate anomaly_review_queue from entry/exit imbalance view."""
    await db.execute(text("""
        INSERT INTO anomaly_review_queue
            (id, person_id, anomaly_type, score, status, created_at)
        SELECT
            gen_random_uuid(),
            person_id,
            'entry_exit_imbalance',
            LEAST(abs_imbalance::float / 5.0, 1.0) AS score,
            'pending',
            NOW()
        FROM vw_entry_exit_imbalance
        WHERE abs_imbalance >= 1
        ON CONFLICT DO NOTHING;
    """))
    await db.commit()
    logger.info("Anomaly queue seeded from imbalance view")