from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db
from app.core.governance import add_caveat
from collections import defaultdict

router = APIRouter(prefix="/api/v1/cohorts", tags=["cohorts"])

NO_DATA_MSG = "No cohort data found. Run POST /api/v1/cohorts/run first."


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
    try:
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
    except ProgrammingError:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

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
        if r.member_count >= 5
    ]
    return add_caveat({"cohorts": data, "total_cohorts": len(data)}, "attendance")


@router.get("/members/{cohort_label}")
async def get_cohort_members(
    cohort_label: str,
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db),
):
    """Get members of a specific cohort. Admin and leadership only."""
    try:
        result = await db.execute(text("""
            SELECT person_id, avg_arrival_hour, avg_session_hours, days_present, scored_at
            FROM person_cohort
            WHERE cohort_label = :label
            ORDER BY avg_arrival_hour ASC
        """), {"label": cohort_label})
    except ProgrammingError:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

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


@router.get("/centroids")
async def get_cohort_centroids(
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Get cohort centroids — the average behaviour of each cluster."""
    try:
        result = await db.execute(text("""
            SELECT
                cohort_label,
                COUNT(*) AS member_count,
                ROUND(AVG(avg_arrival_hour)::numeric, 2) AS centroid_arrival_hour,
                ROUND(AVG(avg_session_hours)::numeric, 2) AS centroid_session_hours,
                ROUND(MIN(avg_arrival_hour)::numeric, 2) AS min_arrival_hour,
                ROUND(MAX(avg_arrival_hour)::numeric, 2) AS max_arrival_hour,
                ROUND(MIN(avg_session_hours)::numeric, 2) AS min_session_hours,
                ROUND(MAX(avg_session_hours)::numeric, 2) AS max_session_hours,
                ROUND(STDDEV(avg_arrival_hour)::numeric, 3) AS std_arrival_hour,
                ROUND(STDDEV(avg_session_hours)::numeric, 3) AS std_session_hours
            FROM person_cohort
            GROUP BY cohort_label
            HAVING COUNT(*) >= 5
            ORDER BY centroid_arrival_hour ASC
        """))
    except ProgrammingError:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

    data = [
        {
            "cohort": r.cohort_label,
            "member_count": r.member_count,
            "centroid": {
                "avg_arrival_hour": float(r.centroid_arrival_hour),
                "avg_arrival_time": f"{int(r.centroid_arrival_hour):02d}:{int((float(r.centroid_arrival_hour) % 1) * 60):02d}",
                "avg_session_hours": float(r.centroid_session_hours),
            },
            "spread": {
                "arrival_hour_range": [float(r.min_arrival_hour), float(r.max_arrival_hour)],
                "session_hours_range": [float(r.min_session_hours), float(r.max_session_hours)],
                "arrival_std": float(r.std_arrival_hour) if r.std_arrival_hour else 0.0,
                "session_std": float(r.std_session_hours) if r.std_session_hours else 0.0,
            },
            "note": "Descriptive pattern only — not a performance indicator",
        }
        for r in rows
    ]
    return add_caveat({"centroids": data, "total_cohorts": len(data)}, "attendance")


@router.get("/assignments")
async def get_cohort_assignments(
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db),
):
    """Get all cohort assignments — which cohort each person belongs to."""
    try:
        result = await db.execute(text("""
            SELECT
                person_id,
                cluster_id,
                cohort_label,
                avg_arrival_hour,
                avg_session_hours,
                days_present,
                scored_at
            FROM person_cohort
            ORDER BY cohort_label, avg_arrival_hour ASC
        """))
    except ProgrammingError:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="No assignments found. Run POST /api/v1/cohorts/run first.")

    grouped = defaultdict(list)
    for r in rows:
        grouped[r.cohort_label].append({
            "person_id": r.person_id,
            "cluster_id": r.cluster_id,
            "avg_arrival_hour": float(r.avg_arrival_hour),
            "avg_arrival_time": f"{int(r.avg_arrival_hour):02d}:{int((float(r.avg_arrival_hour) % 1) * 60):02d}",
            "avg_session_hours": float(r.avg_session_hours),
            "days_present": r.days_present,
            "scored_at": str(r.scored_at),
        })

    result_data = {
        cohort: members
        for cohort, members in grouped.items()
        if len(members) >= 5
    }

    return add_caveat({
        "total_persons": sum(len(m) for m in result_data.values()),
        "total_cohorts": len(result_data),
        "assignments": result_data,
    }, "attendance")


@router.get("/overview")
async def get_cohort_overview(
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Full cohort overview — summary + centroids in one call."""
    try:
        result = await db.execute(text("""
            SELECT
                cohort_label,
                cluster_id,
                COUNT(*) AS member_count,
                ROUND(AVG(avg_arrival_hour)::numeric, 2) AS centroid_arrival,
                ROUND(AVG(avg_session_hours)::numeric, 2) AS centroid_session,
                ROUND(AVG(days_present)::numeric, 1) AS avg_days_present,
                MAX(scored_at) AS last_scored
            FROM person_cohort
            GROUP BY cohort_label, cluster_id
            HAVING COUNT(*) >= 5
            ORDER BY centroid_arrival ASC
        """))
    except ProgrammingError:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

    rows = result.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail=NO_DATA_MSG)

    total_persons = 0
    cohorts = []
    for r in rows:
        arrival = float(r.centroid_arrival)
        session = float(r.centroid_session)
        total_persons += r.member_count
        cohorts.append({
            "cohort": r.cohort_label,
            "cluster_id": r.cluster_id,
            "member_count": r.member_count,
            "centroid_arrival_time": f"{int(arrival):02d}:{int((arrival % 1) * 60):02d}",
            "centroid_arrival_hour": arrival,
            "centroid_session_hours": session,
            "avg_days_present": float(r.avg_days_present),
            "last_scored": str(r.last_scored),
            "note": "Descriptive pattern only — not a performance indicator",
        })

    return add_caveat({
        "total_persons_clustered": total_persons,
        "total_cohorts": len(cohorts),
        "cohorts": cohorts,
    }, "attendance")
