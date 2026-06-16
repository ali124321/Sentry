from fastapi import APIRouter, Depends
from app.auth.dependencies import get_current_user
from app.schemas.user import UserResponse

router = APIRouter(prefix="/api/v1", tags=["protected"])

@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user

@router.get("/dashboard")
async def dashboard(current_user=Depends(get_current_user)):
    return {"message": f"Welcome, {current_user.full_name}"}