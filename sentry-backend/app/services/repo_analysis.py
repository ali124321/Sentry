"""
Background repository analysis service.
Clones a repo, runs GitHub sync + code quality scanners, and updates status.
"""

import asyncio
import logging
import os
from datetime import datetime
from pathlib import Path

from sqlalchemy import text
from app.core.database import AsyncSessionLocal
from app.core.config import settings
from app.pipeline.github_sync import sync_github
from app.services.scanners.orchestrator import run_all_scanners
from app.pipeline.dora_views import create_dora_views, refresh_dora_views

logger = logging.getLogger(__name__)


async def _update_status(db, repo_id: int, status: str, error: str = None):
    params = {"id": repo_id, "status": status, "error": error}
    if status == "ready":
        params["synced"] = datetime.utcnow()
        await db.execute(text("""
            UPDATE repository SET status = :status, error_message = :error,
                                  last_synced_at = :synced
            WHERE id = :id
        """), params)
    else:
        await db.execute(text("""
            UPDATE repository SET status = :status, error_message = :error
            WHERE id = :id
        """), params)
    await db.commit()


async def _run_shell(cmd: list[str], cwd: str = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"Command {cmd} failed: {stderr.decode().strip()}")
    return stdout.decode().strip()


async def analyze_repo(repo_id: int):
    """Clone repo, sync GitHub data, run scanners. Runs as a background task."""
    async with AsyncSessionLocal() as db:
        try:
            # Fetch repo + owner
            result = await db.execute(text("""
                SELECT r.*, u.github_access_token
                FROM repository r JOIN users u ON r.user_id = u.id
                WHERE r.id = :id
            """), {"id": repo_id})
            repo = result.mappings().first()
            if not repo:
                logger.error(f"Repository {repo_id} not found")
                return

            full_name = repo["github_full_name"]
            token = repo["github_access_token"]
            if not token:
                await _update_status(db, repo_id, "failed", "No GitHub token — re-login via GitHub")
                return

            # -- Clone or pull --
            await _update_status(db, repo_id, "cloning")
            base_dir = Path(settings.REPO_CLONE_BASE_DIR)
            clone_dir = base_dir / str(repo_id)
            clone_dir.parent.mkdir(parents=True, exist_ok=True)

            clone_url = f"https://{token}@github.com/{full_name}.git"

            if (clone_dir / ".git").exists():
                logger.info(f"Pulling updates for {full_name}")
                await _run_shell(["git", "pull"], cwd=str(clone_dir))
            else:
                logger.info(f"Cloning {full_name}")
                await _run_shell(["git", "clone", clone_url, str(clone_dir)])

            # Save clone path
            await db.execute(text(
                "UPDATE repository SET clone_path = :path WHERE id = :id"
            ), {"path": str(clone_dir), "id": repo_id})
            await db.commit()

            # -- Sync GitHub data --
            await _update_status(db, repo_id, "syncing")
            await sync_github(
                db,
                repo_name=full_name,
                local_clone_path=str(clone_dir),
                github_token=token,
            )

            # -- Run code quality scanners --
            await _update_status(db, repo_id, "analyzing")
            head_sha = await _run_shell(
                ["git", "rev-parse", "HEAD"], cwd=str(clone_dir)
            )
            await run_all_scanners(db, repo_id, head_sha, str(clone_dir))

            # -- Refresh DORA views --
            try:
                await create_dora_views(db)
                await refresh_dora_views(db)
            except Exception as e:
                logger.warning(f"DORA view refresh failed (non-fatal): {e}")

            # -- Done --
            await _update_status(db, repo_id, "ready")
            logger.info(f"Analysis complete for {full_name} (repo_id={repo_id})")

        except Exception as e:
            logger.error(f"Analysis failed for repo_id={repo_id}: {e}")
            try:
                await _update_status(db, repo_id, "failed", str(e)[:500])
            except Exception:
                logger.error(f"Could not update failure status for repo_id={repo_id}")
