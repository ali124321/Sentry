"""
SENTRY-33: Mutation endpoints for lint findings and secret alerts.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.auth.dependencies import require_role, get_current_user

router = APIRouter(prefix="/api/code-quality", tags=["Code Quality"])


class LintStatusUpdate(BaseModel):
    status: str  # resolved | suppressed


class SecretStateUpdate(BaseModel):
    state: str        # resolved | dismissed
    resolution: str   # false_positive | wont_fix | revoked | used_in_tests


@router.patch("/lint/{finding_id}")
async def update_lint_finding(
    finding_id: int,
    body: LintStatusUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "leadership")),
):
    if body.status not in ("resolved", "suppressed"):
        raise HTTPException(400, "status must be 'resolved' or 'suppressed'")

    result = await db.execute(
        text("""
            UPDATE lint_finding
            SET status = :status
            WHERE id = :id
            RETURNING id
        """),
        {"id": finding_id, "status": body.status},
    )
    if not result.fetchone():
        raise HTTPException(404, "Finding not found")

    await db.commit()
    return {"id": finding_id, "status": body.status}


@router.patch("/secrets/{alert_id}")
async def update_secret_alert(
    alert_id: int,
    body: SecretStateUpdate,
    db: AsyncSession = Depends(get_db),
    user=Depends(require_role("admin", "leadership")),
):
    valid_states = ("resolved", "dismissed")
    valid_resolutions = ("false_positive", "wont_fix", "revoked", "used_in_tests", "pattern_deleted")

    if body.state not in valid_states:
        raise HTTPException(400, f"state must be one of {valid_states}")
    if body.resolution not in valid_resolutions:
        raise HTTPException(400, f"resolution must be one of {valid_resolutions}")

    result = await db.execute(
        text("""
            UPDATE secret_scan_alert
            SET state       = :state,
                resolution  = :resolution,
                resolved_at = now()
            WHERE id = :id
            RETURNING id
        """),
        {"id": alert_id, "state": body.state, "resolution": body.resolution},
    )
    if not result.fetchone():
        raise HTTPException(404, "Alert not found")

    await db.commit()
    return {"id": alert_id, "state": body.state, "resolution": body.resolution}