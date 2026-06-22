from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db
from app.models.anomaly import AnomalyReviewQueue
from app.schemas.anomaly import AnomalyReviewUpdate

router = APIRouter(prefix="/api/v1/anomalies", tags=["anomalies"])


@router.post("/setup")
async def setup_anomaly_views(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create anomaly detection views."""
    from app.pipeline.anomaly_views import create_anomaly_views
    await create_anomaly_views(db)
    return {"message": "Anomaly views created successfully"}


@router.post("/seed")
async def seed_anomaly_queue(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Seed anomaly_review_queue from imbalance view."""
    from app.pipeline.anomaly_views import seed_anomaly_queue_from_imbalance
    await seed_anomaly_queue_from_imbalance(db)
    return {"message": "Anomaly queue seeded successfully"}


@router.post("/score")
async def run_anomaly_scoring(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Run the Isolation Forest anomaly scoring job. Never auto-acts — only flags for human review."""
    from app.pipeline.isolation_forest_model import run_anomaly_scoring_job
    result = await run_anomaly_scoring_job(db)
    return {
        "message": "Anomaly scoring complete. Flagged events written to review queue for human review only.",
        **result,
    }


@router.get("/denied-access")
async def get_denied_access(
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Get denied access patterns."""
    result = await db.execute(text("SELECT * FROM vw_denied_access LIMIT 100"))
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


@router.get("/entry-exit-imbalance")
async def get_entry_exit_imbalance(
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Get entry/exit imbalance patterns."""
    result = await db.execute(text("SELECT * FROM vw_entry_exit_imbalance LIMIT 100"))
    rows = result.fetchall()
    return [dict(row._mapping) for row in rows]


@router.get("/queue")
async def get_anomaly_queue(
    status: str = None,
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Get items in the anomaly review queue."""
    query = select(AnomalyReviewQueue).order_by(AnomalyReviewQueue.score.desc())
    if status:
        query = query.where(AnomalyReviewQueue.status == status)
    result = await db.execute(query)
    items = result.scalars().all()
    return items


@router.patch("/queue/{anomaly_id}")
async def review_anomaly(
    anomaly_id: str,
    data: AnomalyReviewUpdate,
    current_user=Depends(require_role("admin", "leadership", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Review/update an anomaly item."""
    from datetime import datetime
    result = await db.execute(
        select(AnomalyReviewQueue).where(AnomalyReviewQueue.id == anomaly_id)
    )
    anomaly = result.scalar_one_or_none()
    if not anomaly:
        raise HTTPException(status_code=404, detail="Anomaly not found")

    anomaly.status = data.status
    anomaly.review_notes = data.review_notes
    anomaly.reviewer_id = str(current_user.id)
    anomaly.reviewed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(anomaly)
    return anomaly