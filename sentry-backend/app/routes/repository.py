"""
Repository management routes — list GitHub repos, connect, status, resync.
"""

import asyncio
import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.services.repo_analysis import analyze_repo

router = APIRouter(prefix="/api/v1/repos", tags=["repositories"])


class ConnectRequest(BaseModel):
    github_full_name: str          # "owner/repo"
    default_branch: str = "main"


# ── List GitHub repos available to the user ──────────────────────────────

@router.get("/github")
async def list_github_repos(current_user=Depends(get_current_user)):
    """Fetch the user's GitHub repositories using their stored OAuth token."""
    token = current_user.github_access_token
    if not token:
        raise HTTPException(
            status_code=400,
            detail="No GitHub token stored. Please log in via GitHub OAuth first."
        )

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.github.com/user/repos",
            params={"per_page": 100, "sort": "updated", "type": "all"},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
            },
        )
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="GitHub token expired. Please re-login via GitHub.")
        resp.raise_for_status()

    repos = resp.json()
    return [
        {
            "full_name": r["full_name"],
            "description": r.get("description"),
            "private": r["private"],
            "default_branch": r.get("default_branch", "main"),
            "language": r.get("language"),
            "updated_at": r.get("updated_at"),
        }
        for r in repos
    ]


# ── Connect a repository ─────────────────────────────────────────────────

@router.post("/connect")
async def connect_repo(
    body: ConnectRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Register a GitHub repo and start background analysis."""
    # Check if already connected
    existing = await db.execute(text("""
        SELECT id, status FROM repository
        WHERE user_id = :uid AND github_full_name = :name
    """), {"uid": str(current_user.id), "name": body.github_full_name})
    row = existing.mappings().first()
    if row:
        return {"id": row["id"], "github_full_name": body.github_full_name, "status": row["status"], "message": "Already connected"}

    # Insert
    result = await db.execute(text("""
        INSERT INTO repository (user_id, github_full_name, default_branch, status)
        VALUES (:uid, :name, :branch, 'pending')
        RETURNING id
    """), {
        "uid": str(current_user.id),
        "name": body.github_full_name,
        "branch": body.default_branch,
    })
    repo_id = result.scalar_one()
    await db.commit()

    # Launch background analysis
    asyncio.create_task(analyze_repo(repo_id))

    return {"id": repo_id, "github_full_name": body.github_full_name, "status": "pending"}


# ── List connected repos ─────────────────────────────────────────────────

@router.get("/")
async def list_repos(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all repositories connected by the current user."""
    result = await db.execute(text("""
        SELECT id, github_full_name, default_branch, status, error_message,
               last_synced_at, created_at
        FROM repository
        WHERE user_id = :uid
        ORDER BY created_at DESC
    """), {"uid": str(current_user.id)})
    rows = result.mappings().all()
    return [dict(r) for r in rows]


# ── Poll repo analysis status ────────────────────────────────────────────

@router.get("/{repo_id}/status")
async def repo_status(
    repo_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current analysis status for a repository."""
    result = await db.execute(text("""
        SELECT id, github_full_name, status, error_message, last_synced_at
        FROM repository
        WHERE id = :id AND user_id = :uid
    """), {"id": repo_id, "uid": str(current_user.id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    return dict(row)


# ── Re-trigger analysis ──────────────────────────────────────────────────

@router.post("/{repo_id}/resync")
async def resync_repo(
    repo_id: int,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Re-trigger analysis on an existing repository."""
    result = await db.execute(text("""
        SELECT id, status FROM repository
        WHERE id = :id AND user_id = :uid
    """), {"id": repo_id, "uid": str(current_user.id)})
    row = result.mappings().first()
    if not row:
        raise HTTPException(status_code=404, detail="Repository not found")
    if row["status"] in ("cloning", "syncing", "analyzing"):
        raise HTTPException(status_code=409, detail="Analysis already in progress")

    await db.execute(text(
        "UPDATE repository SET status = 'pending', error_message = NULL WHERE id = :id"
    ), {"id": repo_id})
    await db.commit()

    asyncio.create_task(analyze_repo(repo_id))
    return {"id": repo_id, "status": "pending", "message": "Re-sync started"}
