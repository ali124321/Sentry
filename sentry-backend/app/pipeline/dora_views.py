from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


async def create_dora_views(db: AsyncSession):
    """
    Create DORA metric views from commit/PR/CI/deployment data.

    Limitation: lead time is approximated as PR opened_at -> merged_at
    (no commit-to-PR linkage table exists yet, so true first-commit-to-deploy
    lead time cannot be computed). This is documented and surfaced in the API.
    """

    # 1. Deployment frequency — daily deployment counts per environment
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_deployment_frequency AS
        SELECT
            DATE(deployed_at) AS day,
            environment,
            COUNT(*) AS deployment_count,
            COUNT(*) FILTER (WHERE status = 'success') AS successful_count,
            COUNT(*) FILTER (WHERE status != 'success') AS failed_count
        FROM deployment
        WHERE deployed_at IS NOT NULL
        GROUP BY day, environment
        ORDER BY day, environment;
    """))

    # 2. Lead time for changes — PR opened_at -> merged_at (approximation, see note above)
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_lead_time AS
        SELECT
            DATE(merged_at) AS day,
            repo,
            pr_number,
            author_id,
            opened_at,
            merged_at,
            EXTRACT(EPOCH FROM (merged_at - opened_at)) / 3600.0 AS lead_time_hours
        FROM pull_request
        WHERE merged = true
          AND merged_at IS NOT NULL
          AND opened_at IS NOT NULL
        ORDER BY merged_at DESC;
    """))

    # 3. Change failure rate — deployments per day vs failed deployments
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_change_failure_rate AS
        SELECT
            DATE(deployed_at) AS day,
            environment,
            COUNT(*) AS total_deployments,
            COUNT(*) FILTER (WHERE status != 'success') AS failed_deployments,
            ROUND(
                100.0 * COUNT(*) FILTER (WHERE status != 'success') / NULLIF(COUNT(*), 0),
                2
            ) AS change_failure_rate_pct
        FROM deployment
        WHERE deployed_at IS NOT NULL
        GROUP BY day, environment
        ORDER BY day, environment;
    """))

    # 4. Time to restore — gap between a failed deployment and the next successful one
    #    for the same environment (proxy for MTTR, since there's no explicit incident table)
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_time_to_restore AS
        WITH failures AS (
            SELECT
                id,
                environment,
                deployed_at AS failed_at
            FROM deployment
            WHERE status != 'success'
              AND deployed_at IS NOT NULL
        ),
        next_success AS (
            SELECT
                f.id AS failure_id,
                f.environment,
                f.failed_at,
                MIN(d.deployed_at) AS restored_at
            FROM failures f
            JOIN deployment d
                ON d.environment = f.environment
               AND d.status = 'success'
               AND d.deployed_at > f.failed_at
            GROUP BY f.id, f.environment, f.failed_at
        )
        SELECT
            environment,
            failed_at,
            restored_at,
            EXTRACT(EPOCH FROM (restored_at - failed_at)) / 3600.0 AS restore_time_hours
        FROM next_success
        ORDER BY failed_at DESC;
    """))

    # 5. Review latency — PR opened_at -> first review submitted_at
    await db.execute(text("""
        CREATE MATERIALIZED VIEW IF NOT EXISTS mv_review_latency AS
        SELECT
            pr.repo,
            pr.pr_number,
            pr.author_id,
            pr.opened_at,
            MIN(rv.submitted_at) AS first_review_at,
            EXTRACT(EPOCH FROM (MIN(rv.submitted_at) - pr.opened_at)) / 3600.0 AS review_latency_hours
        FROM pull_request pr
        JOIN pr_review rv ON rv.pr_id = pr.id
        WHERE pr.opened_at IS NOT NULL
          AND rv.submitted_at IS NOT NULL
        GROUP BY pr.id, pr.repo, pr.pr_number, pr.author_id, pr.opened_at
        ORDER BY pr.opened_at DESC;
    """))

    await db.commit()
    logger.info("DORA views created successfully")


async def refresh_dora_views(db: AsyncSession):
    """Refresh all DORA materialized views."""
    for view in [
        "mv_deployment_frequency",
        "mv_lead_time",
        "mv_change_failure_rate",
        "mv_time_to_restore",
        "mv_review_latency",
    ]:
        await db.execute(text(f"REFRESH MATERIALIZED VIEW {view};"))
    await db.commit()
    logger.info("DORA views refreshed")


async def create_dora_indexes(db: AsyncSession):
    """Create indexes on DORA materialized views for fast dashboard queries."""
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_deployment_freq_day
        ON mv_deployment_frequency (day, environment);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_lead_time_day
        ON mv_lead_time (day, repo);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_change_failure_day
        ON mv_change_failure_rate (day, environment);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_restore_env
        ON mv_time_to_restore (environment, failed_at);
    """))
    await db.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_review_latency_repo
        ON mv_review_latency (repo, opened_at);
    """))
    await db.commit()
    logger.info("DORA indexes created")