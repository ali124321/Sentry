from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db
from app.schemas.security import AnomalyAction

router = APIRouter(prefix="/api/v1/security", tags=["security"])


# ── C1: Denied-access rate ───────────────────────────────────────────────────

@router.get("/metrics/denied-access")
async def denied_access_rate(
    days: int = 30,
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """C1 — Denied-access rate over last N days."""
    result = await db.execute(text("""
        SELECT
            COUNT(*) AS total_events,
            COUNT(*) FILTER (WHERE direction = 'DENIED') AS denied_count
        FROM fact_access_event
        WHERE event_ts >= NOW() - (INTERVAL '1 day' * :days)
    """), {"days": days})
    row = result.fetchone()

    total = row.total_events or 0
    denied = row.denied_count or 0
    rate = round((denied / total * 100), 2) if total > 0 else 0.0

    return {
        "period_days": days,
        "total_events": total,
        "denied_count": denied,
        "denied_rate_pct": rate,
    }


# ── C1: Entry/exit imbalance ─────────────────────────────────────────────────

@router.get("/metrics/imbalance")
async def entry_exit_imbalance(
    days: int = 30,
    limit: int = 20,
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """C1 — Entry/exit imbalance per person over last N days."""
    result = await db.execute(text("""
        SELECT
            person_id,
            COUNT(*) FILTER (WHERE direction = 'IN') AS entry_count,
            COUNT(*) FILTER (WHERE direction = 'OUT') AS exit_count,
            ABS(
                COUNT(*) FILTER (WHERE direction = 'IN') -
                COUNT(*) FILTER (WHERE direction = 'OUT')
            ) AS imbalance
        FROM fact_access_event
        WHERE event_ts >= NOW() - (INTERVAL '1 day' * :days)
        GROUP BY person_id
        HAVING ABS(
            COUNT(*) FILTER (WHERE direction = 'IN') -
            COUNT(*) FILTER (WHERE direction = 'OUT')
        ) > 0
        ORDER BY imbalance DESC
        LIMIT :limit
    """), {"days": days, "limit": limit})

    rows = result.fetchall()
    return [
        {
            "person_id": row.person_id,
            "entry_count": row.entry_count,
            "exit_count": row.exit_count,
            "imbalance": row.imbalance,
        }
        for row in rows
    ]


# ── C3: Review queue — list ──────────────────────────────────────────────────

@router.get("/review-queue")
async def list_review_queue(
    status: str = "pending",
    limit: int = 50,
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """C3 — List anomaly review queue items."""
    result = await db.execute(text("""
        SELECT id, event_ref, score, status, reviewer_id, created_at
        FROM anomaly_review_queue
        WHERE status = :status
        ORDER BY score DESC
        LIMIT :limit
    """), {"status": status, "limit": limit})

    rows = result.fetchall()
    return [
        {
            "id": str(row.id),
            "event_ref": row.event_ref,
            "score": row.score,
            "status": row.status,
            "reviewer": row.reviewer_id,
            "created_at": str(row.created_at),
        }
        for row in rows
    ]


# ── C3: Review queue — confirm ───────────────────────────────────────────────

@router.patch("/review-queue/{item_id}/confirm")
async def confirm_queue_item(
    item_id: str,
    body: AnomalyAction,
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db),
):
    """C3 — Confirm an anomaly as a real security event."""
    result = await db.execute(text("""
        UPDATE anomaly_review_queue
        SET status = 'confirmed', reviewer_id = :reviewer
        WHERE id = :item_id
        RETURNING id, event_ref, score, status, reviewer_id
    """), {"item_id": item_id, "reviewer": body.reviewer})

    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Queue item not found")

    return {
        "id": str(row.id),
        "event_ref": row.event_ref,
        "score": row.score,
        "status": row.status,
        "reviewer": row.reviewer_id,
    }


# ── C3: Review queue — dismiss ───────────────────────────────────────────────

@router.patch("/review-queue/{item_id}/dismiss")
async def dismiss_queue_item(
    item_id: str,
    body: AnomalyAction,
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db),
):
    """C3 — Dismiss an anomaly as a false positive."""
    result = await db.execute(text("""
        UPDATE anomaly_review_queue
        SET status = 'dismissed', reviewer_id = :reviewer
        WHERE id = :item_id
        RETURNING id, event_ref, score, status, reviewer_id
    """), {"item_id": item_id, "reviewer": body.reviewer})

    row = result.fetchone()
    await db.commit()

    if not row:
        raise HTTPException(status_code=404, detail="Queue item not found")

    return {
        "id": str(row.id),
        "event_ref": row.event_ref,
        "score": row.score,
        "status": row.status,
        "reviewer": row.reviewer_id,
    }


# ── Summary stats ────────────────────────────────────────────────────────────

@router.get("/review-queue/summary")
async def queue_summary(
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Summary counts by status."""
    result = await db.execute(text("""
        SELECT status, COUNT(*) as count
        FROM anomaly_review_queue
        GROUP BY status
    """))
    rows = result.fetchall()
    return {row.status: row.count for row in rows}