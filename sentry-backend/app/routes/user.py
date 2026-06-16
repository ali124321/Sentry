from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import get_current_user, require_role
from app.crud.user import get_all_users, update_user, disable_user, assign_role
from app.crud.audit_log import create_audit_log, get_audit_logs
from app.schemas.user import UserResponse, UserUpdate
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/users", tags=["users"])

VALID_ROLES = ["admin", "leadership", "manager", "employee"]

# Get all users — admin and leadership only
@router.get("/", response_model=list[UserResponse])
async def list_users(
    current_user=Depends(require_role("admin", "leadership")),
    db: AsyncSession = Depends(get_db)
):
    await create_audit_log(
        db, str(current_user.id), current_user.email,
        action="LIST_USERS"
    )
    return await get_all_users(db)

# Update user — admin can update anyone, users can only update themselves
@router.put("/{user_id}", response_model=UserResponse)
async def update_user_route(
    user_id: str,
    data: UserUpdate,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Only admin can update others
    if str(current_user.id) != user_id and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You can only update your own profile")
    
    # Only admin can change roles
    if data.role is not None and current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admin can change roles")

    user = await update_user(db, user_id, data)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await create_audit_log(
        db, str(current_user.id), current_user.email,
        action="UPDATE_USER",
        target_id=user_id,
        details=f"Updated fields: {list(data.model_dump(exclude_none=True).keys())}"
    )
    return user

# Disable user — admin only
@router.patch("/{user_id}/disable", response_model=UserResponse)
async def disable_user_route(
    user_id: str,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    # Admin cannot disable themselves
    if str(current_user.id) == user_id:
        raise HTTPException(status_code=400, detail="You cannot disable your own account")

    user = await disable_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await create_audit_log(
        db, str(current_user.id), current_user.email,
        action="DISABLE_USER",
        target_id=user_id,
        details=f"Disabled user {user.email}"
    )
    return user

# Assign role — admin only
@router.patch("/{user_id}/role", response_model=UserResponse)
async def assign_role_route(
    user_id: str,
    role: str,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    if role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {VALID_ROLES}")

    user = await assign_role(db, user_id, role)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    await create_audit_log(
        db, str(current_user.id), current_user.email,
        action="ASSIGN_ROLE",
        target_id=user_id,
        details=f"Assigned role '{role}' to {user.email}"
    )
    return user

# Get audit logs — admin only
@router.get("/audit-logs")
async def get_audit_logs_route(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db)
):
    return await get_audit_logs(db)

# Get current user profile — everyone
@router.get("/me", response_model=UserResponse)
async def get_me(current_user=Depends(get_current_user)):
    return current_user