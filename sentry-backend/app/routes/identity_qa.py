"""
SENTRY-15: Identity QA API
Endpoints for reviewing identity resolution quality before trusting KPIs.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/identity-qa", tags=["Identity QA"])


# -------------------------------------------------------
# 1. Unresolved badge code %
# -------------------------------------------------------
@router.get("/unresolved-codes")
async def unresolved_codes(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT
            COUNT(*) AS total_events,
            COUNT(*) FILTER (
                WHERE person_id::text NOT IN (SELECT person_id::text FROM dim_person)
            ) AS unresolved_count
        FROM fact_access_event
    """))
    row = result.mappings().one()
    total = int(row["total_events"] or 0)
    unresolved = int(row["unresolved_count"] or 0)
    pct = round((unresolved / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_events": total,
        "unresolved_count": unresolved,
        "unresolved_pct": pct,
        "threshold_pct": 2.0,
        "status": "OK" if pct <= 2.0 else "WARNING",
    }


# -------------------------------------------------------
# 2. Duplicate identity clusters
# -------------------------------------------------------
@router.get("/duplicate-clusters")
async def duplicate_clusters(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        SELECT
            lower(email) AS email,
            COUNT(*) AS id_count,
            array_agg(person_id::text) AS person_ids
        FROM dim_person
        GROUP BY lower(email)
        HAVING COUNT(*) > 1
    """))
    rows = result.mappings().all()
    clusters = [dict(r) for r in rows]

    return {
        "duplicate_clusters": len(clusters),
        "status": "OK" if len(clusters) == 0 else "WARNING",
        "clusters": clusters,
    }


# -------------------------------------------------------
# 3. Unmatched sessions
# -------------------------------------------------------
@router.get("/unmatched-sessions")
async def unmatched_sessions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(text("""
        WITH ins AS (
            SELECT person_id, event_ts
            FROM fact_access_event
            WHERE direction = 'IN'
        ),
        outs AS (
            SELECT person_id, event_ts
            FROM fact_access_event
            WHERE direction = 'OUT'
        ),
        unmatched AS (
            SELECT i.person_id, i.event_ts AS entry_ts
            FROM ins i
            LEFT JOIN outs o
                ON i.person_id::text = o.person_id::text
                AND o.event_ts > i.event_ts
                AND o.event_ts <= i.event_ts + INTERVAL '16 hours'
            WHERE o.person_id IS NULL
        )
        SELECT
            (SELECT COUNT(*) FROM ins) AS total_entries,
            COUNT(*) AS unmatched_count,
            array_agg(DISTINCT person_id::text) AS unmatched_person_ids
        FROM unmatched
    """))
    row = result.mappings().one()
    total = int(row["total_entries"] or 0)
    unmatched = int(row["unmatched_count"] or 0)
    pct = round((unmatched / total) * 100, 2) if total > 0 else 0.0

    return {
        "total_entries": total,
        "unmatched_count": unmatched,
        "unmatched_pct": pct,
        "threshold_pct": 5.0,
        "status": "OK" if pct <= 5.0 else "WARNING",
        "unmatched_person_ids": row["unmatched_person_ids"] or [],
    }


# -------------------------------------------------------
# 4. Overall QA summary
# -------------------------------------------------------
@router.get("/summary")
async def qa_summary(db: AsyncSession = Depends(get_db)):
    unresolved = await unresolved_codes(db)
    duplicates = await duplicate_clusters(db)
    unmatched = await unmatched_sessions(db)

    all_ok = all([
        unresolved["status"] == "OK",
        duplicates["status"] == "OK",
        unmatched["status"] == "OK",
    ])

    return {
        "overall_status": "OK" if all_ok else "WARNING",
        "checks": {
            "unresolved_codes": unresolved,
            "duplicate_clusters": duplicates,
            "unmatched_sessions": unmatched,
        }
    }