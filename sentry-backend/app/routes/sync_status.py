from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role
from app.core.database import get_db
from app.pipeline.github_sync import get_github_client
import asyncio

router = APIRouter(prefix="/api/v1/sync", tags=["sync"])


@router.get("/status")
async def get_sync_status(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get last sync run and GitHub rate limit budget."""

    result = await db.execute(text("""
        SELECT job_name, status, started_at, finished_at, rows_synced, error_message
        FROM sync_status
        ORDER BY created_at DESC
        LIMIT 5
    """))
    rows = result.fetchall()

    last_runs = [
        {
            "job_name": row.job_name,
            "status": row.status,
            "started_at": str(row.started_at) if row.started_at else None,
            "finished_at": str(row.finished_at) if row.finished_at else None,
            "rows_synced": row.rows_synced,
            "error_message": row.error_message,
        }
        for row in rows
    ]

    rate_limit_info = {}
    try:
        gh = get_github_client()
        rate = gh.get_rate_limit()
        rate_limit_info = {
            "remaining": rate.core.remaining,
            "limit": rate.core.limit,
            "reset_at": str(rate.core.reset),
            "used": rate.core.limit - rate.core.remaining,
        }
    except Exception as e:
        try:
            gh = get_github_client()
            user = gh.get_user()
            rate_limit_info = {
                "status": "connected",
                "user": user.login,
                "note": "Rate limit details unavailable in this PyGithub version",
            }
        except Exception as e2:
            rate_limit_info = {"error": str(e2)}

    return {
        "last_runs": last_runs,
        "rate_limit": rate_limit_info,
        "next_scheduled": "Every 6 hours",
    }


@router.post("/trigger")
async def trigger_sync(
    current_user=Depends(require_role("admin")),
):
    """Manually trigger a GitHub sync."""
    from app.services.sync_job import run_github_sync
    asyncio.create_task(run_github_sync())
    return {"message": "GitHub sync triggered in background"}