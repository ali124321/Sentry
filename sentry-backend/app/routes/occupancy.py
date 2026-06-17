from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/occupancy", tags=["occupancy"])


@router.post("/setup")
async def setup_occupancy_views(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create occupancy materialized views and indexes."""
    from app.pipeline.occupancy_views import create_occupancy_views, create_occupancy_indexes
    await create_occupancy_views(db)
    await create_occupancy_indexes(db)
    return {"message": "Occupancy views and indexes created successfully"}


@router.post("/refresh")
async def refresh_views(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Refresh occupancy materialized views."""
    from app.pipeline.occupancy_views import refresh_occupancy_views
    await refresh_occupancy_views(db)
    return {"message": "Occupancy views refreshed"}


@router.get("/running")
async def get_running_occupancy(
    location: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get running occupancy series."""
    query = """
        SELECT person_id, event_ts, direction, location, running_occupancy
        FROM mv_running_occupancy
        WHERE 1=1
    """
    params = {}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " ORDER BY event_ts DESC LIMIT 100"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "person_id": row.person_id,
            "event_ts": str(row.event_ts),
            "direction": row.direction,
            "location": row.location,
            "running_occupancy": row.running_occupancy,
        }
        for row in rows
    ]


@router.get("/daily-peak")
async def get_daily_peak(
    location: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get daily peak occupancy."""
    query = """
        SELECT day, location, peak_occupancy, min_occupancy, avg_occupancy
        FROM mv_daily_peak_occupancy
        WHERE 1=1
    """
    params = {}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " ORDER BY day DESC LIMIT 30"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "day": str(row.day),
            "location": row.location,
            "peak_occupancy": row.peak_occupancy,
            "min_occupancy": row.min_occupancy,
            "avg_occupancy": float(row.avg_occupancy) if row.avg_occupancy else None,
        }
        for row in rows
    ]


@router.get("/mobile-vs-card")
async def get_mobile_vs_card(
    location: str = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get mobile vs card access breakdown."""
    query = """
        SELECT day, location, access_type, event_count, unique_persons
        FROM mv_mobile_vs_card
        WHERE 1=1
    """
    params = {}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " ORDER BY day DESC LIMIT 60"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "day": str(row.day),
            "location": row.location,
            "access_type": row.access_type,
            "event_count": row.event_count,
            "unique_persons": row.unique_persons,
        }
        for row in rows
    ]