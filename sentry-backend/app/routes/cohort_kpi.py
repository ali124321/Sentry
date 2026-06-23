from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db
from app.core.governance import add_caveat

router = APIRouter(prefix="/api/v1/cohorts", tags=["cohorts"])


@router.post("/run")
async def run_cohort_model(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """C5 — Run behavioural cohort clustering (K-means)."""
    from app.pipeline.cohort_clustering import run_cohort_clustering
    result = await run_cohort_clustering(db)
    return add_caveat(result, "attendance")


@router.get("/summary")
async def get_cohort_summary(
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Get cohort distribution summary."""
    result = await db.execute(text("""
        SELECT
            cohort_label,
            COUNT(*) AS member_count,
            ROUND(AVG(avg_arrival_hour)::numeric, 2) AS avg_arrival_hour,
            ROUND(AVG(avg_session_hours)::numeric, 2) AS avg_session_hours,
            ROUND(AVG(days_present)::numeric, 1) AS avg_days_present
        FROM person_cohort
        GROUP BY cohort_label
        ORDER BY avg_arrival_hour ASC
    """))
    rows = result.fetchall()

    if not rows:
        raise HTTPException(
            status_code=404,
            detail="No cohort data found. Run POST /api/v1/cohorts/run first."
        )

    data = [
        {
            "cohort": r.cohort_label,
            "member_count": r.member_count,
            "avg_arrival_hour": float(r.avg_arrival_hour),
            "avg_arrival_time": f"{int(r.avg_arrival_hour):02d}:{int((float(r.avg_arrival_hour) % 1) * 60):02d}",
            "avg_session_hours": float(r.avg_session_hours),
            "avg_days_present": float(r.avg_days_present),
            "note": "Descriptive pattern only — not a performance indicator",
        }
        for r in rows
        if r.member_count >= 5  # suppress small cohorts
    ]
    return add_caveat({"cohorts": data, "total_cohorts": len(data)}, "attendance")


@router.get("/members/{cohort_label}")
async def get_cohort_members(
    cohort_label: str,
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db),
):
    """Get members of a specific cohort. Admin and leadership only."""
    result = await db.execute(text("""
        SELECT person_id, avg_arrival_hour, avg_session_hours, days_present, scored_at
        FROM person_cohort
        WHERE cohort_label = :label
        ORDER BY avg_arrival_hour ASC
    """), {"label": cohort_label})
    rows = result.fetchall()

    if not rows:
        raise HTTPException(status_code=404, detail=f"Cohort '{cohort_label}' not found.")

    if len(rows) < 5:
        raise HTTPException(
            status_code=403,
            detail="Cohort suppressed — fewer than 5 members (privacy threshold)."
        )

    data = [
        {
            "person_id": r.person_id,
            "avg_arrival_hour": float(r.avg_arrival_hour),
            "avg_arrival_time": f"{int(r.avg_arrival_hour):02d}:{int((float(r.avg_arrival_hour) % 1) * 60):02d}",
            "avg_session_hours": float(r.avg_session_hours),
            "days_present": r.days_present,
            "scored_at": str(r.scored_at),
        }
        for r in rows
    ]
    return add_caveat({"cohort": cohort_label, "members": data}, "attendance")