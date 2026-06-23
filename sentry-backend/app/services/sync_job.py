import os
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.pipeline.github_sync import sync_github

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


# ── Job 1: GitHub Sync ───────────────────────────────────────────────────────

async def run_github_sync():
    """Idempotent GitHub sync — mine commits, PRs, CI, deployments."""
    repo_name = os.getenv("GITHUB_REPO")
    local_clone_path = os.getenv("GITHUB_LOCAL_CLONE_PATH")

    if not repo_name or not local_clone_path:
        logger.warning("GITHUB_REPO or GITHUB_LOCAL_CLONE_PATH not set — skipping sync")
        return

    started_at = datetime.utcnow()
    logger.info(f"[SCHEDULER] Starting GitHub sync for {repo_name}")

    async with AsyncSessionLocal() as db:
        await db.execute(text("""
            INSERT INTO sync_status (id, job_name, status, started_at)
            VALUES (gen_random_uuid(), 'github_sync', 'running', :started_at)
        """), {"started_at": started_at})
        await db.commit()

        try:
            await sync_github(db, repo_name, local_clone_path)
            await db.execute(text("""
                UPDATE sync_status SET status = 'success', finished_at = NOW()
                WHERE job_name = 'github_sync' AND status = 'running'
            """))
            await db.commit()
            logger.info("[SCHEDULER] GitHub sync complete")
        except Exception as e:
            await db.execute(text("""
                UPDATE sync_status
                SET status = 'failed', finished_at = NOW(), error_message = :error
                WHERE job_name = 'github_sync' AND status = 'running'
            """), {"error": str(e)})
            await db.commit()
            logger.error(f"[SCHEDULER] GitHub sync failed: {e}")


# ── Job 2: Access Log Refresh ────────────────────────────────────────────────

async def run_occupancy_refresh():
    """Refresh occupancy materialized views after new access events."""
    logger.info("[SCHEDULER] Refreshing occupancy views")
    async with AsyncSessionLocal() as db:
        try:
            from app.pipeline.occupancy_views import refresh_occupancy_views
            await refresh_occupancy_views(db)
            await db.execute(text("""
                INSERT INTO sync_status (id, job_name, status, started_at, finished_at)
                VALUES (gen_random_uuid(), 'occupancy_refresh', 'success', NOW(), NOW())
            """))
            await db.commit()
            logger.info("[SCHEDULER] Occupancy refresh complete")
        except Exception as e:
            logger.error(f"[SCHEDULER] Occupancy refresh failed: {e}")


# ── Job 3: DORA Views Refresh ─────────────────────────────────────────────────

async def run_dora_refresh():
    """Refresh DORA materialized views."""
    logger.info("[SCHEDULER] Refreshing DORA views")
    async with AsyncSessionLocal() as db:
        try:
            from app.pipeline.dora_views import refresh_dora_views
            await refresh_dora_views(db)
            await db.execute(text("""
                INSERT INTO sync_status (id, job_name, status, started_at, finished_at)
                VALUES (gen_random_uuid(), 'dora_refresh', 'success', NOW(), NOW())
            """))
            await db.commit()
            logger.info("[SCHEDULER] DORA refresh complete")
        except Exception as e:
            logger.error(f"[SCHEDULER] DORA refresh failed: {e}")


# ── Job 4: Anomaly Scoring ────────────────────────────────────────────────────

async def run_anomaly_scoring():
    """Run Isolation Forest anomaly scoring job."""
    logger.info("[SCHEDULER] Running anomaly scoring")
    async with AsyncSessionLocal() as db:
        try:
            from app.pipeline.isolation_forest_model import run_anomaly_scoring_job
            result = await run_anomaly_scoring_job(db)
            await db.execute(text("""
                INSERT INTO sync_status
                    (id, job_name, status, started_at, finished_at, rows_synced)
                VALUES
                    (gen_random_uuid(), 'anomaly_scoring', 'success', NOW(), NOW(), :rows)
            """), {"rows": result.get("anomalies_found", 0)})
            await db.commit()
            logger.info(f"[SCHEDULER] Anomaly scoring complete: {result}")
        except Exception as e:
            logger.error(f"[SCHEDULER] Anomaly scoring failed: {e}")


