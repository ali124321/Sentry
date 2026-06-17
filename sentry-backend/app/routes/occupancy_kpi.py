from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import get_current_user
from app.core.database import get_db
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/occupancy-kpi", tags=["occupancy-kpi"])


# ── B1: Peak Occupancy ──────────────────────────────────────────────────────

@router.get("/peak")
async def get_peak_occupancy(
    location: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT
            location,
            MAX(peak_occupancy) AS all_time_peak,
            AVG(peak_occupancy) AS avg_daily_peak,
            MIN(peak_occupancy) AS min_daily_peak,
            COUNT(*) AS days_with_data
        FROM mv_daily_peak_occupancy
        WHERE day >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " GROUP BY location ORDER BY all_time_peak DESC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return {
        "period_days": days,
        "data": [
            {
                "location": row.location,
                "all_time_peak": row.all_time_peak,
                "avg_daily_peak": float(row.avg_daily_peak) if row.avg_daily_peak else 0,
                "min_daily_peak": row.min_daily_peak,
                "days_with_data": row.days_with_data,
            }
            for row in rows
        ]
    }


# ── B2: Daily Occupancy Trend ────────────────────────────────────────────────

@router.get("/trend")
async def get_occupancy_trend(
    location: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT day, location, peak_occupancy, avg_occupancy
        FROM mv_daily_peak_occupancy
        WHERE day >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " ORDER BY day ASC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    return {
        "period_days": days,
        "data": [
            {
                "day": str(row.day),
                "location": row.location,
                "peak_occupancy": row.peak_occupancy,
                "avg_occupancy": float(row.avg_occupancy) if row.avg_occupancy else 0,
            }
            for row in rows
        ]
    }


# ── B3: Occupancy Forecast ───────────────────────────────────────────────────

@router.get("/forecast")
async def get_occupancy_forecast(
    location: str = None,
    forecast_days: int = 7,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT day, AVG(peak_occupancy) AS peak_occupancy
        FROM mv_daily_peak_occupancy
        WHERE 1=1
    """
    params = {}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " GROUP BY day ORDER BY day ASC"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    if len(rows) < 2:
        return {
            "forecast": [],
            "note": "Not enough data for forecasting. Need at least 2 days of data."
        }

    try:
        from prophet import Prophet
        import pandas as pd

        df = pd.DataFrame([
            {"ds": str(row.day), "y": float(row.peak_occupancy)}
            for row in rows
        ])
        df["ds"] = pd.to_datetime(df["ds"])

        model = Prophet(
            interval_width=0.95,
            daily_seasonality=False,
            weekly_seasonality=True,
            yearly_seasonality=False,
        )
        model.fit(df)

        future = model.make_future_dataframe(periods=forecast_days)
        forecast = model.predict(future)

        forecast_data = forecast.tail(forecast_days)[
            ["ds", "yhat", "yhat_lower", "yhat_upper"]
        ].to_dict(orient="records")

        return {
            "location": location or "all",
            "forecast_days": forecast_days,
            "forecast": [
                {
                    "date": str(row["ds"])[:10],
                    "predicted": max(0, round(row["yhat"], 1)),
                    "lower_bound": max(0, round(row["yhat_lower"], 1)),
                    "upper_bound": max(0, round(row["yhat_upper"], 1)),
                }
                for row in forecast_data
            ]
        }

    except ImportError:
        import statistics
        values = [float(row.peak_occupancy) for row in rows]
        avg = statistics.mean(values[-7:]) if len(values) >= 7 else statistics.mean(values)
        std = statistics.stdev(values[-7:]) if len(values) >= 7 else 0

        return {
            "location": location or "all",
            "forecast_days": forecast_days,
            "method": "moving_average_fallback",
            "forecast": [
                {
                    "date": f"Day +{i+1}",
                    "predicted": round(avg, 1),
                    "lower_bound": round(max(0, avg - std), 1),
                    "upper_bound": round(avg + std, 1),
                }
                for i in range(forecast_days)
            ]
        }


# ── B4: Mobile Adoption Rate ─────────────────────────────────────────────────

@router.get("/mobile-adoption")
async def get_mobile_adoption(
    location: str = None,
    days: int = 30,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = """
        SELECT
            location,
            access_type,
            SUM(event_count) AS total_events,
            SUM(unique_persons) AS total_persons
        FROM mv_mobile_vs_card
        WHERE day >= CURRENT_DATE - CAST(:days AS INTEGER) * INTERVAL '1 day'
    """
    params = {"days": days}
    if location:
        query += " AND location = :location"
        params["location"] = location
    query += " GROUP BY location, access_type ORDER BY location, access_type"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    locations: dict = {}
    for row in rows:
        loc = row.location or "unknown"
        if loc not in locations:
            locations[loc] = {"mobile": 0, "card": 0}
        locations[loc][row.access_type] = row.total_events

    adoption = []
    for loc, counts in locations.items():
        total = counts["mobile"] + counts["card"]
        if total == 0:
            continue
        adoption.append({
            "location": loc,
            "mobile_events": counts["mobile"],
            "card_events": counts["card"],
            "total_events": total,
            "mobile_adoption_rate": round(counts["mobile"] / total * 100, 1),
            "card_adoption_rate": round(counts["card"] / total * 100, 1),
        })

    return {
        "period_days": days,
        "data": adoption
    }