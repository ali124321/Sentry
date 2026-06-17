from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.database import get_db
from app.core.config import settings
import httpx
import jwt
from datetime import datetime, timedelta
import uuid

router = APIRouter(prefix="/api/v1/auth", tags=["GitHub Auth"])

GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAIL_URL = "https://api.github.com/user/emails"


@router.get("/github")
async def github_login():
    url = f"{GITHUB_AUTH_URL}?client_id={settings.GITHUB_CLIENT_ID}&redirect_uri={settings.GITHUB_REDIRECT_URI}&scope=user:email"
    return RedirectResponse(url)


@router.get("/github/callback")
async def github_callback(code: str, db: AsyncSession = Depends(get_db)):
    async with httpx.AsyncClient() as client:
        # Exchange code for token
        token_res = await client.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": settings.GITHUB_REDIRECT_URI,
            },
        )
        token_data = token_res.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise HTTPException(status_code=400, detail="GitHub auth failed")

        # Get user info
        user_res = await client.get(
            GITHUB_USER_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        github_user = user_res.json()

        # Get email
        email_res = await client.get(
            GITHUB_EMAIL_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        emails = email_res.json()
        primary_email = next(
            (e["email"] for e in emails if e["primary"] and e["verified"]),
            None
        )

        if not primary_email:
            raise HTTPException(status_code=400, detail="No verified email from GitHub")

    # Check if user exists
    result = await db.execute(
        text("SELECT * FROM users WHERE email = :email"),
        {"email": primary_email}
    )
    user = result.mappings().first()

    if not user:
        # Create new user
        await db.execute(text("""
            INSERT INTO users (id, email, full_name, role, is_active, hashed_password, created_at)
            VALUES (:id, :email, :full_name, 'employee', true, '', NOW())
        """), {
            "id": str(uuid.uuid4()),
            "email": primary_email,
            "full_name": github_user.get("name") or github_user.get("login"),
        })
        await db.commit()

        result = await db.execute(
            text("SELECT * FROM users WHERE email = :email"),
            {"email": primary_email}
        )
        user = result.mappings().first()

    # Generate JWT
    payload = {
        "sub": user["email"],
        "exp": datetime.utcnow() + timedelta(minutes=30)
    }
    jwt_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    return RedirectResponse(
        f"http://localhost:3000/dashboard?token={jwt_token}"
    )