# ── Job 5: Defect Risk Model ──────────────────────────────────────────────────

async def run_defect_risk():
    """Retrain and score defect risk model."""
    logger.info("[SCHEDULER] Running defect risk model")
    async with AsyncSessionLocal() as db:
        try:
            from app.pipeline.defect_risk_model import run_defect_prediction
            result = await run_defect_prediction(db)
            await db.execute(text("""
                INSERT INTO sync_status
                    (id, job_name, status, started_at, finished_at, rows_synced)
                VALUES
                    (gen_random_uuid(), 'defect_risk_model', 'success', NOW(), NOW(), :rows)
            """), {"rows": result.get("files_scored", 0)})
            await db.commit()
            logger.info(f"[SCHEDULER] Defect risk model complete: {result}")
        except Exception as e:
            logger.error(f"[SCHEDULER] Defect risk model failed: {e}")


# ── Job 6: SZZ Tracing ───────────────────────────────────────────────────────

async def run_szz():
    """Run SZZ bug-introducing commit tracing."""
    local_clone_path = os.getenv("GITHUB_LOCAL_CLONE_PATH")
    if not local_clone_path:
        logger.warning("GITHUB_LOCAL_CLONE_PATH not set — skipping SZZ")
        return

    logger.info("[SCHEDULER] Running SZZ tracing")
    async with AsyncSessionLocal() as db:
        try:
            from app.pipeline.szz import run_szz_tracing
            result = await run_szz_tracing(db, local_clone_path)
            await db.execute(text("""
                INSERT INTO sync_status
                    (id, job_name, status, started_at, finished_at, rows_synced)
                VALUES
                    (gen_random_uuid(), 'szz_tracing', 'success', NOW(), NOW(), :rows)
            """), {"rows": result.get("traces_found", 0)})
            await db.commit()
            logger.info(f"[SCHEDULER] SZZ tracing complete: {result}")
        except Exception as e:
            logger.error(f"[SCHEDULER] SZZ tracing failed: {e}")


# ── Scheduler Setup ───────────────────────────────────────────────────────────

def start_scheduler():
    """
    Start the pipeline orchestration scheduler.
    
    Schedule:
    - GitHub sync          → every 6 hours
    - Occupancy refresh    → every 2 hours
    - DORA refresh         → every 6 hours
    - Anomaly scoring      → daily at 2am
    - Defect risk model    → daily at 3am
    - SZZ tracing          → daily at 4am
    
    All jobs are idempotent — safe to re-run if they fail.
    """
    scheduler.add_job(
        run_github_sync,
        trigger=IntervalTrigger(hours=6),
        id="github_sync",
        name="GitHub Sync",
        replace_existing=True,
    )
    scheduler.add_job(
        run_occupancy_refresh,
        trigger=IntervalTrigger(hours=2),
        id="occupancy_refresh",
        name="Occupancy Views Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        run_dora_refresh,
        trigger=IntervalTrigger(hours=6),
        id="dora_refresh",
        name="DORA Views Refresh",
        replace_existing=True,
    )
    scheduler.add_job(
        run_anomaly_scoring,
        trigger=CronTrigger(hour=2, minute=0),
        id="anomaly_scoring",
        name="Isolation Forest Anomaly Scoring",
        replace_existing=True,
    )
    scheduler.add_job(
        run_defect_risk,
        trigger=CronTrigger(hour=3, minute=0),
        id="defect_risk_model",
        name="Defect Risk Model",
        replace_existing=True,
    )
    scheduler.add_job(
        run_szz,
        trigger=CronTrigger(hour=4, minute=0),
        id="szz_tracing",
        name="SZZ Bug-Introducing Commit Tracing",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("Pipeline scheduler started — 6 jobs registered")


def stop_scheduler():
    scheduler.shutdown()
    logger.info("Pipeline scheduler stopped")