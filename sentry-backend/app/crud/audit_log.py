from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.audit_log import AuditLog

async def create_audit_log(
    db: AsyncSession,
    user_id: str,
    user_email: str,
    action: str,
    target_id: str = None,
    details: str = None,
):
    log = AuditLog(
        user_id=user_id,
        user_email=user_email,
        action=action,
        target_id=target_id,
        details=details,
    )
    db.add(log)
    await db.commit()
    await db.refresh(log)
    return log

async def get_audit_logs(db: AsyncSession) -> list[AuditLog]:
    result = await db.execute(
        select(AuditLog).order_by(AuditLog.created_at.desc()).limit(50)
    )
    return result.scalars().all()