import os
import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.pipeline.github_sync import sync_github

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


async def run_github_sync():
    """Idempotent GitHub sync job."""
    repo_name = os.getenv("GITHUB_REPO")
    local_clone_path = os.getenv("GITHUB_LOCAL_CLONE_PATH")

    if not repo_name or not local_clone_path:
        logger.warning("GITHUB_REPO or GITHUB_LOCAL_CLONE_PATH not set — skipping sync")
        return

    started_at = datetime.utcnow()
    logger.info(f"Starting scheduled GitHub sync for {repo_name}")

    async with AsyncSessionLocal() as db:
        # Record sync start
        await db.execute(text("""
            INSERT INTO sync_status (id, job_name, status, started_at)
            VALUES (gen_random_uuid(), 'github_sync', 'running', :started_at)
        """), {"started_at": started_at})
        await db.commit()

        try:
            await sync_github(db, repo_name, local_clone_path)
            finished_at = datetime.utcnow()

            # Record success
            await db.execute(text("""
                UPDATE sync_status
                SET status = 'success', finished_at = :finished_at
                WHERE job_name = 'github_sync' AND status = 'running'
            """), {"finished_at": finished_at})
            await db.commit()
            logger.info("GitHub sync job completed successfully")

        except Exception as e:
            finished_at = datetime.utcnow()
            logger.error(f"GitHub sync job failed: {e}")

            # Record failure
            await db.execute(text("""
                UPDATE sync_status
                SET status = 'failed', finished_at = :finished_at, error_message = :error
                WHERE job_name = 'github_sync' AND status = 'running'
            """), {"finished_at": finished_at, "error": str(e)})
            await db.commit()


def start_scheduler():
    """Start the background scheduler."""
    scheduler.add_job(
        run_github_sync,
        trigger=IntervalTrigger(hours=6),  # runs every 6 hours
        id="github_sync",
        name="GitHub Sync Job",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Scheduler started — GitHub sync runs every 6 hours")


def stop_scheduler():
    """Stop the background scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler stopped")