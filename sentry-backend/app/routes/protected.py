from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user
from app.crud.user import get_user_by_id
from app.schemas.user import UserResponse
from app.core.database import get_db

router = APIRouter(prefix="/api/v1", tags=["protected"])

@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user_id: str = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    user = await get_user_by_id(db, current_user_id)
    return user