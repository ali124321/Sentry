from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_role
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/seed", tags=["seed"])


@router.post("/test-data")
async def seed_test_data(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """DEV ONLY — seed realistic fake test data across access events, GitHub, and code quality tables."""
    from app.pipeline.seed_test_data import seed_all_test_data
    result = await seed_all_test_data(db)
    return result