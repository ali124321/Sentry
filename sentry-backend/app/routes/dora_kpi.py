from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/dora-kpi", tags=["dora-kpi"])


# ── F1: Deployment Frequency ─────────────────────────────────────────────────

@router.get("/deployment-frequency")
async def f1_deployment_frequency(
    environment: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT environment, SUM(deployment_count) AS total_deployments,
               ROUND(AVG(deployment_count), 2) AS avg_per_day,
               COUNT(*) AS days_with_deploys
        FROM mv_deployment_frequency
        WHERE day >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if environment:
        query += " AND environment = :environment"
        params["environment"] = environment
    query += " GROUP BY environment ORDER BY total_deployments DESC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return {
        "period_days": days,
        "data": [
            {
                "environment": row.environment,
                "total_deployments": row.total_deployments,
                "avg_per_day": float(row.avg_per_day) if row.avg_per_day else 0,
                "days_with_deploys": row.days_with_deploys,
            }
            for row in rows
        ]
    }


# ── F2: Lead Time for Changes ────────────────────────────────────────────────

@router.get("/lead-time")
async def f2_lead_time(
    repo: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT repo, ROUND(AVG(lead_time_hours)::numeric, 2) AS avg_lead_time_hours,
               ROUND(MIN(lead_time_hours)::numeric, 2) AS min_lead_time_hours,
               ROUND(MAX(lead_time_hours)::numeric, 2) AS max_lead_time_hours,
               COUNT(*) AS pr_count
        FROM mv_lead_time
        WHERE day >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if repo:
        query += " AND repo = :repo"
        params["repo"] = repo
    query += " GROUP BY repo"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return {
        "period_days": days,
        "note": "Approximated as PR opened_at -> merged_at (no commit-to-PR linkage table yet)",
        "data": [
            {
                "repo": row.repo,
                "avg_lead_time_hours": float(row.avg_lead_time_hours) if row.avg_lead_time_hours else 0,
                "min_lead_time_hours": float(row.min_lead_time_hours) if row.min_lead_time_hours else 0,
                "max_lead_time_hours": float(row.max_lead_time_hours) if row.max_lead_time_hours else 0,
                "pr_count": row.pr_count,
            }
            for row in rows
        ]
    }


# ── F3: Change Failure Rate ──────────────────────────────────────────────────

@router.get("/change-failure-rate")
async def f3_change_failure_rate(
    environment: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT environment,
               SUM(total_deployments) AS total_deployments,
               SUM(failed_deployments) AS failed_deployments,
               ROUND(
                   100.0 * SUM(failed_deployments) / NULLIF(SUM(total_deployments), 0),
                   2
               ) AS change_failure_rate_pct
        FROM mv_change_failure_rate
        WHERE day >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if environment:
        query += " AND environment = :environment"
        params["environment"] = environment
    query += " GROUP BY environment"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return {
        "period_days": days,
        "data": [
            {
                "environment": row.environment,
                "total_deployments": row.total_deployments,
                "failed_deployments": row.failed_deployments,
                "change_failure_rate_pct": float(row.change_failure_rate_pct) if row.change_failure_rate_pct is not None else 0,
            }
            for row in rows
        ]
    }


# ── F4: Time to Restore ──────────────────────────────────────────────────────

@router.get("/time-to-restore")
async def f4_time_to_restore(
    environment: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT environment,
               ROUND(AVG(restore_time_hours)::numeric, 2) AS avg_restore_hours,
               ROUND(MIN(restore_time_hours)::numeric, 2) AS min_restore_hours,
               ROUND(MAX(restore_time_hours)::numeric, 2) AS max_restore_hours,
               COUNT(*) AS incidents
        FROM mv_time_to_restore
        WHERE 1=1
    """
    params = {}
    if environment:
        query += " AND environment = :environment"
        params["environment"] = environment
    query += " GROUP BY environment"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return {
        "note": "Restore time = gap between a failed deployment and the next successful one in the same environment (proxy for MTTR; no explicit incident table exists)",
        "data": [
            {
                "environment": row.environment,
                "avg_restore_hours": float(row.avg_restore_hours) if row.avg_restore_hours else 0,
                "min_restore_hours": float(row.min_restore_hours) if row.min_restore_hours else 0,
                "max_restore_hours": float(row.max_restore_hours) if row.max_restore_hours else 0,
                "incidents": row.incidents,
            }
            for row in rows
        ]
    }


# ── F5: PR Review Latency ────────────────────────────────────────────────────

@router.get("/review-latency")
async def f5_review_latency(
    repo: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT repo,
               ROUND(AVG(review_latency_hours)::numeric, 2) AS avg_latency_hours,
               ROUND(MIN(review_latency_hours)::numeric, 2) AS min_latency_hours,
               ROUND(MAX(review_latency_hours)::numeric, 2) AS max_latency_hours,
               COUNT(*) AS reviewed_pr_count
        FROM mv_review_latency
        WHERE opened_at >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if repo:
        query += " AND repo = :repo"
        params["repo"] = repo
    query += " GROUP BY repo"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return {
        "period_days": days,
        "data": [
            {
                "repo": row.repo,
                "avg_latency_hours": float(row.avg_latency_hours) if row.avg_latency_hours else 0,
                "min_latency_hours": float(row.min_latency_hours) if row.min_latency_hours else 0,
                "max_latency_hours": float(row.max_latency_hours) if row.max_latency_hours else 0,
                "reviewed_pr_count": row.reviewed_pr_count,
            }
            for row in rows
        ]
    }


# ── F7: SZZ Tracing ───────────────────────────────────────────────────────────

@router.post("/szz/run")
async def run_szz(
    repo_path: str = "/Users/ahmedalif/Desktop/sentry",
    limit_commits: int = 100,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """F7 — Run SZZ tracing: blame fix commits back to bug-introducing commits."""
    from app.pipeline.szz import run_szz_tracing
    result = await run_szz_tracing(db, repo_path, limit_commits)
    return {"message": "SZZ tracing complete", **result}


@router.get("/szz/traces")
async def get_szz_traces(
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """F7 — Get SZZ trace results: fix commit -> bug-introducing commit."""
    result = await db.execute(text("""
        SELECT fix_sha, bug_introducing_sha, filename, fix_author_id, bug_author_id,
               fix_committed_at, bug_committed_at
        FROM szz_trace
        ORDER BY fix_committed_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {
            "fix_sha": row.fix_sha,
            "bug_introducing_sha": row.bug_introducing_sha,
            "filename": row.filename,
            "fix_author_id": row.fix_author_id,
            "bug_author_id": row.bug_author_id,
            "fix_committed_at": str(row.fix_committed_at) if row.fix_committed_at else None,
            "bug_committed_at": str(row.bug_committed_at) if row.bug_committed_at else None,
        }
        for row in rows
    ]


@router.get("/szz/top-bug-introducers")
async def get_top_bug_introducers(
    limit: int = 10,
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db),
):
    """F7 — Who introduces the most bugs that later get fixed (by trace count)."""
    result = await db.execute(text("""
        SELECT bug_author_id, COUNT(*) AS bug_count
        FROM szz_trace
        WHERE bug_author_id IS NOT NULL
        GROUP BY bug_author_id
        ORDER BY bug_count DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [{"author_id": row.bug_author_id, "bug_count": row.bug_count} for row in rows]