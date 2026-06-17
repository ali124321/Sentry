from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/attendance", tags=["attendance"])


@router.post("/refresh")
async def refresh_views(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Refresh all attendance materialized views."""
    for view in ["mv_first_entry_per_day", "mv_days_present", "mv_daily_sessions"]:
        await db.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view}"))
    await db.commit()
    return {"message": "Attendance views refreshed"}


@router.get("/days-present")
async def get_days_present(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Days present per person per month."""
    result = await db.execute(text("""
        SELECT person_id, month, days_present
        FROM mv_days_present
        ORDER BY month DESC, days_present DESC
    """))
    rows = result.fetchall()
    return [{"person_id": r.person_id, "month": str(r.month), "days_present": r.days_present} for r in rows]


@router.get("/first-entry")
async def get_first_entry(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """First entry per person per day."""
    result = await db.execute(text("""
        SELECT person_id, day, first_entry
        FROM mv_first_entry_per_day
        ORDER BY day DESC
    """))
    rows = result.fetchall()
    return [{"person_id": r.person_id, "day": str(r.day), "first_entry": str(r.first_entry)} for r in rows]


@router.get("/sessions")
async def get_sessions(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Session durations per person per day."""
    result = await db.execute(text("""
        SELECT person_id, day, entry_time, exit_time, hours_spent
        FROM mv_daily_sessions
        ORDER BY day DESC
    """))
    rows = result.fetchall()
    return [
        {
            "person_id": r.person_id,
            "day": str(r.day),
            "entry_time": str(r.entry_time),
            "exit_time": str(r.exit_time) if r.exit_time else None,
            "hours_spent": round(float(r.hours_spent), 2) if r.hours_spent else None,
        }
        for r in rows
    ]