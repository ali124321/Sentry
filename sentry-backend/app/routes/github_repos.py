from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.auth.dependencies import get_current_user
from app.core.config import settings
import httpx

router = APIRouter(prefix="/api/v1/github", tags=["GitHub Repos"])

@router.get("/repos")
async def get_repos(current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            "https://api.github.com/user/repos?per_page=100&sort=updated",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch repos")
    return res.json()

@router.get("/repos/{owner}/{repo}/commits")
async def get_commits(owner: str, repo: str, current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=100",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch commits")
    return res.json()

@router.get("/repos/{owner}/{repo}/contributors")
async def get_contributors(owner: str, repo: str, current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contributors",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch contributors")
    return res.json()

@router.get("/repos/{owner}/{repo}/languages")
async def get_languages(owner: str, repo: str, current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/languages",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch languages")
    return res.json()

@router.get("/repos/{owner}/{repo}/pulls")
async def get_pulls(owner: str, repo: str, current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=50",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch PRs")
    return res.json()

@router.get("/repos/{owner}/{repo}/issues")
async def get_issues(owner: str, repo: str, current_user=Depends(get_current_user)):
    async with httpx.AsyncClient() as client:
        res = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/issues?state=all&per_page=50",
            headers={
                "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
                "Accept": "application/vnd.github+json",
            },
        )
    if res.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch issues")
    return res.json()