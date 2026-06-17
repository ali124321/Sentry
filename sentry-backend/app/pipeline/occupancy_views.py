from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def create_occupancy_views(db: AsyncSession):
    """Create materialized views for occupancy aggregation."""

    # 1. Running occupancy series (+1 entry / -1 exit)
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_running_occupancy AS
        SELECT
            person_id,
            event_ts,
            direction,
            location,
            SUM(
                CASE WHEN direction = 'IN' THEN 1
                     WHEN direction = 'OUT' THEN -1
                     ELSE 0 END
            ) OVER (
                PARTITION BY location
                ORDER BY event_ts
                ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
            ) AS running_occupancy
        FROM fact_access_event
        ORDER BY event_ts;
    """))

    # 2. Daily peak occupancy per location
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_daily_peak_occupancy AS
        WITH occupancy_series AS (
            SELECT
                DATE(event_ts) AS day,
                location,
                event_ts,
                SUM(
                    CASE WHEN direction = 'IN' THEN 1
                         WHEN direction = 'OUT' THEN -1
                         ELSE 0 END
                ) OVER (
                    PARTITION BY location, DATE(event_ts)
                    ORDER BY event_ts
                    ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW
                ) AS occupancy
            FROM fact_access_event
        )
        SELECT
            day,
            location,
            MAX(occupancy) AS peak_occupancy,
            MIN(occupancy) AS min_occupancy,
            AVG(occupancy) AS avg_occupancy
        FROM occupancy_series
        GROUP BY day, location
        ORDER BY day, location;
    """))

   # 3. Mobile vs card breakdown per day
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_mobile_vs_card AS
        SELECT
            DATE(event_ts) AS day,
            location,
            CASE
                WHEN raw_event_id IS NULL THEN 'mobile'
                ELSE 'card'
            END AS access_type,
            COUNT(*) AS event_count,
            COUNT(DISTINCT person_id) AS unique_persons
        FROM fact_access_event
        GROUP BY day, location, access_type
        ORDER BY day, location, access_type;
    """))
    await db.commit()
    logger.info("Occupancy materialized views created successfully")


async def refresh_occupancy_views(db: AsyncSession):
    """Refresh all occupancy materialized views."""
    await db.execute(text("REFRESH MATERIALIZED VIEW mv_running_occupancy;"))
    await db.execute(text("REFRESH MATERIALIZED VIEW mv_daily_peak_occupancy;"))
    await db.execute(text("REFRESH MATERIALIZED VIEW mv_mobile_vs_card;"))
    await db.commit()
    logger.info("Occupancy views refreshed")


async def create_occupancy_indexes(db: AsyncSession):
    """Create indexes on materialized views for fast dashboard queries."""
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_running_occupancy_ts
        ON mv_running_occupancy (event_ts);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_running_occupancy_location
        ON mv_running_occupancy (location, event_ts);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_daily_peak_day
        ON mv_daily_peak_occupancy (day, location);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_mobile_card_day
        ON mv_mobile_vs_card (day, location);
    """))
    await db.commit()
    logger.info("Occupancy indexes created")