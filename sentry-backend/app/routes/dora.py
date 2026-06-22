from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/dora", tags=["dora"])


@router.post("/setup")
async def setup_dora_views(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create DORA materialized views and indexes."""
    from app.pipeline.dora_views import create_dora_views, create_dora_indexes
    await create_dora_views(db)
    await create_dora_indexes(db)
    return {
        "message": "DORA views and indexes created successfully",
        "note": "Lead time is approximated as PR opened_at -> merged_at since no commit-to-PR linkage exists yet."
    }


@router.post("/refresh")
async def refresh_views(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Refresh DORA materialized views."""
    from app.pipeline.dora_views import refresh_dora_views
    await refresh_dora_views(db)
    return {"message": "DORA views refreshed"}


@router.get("/deployment-frequency")
async def get_deployment_frequency(
    environment: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT day, environment, deployment_count, successful_count, failed_count FROM mv_deployment_frequency WHERE 1=1"
    params = {}
    if environment:
        query += " AND environment = :environment"
        params["environment"] = environment
    query += " ORDER BY day DESC LIMIT 90"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "day": str(row.day),
            "environment": row.environment,
            "deployment_count": row.deployment_count,
            "successful_count": row.successful_count,
            "failed_count": row.failed_count,
        }
        for row in rows
    ]


@router.get("/lead-time")
async def get_lead_time(
    repo: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT day, repo, pr_number, author_id, lead_time_hours FROM mv_lead_time WHERE 1=1"
    params = {}
    if repo:
        query += " AND repo = :repo"
        params["repo"] = repo
    query += " ORDER BY day DESC LIMIT 100"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return {
        "note": "Approximated as PR opened_at -> merged_at (no commit-to-PR linkage table yet)",
        "data": [
            {
                "day": str(row.day),
                "repo": row.repo,
                "pr_number": row.pr_number,
                "author_id": row.author_id,
                "lead_time_hours": round(float(row.lead_time_hours), 2),
            }
            for row in rows
        ]
    }


@router.get("/change-failure-rate")
async def get_change_failure_rate(
    environment: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT day, environment, total_deployments, failed_deployments, change_failure_rate_pct FROM mv_change_failure_rate WHERE 1=1"
    params = {}
    if environment:
        query += " AND environment = :environment"
        params["environment"] = environment
    query += " ORDER BY day DESC LIMIT 90"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "day": str(row.day),
            "environment": row.environment,
            "total_deployments": row.total_deployments,
            "failed_deployments": row.failed_deployments,
            "change_failure_rate_pct": float(row.change_failure_rate_pct) if row.change_failure_rate_pct is not None else 0,
        }
        for row in rows
    ]


@router.get("/time-to-restore")
async def get_time_to_restore(
    environment: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT environment, failed_at, restored_at, restore_time_hours FROM mv_time_to_restore WHERE 1=1"
    params = {}
    if environment:
        query += " AND environment = :environment"
        params["environment"] = environment
    query += " ORDER BY failed_at DESC LIMIT 50"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "environment": row.environment,
            "failed_at": str(row.failed_at),
            "restored_at": str(row.restored_at),
            "restore_time_hours": round(float(row.restore_time_hours), 2),
        }
        for row in rows
    ]


@router.get("/review-latency")
async def get_review_latency(
    repo: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = "SELECT repo, pr_number, author_id, opened_at, first_review_at, review_latency_hours FROM mv_review_latency WHERE 1=1"
    params = {}
    if repo:
        query += " AND repo = :repo"
        params["repo"] = repo
    query += " ORDER BY opened_at DESC LIMIT 100"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "repo": row.repo,
            "pr_number": row.pr_number,
            "author_id": row.author_id,
            "opened_at": str(row.opened_at),
            "first_review_at": str(row.first_review_at),
            "review_latency_hours": round(float(row.review_latency_hours), 2),
        }
        for row in rows
    ]