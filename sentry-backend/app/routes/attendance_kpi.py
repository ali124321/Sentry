from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/kpi/attendance", tags=["attendance-kpi"])

SUPPRESSION_THRESHOLD = 5  # suppress groups with fewer than 5 people


# ── Helper ───────────────────────────────────────────────────────────────────

def suppress_small_cohorts(rows: list[dict], group_key: str) -> list[dict]:
    """Remove cohorts with fewer than 5 people to protect privacy."""
    from collections import Counter
    counts = Counter(r[group_key] for r in rows)
    return [r for r in rows if counts[r[group_key]] >= SUPPRESSION_THRESHOLD]


# ── A1: Days Present ─────────────────────────────────────────────────────────

@router.get("/days-present")
async def a1_days_present(
    month: str = None,  # e.g. "2026-01"
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A1: Days present per person per month. Role-gated."""
    is_admin_or_above = current_user.role in ("admin", "leadership", "manager")

    if month:
        result = await db.execute(text("""
            SELECT person_id, month, days_present
            FROM mv_days_present
            WHERE TO_CHAR(month, 'YYYY-MM') = :month
            ORDER BY days_present DESC
        """), {"month": month})
    else:
        result = await db.execute(text("""
            SELECT person_id, month, days_present
            FROM mv_days_present
            ORDER BY month DESC, days_present DESC
        """))

    rows = [
        {"person_id": r.person_id, "month": str(r.month)[:7], "days_present": r.days_present}
        for r in result.fetchall()
    ]

    # Employees can only see their own data
    if not is_admin_or_above:
        rows = [r for r in rows if r["person_id"] == str(current_user.id)]
        return rows

    # Suppress small cohorts for privacy
    rows = suppress_small_cohorts(rows, "month")
    return rows


# ── A2: Average Arrival Time ─────────────────────────────────────────────────

@router.get("/avg-arrival")
async def a2_avg_arrival(
    month: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A2: Average arrival time per person per month."""
    is_admin_or_above = current_user.role in ("admin", "leadership", "manager")

    query = """
        SELECT
            person_id,
            TO_CHAR(DATE_TRUNC('month', day), 'YYYY-MM') AS month,
            AVG(EXTRACT(EPOCH FROM first_entry::time) / 3600.0) AS avg_arrival_hour,
            COUNT(*) AS days_counted
        FROM mv_first_entry_per_day
        {where}
        GROUP BY person_id, DATE_TRUNC('month', day)
        ORDER BY month DESC, avg_arrival_hour ASC
    """

    where = "WHERE TO_CHAR(day, 'YYYY-MM') = :month" if month else ""
    params = {"month": month} if month else {}

    result = await db.execute(text(query.format(where=where)), params)

    rows = [
        {
            "person_id": r.person_id,
            "month": r.month,
            "avg_arrival_hour": round(float(r.avg_arrival_hour), 2),
            "avg_arrival_time": f"{int(r.avg_arrival_hour):02d}:{int((r.avg_arrival_hour % 1) * 60):02d}",
            "days_counted": r.days_counted,
        }
        for r in result.fetchall()
    ]

    if not is_admin_or_above:
        rows = [r for r in rows if r["person_id"] == str(current_user.id)]
        return rows

    rows = suppress_small_cohorts(rows, "month")
    return rows


# ── A3: Arrival Consistency ───────────────────────────────────────────────────

@router.get("/arrival-consistency")
async def a3_arrival_consistency(
    month: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A3: Arrival consistency — std deviation of arrival time per person."""
    is_admin_or_above = current_user.role in ("admin", "leadership", "manager")

    query = """
        SELECT
            person_id,
            TO_CHAR(DATE_TRUNC('month', day), 'YYYY-MM') AS month,
            STDDEV(EXTRACT(EPOCH FROM first_entry::time) / 3600.0) AS arrival_std_hours,
            COUNT(*) AS days_counted
        FROM mv_first_entry_per_day
        {where}
        GROUP BY person_id, DATE_TRUNC('month', day)
        HAVING COUNT(*) >= 3
        ORDER BY month DESC, arrival_std_hours ASC
    """

    where = "WHERE TO_CHAR(day, 'YYYY-MM') = :month" if month else ""
    params = {"month": month} if month else {}

    result = await db.execute(text(query.format(where=where)), params)

    rows = [
        {
            "person_id": r.person_id,
            "month": r.month,
            "arrival_std_hours": round(float(r.arrival_std_hours), 3) if r.arrival_std_hours else 0.0,
            "consistency_score": round(max(0, 1 - float(r.arrival_std_hours or 0) / 2), 3),
            "days_counted": r.days_counted,
        }
        for r in result.fetchall()
    ]

    if not is_admin_or_above:
        rows = [r for r in rows if r["person_id"] == str(current_user.id)]
        return rows

    rows = suppress_small_cohorts(rows, "month")
    return rows


# ── A4: Office Session Hours ──────────────────────────────────────────────────

@router.get("/session-hours")
async def a4_session_hours(
    month: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A4: Total and average office session hours per person per month."""
    is_admin_or_above = current_user.role in ("admin", "leadership", "manager")

    query = """
        SELECT
            person_id,
            TO_CHAR(DATE_TRUNC('month', day), 'YYYY-MM') AS month,
            COUNT(*) AS sessions,
            ROUND(SUM(hours_spent)::numeric, 2) AS total_hours,
            ROUND(AVG(hours_spent)::numeric, 2) AS avg_hours_per_day
        FROM mv_daily_sessions
        WHERE hours_spent IS NOT NULL
        {and_where}
        GROUP BY person_id, DATE_TRUNC('month', day)
        ORDER BY month DESC, total_hours DESC
    """

    and_where = "AND TO_CHAR(day, 'YYYY-MM') = :month" if month else ""
    params = {"month": month} if month else {}

    result = await db.execute(text(query.format(and_where=and_where)), params)

    rows = [
        {
            "person_id": r.person_id,
            "month": r.month,
            "sessions": r.sessions,
            "total_hours": float(r.total_hours),
            "avg_hours_per_day": float(r.avg_hours_per_day),
        }
        for r in result.fetchall()
    ]

    if not is_admin_or_above:
        rows = [r for r in rows if r["person_id"] == str(current_user.id)]
        return rows

    rows = suppress_small_cohorts(rows, "month")
    return rows


# ── A5: Attendance Trend ──────────────────────────────────────────────────────

@router.get("/trend")
async def a5_attendance_trend(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A5: Monthly attendance trend across all persons with change detection."""
    if current_user.role not in ("admin", "leadership", "manager"):
        raise HTTPException(status_code=403, detail="Access denied")

    result = await db.execute(text("""
        SELECT
            TO_CHAR(month, 'YYYY-MM') AS month,
            COUNT(DISTINCT person_id) AS unique_persons,
            SUM(days_present) AS total_days,
            ROUND(AVG(days_present)::numeric, 2) AS avg_days_per_person
        FROM mv_days_present
        GROUP BY month
        ORDER BY month ASC
    """))

    rows = result.fetchall()
    trend = []
    prev_avg = None

    for r in rows:
        avg = float(r.avg_days_per_person)
        change = round(avg - prev_avg, 2) if prev_avg is not None else 0.0
        # Simple change-point: flag if change > 20% of previous
        is_change_point = abs(change) > (prev_avg * 0.2) if prev_avg else False

        trend.append({
            "month": r.month,
            "unique_persons": r.unique_persons,
            "total_days": r.total_days,
            "avg_days_per_person": avg,
            "change_from_prev": change,
            "is_change_point": is_change_point,
        })
        prev_avg = avg

    # Suppress if fewer than 5 persons in any month
    trend = [t for t in trend if t["unique_persons"] >= SUPPRESSION_THRESHOLD]
    return trend


# ── A6: Cohort Summary ────────────────────────────────────────────────────────

@router.get("/cohort-summary")
async def a6_cohort_summary(
    month: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """A6: Cohort-level attendance summary for the given month."""
    if current_user.role not in ("admin", "leadership"):
        raise HTTPException(status_code=403, detail="Access denied. Admin and leadership only.")

    params = {"month": month} if month else {}
    where = "WHERE TO_CHAR(month, 'YYYY-MM') = :month" if month else ""

    result = await db.execute(text(f"""
        SELECT
            TO_CHAR(month, 'YYYY-MM') AS month,
            COUNT(DISTINCT person_id) AS total_persons,
            SUM(days_present) AS total_days,
            ROUND(AVG(days_present)::numeric, 2) AS avg_days,
            MAX(days_present) AS max_days,
            MIN(days_present) AS min_days
        FROM mv_days_present
        {where}
        GROUP BY month
        ORDER BY month DESC
    """), params)

    rows = result.fetchall()

    # Suppress cohorts smaller than 5
    return [
        {
            "month": r.month,
            "total_persons": r.total_persons,
            "total_days": r.total_days,
            "avg_days": float(r.avg_days),
            "max_days": r.max_days,
            "min_days": r.min_days,
            "suppressed": r.total_persons < SUPPRESSION_THRESHOLD,
        }
        for r in rows
        if r.total_persons >= SUPPRESSION_THRESHOLD
    ]
