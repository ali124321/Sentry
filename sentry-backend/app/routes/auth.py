from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.service import Token, LoginRequest, authenticate_user, generate_token
from app.schemas.user import UserCreate, UserResponse
from app.crud.user import get_user_by_email, create_user
from app.core.database import get_db
from app.core.security import record_failed_login, is_locked_out, clear_failed_logins
from app.core.rate_limit import limiter

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(body: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await get_user_by_email(db, body.email)
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    return await create_user(db, body)


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login(request: Request, body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Check lockout before anything else
    if is_locked_out(body.email):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked after too many failed attempts. Try again in 15 minutes."
        )

    user = await get_user_by_email(db, body.email)

    if not user or not authenticate_user(body.email, body.password, user.hashed_password):
        record_failed_login(body.email)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is inactive")

    # Successful login — clear any failed attempts
    clear_failed_logins(body.email)
    return generate_token(user_id=str(user.id))