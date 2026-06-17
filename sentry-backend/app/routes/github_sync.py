from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.auth.dependencies import require_role
from app.core.database import get_db
from app.pipeline.github_sync import sync_github
import os

router = APIRouter(prefix="/api/v1/github", tags=["github"])

@router.post("/sync")
async def trigger_github_sync(
    repo_name: str,
    local_clone_path: str,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    if not os.path.exists(local_clone_path):
        raise HTTPException(status_code=400, detail=f"Local clone path not found: {local_clone_path}")
    
    try:
        await sync_github(db, repo_name, local_clone_path)
        return {"message": f"GitHub sync complete for {repo_name}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))