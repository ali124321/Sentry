from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.auth.password import hash_password

async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()

async def get_user_by_id(db: AsyncSession, user_id: str) -> User | None:
    result = await db.execute(select(User).where(User.id == user_id))
    return result.scalar_one_or_none()

async def get_all_users(db: AsyncSession) -> list[User]:
    result = await db.execute(select(User))
    return result.scalars().all()

async def create_user(db: AsyncSession, data: UserCreate) -> User:
    user = User(
        email=data.email,
        full_name=data.full_name,
        hashed_password=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def update_user(db: AsyncSession, user_id: str, data: UserUpdate) -> User | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    if data.full_name is not None:
        user.full_name = data.full_name
    if data.role is not None:
        user.role = data.role
    await db.commit()
    await db.refresh(user)
    return user

async def disable_user(db: AsyncSession, user_id: str) -> User | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    user.is_active = False
    await db.commit()
    await db.refresh(user)
    return user

async def assign_role(db: AsyncSession, user_id: str, role: str) -> User | None:
    user = await get_user_by_id(db, user_id)
    if not user:
        return None
    user.role = role
    await db.commit()
    await db.refresh(user)
    return user