"""
SENTRY-32: Scanner orchestrator — runs all scanners for a repo sync.
Called by the GitHub sync job after cloning/pulling the repo.
"""

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.scanners.complexity import scan_repo_complexity
from app.services.scanners.churn import scan_repo_churn
from app.services.scanners.lint import scan_repo_lint
from app.services.scanners.secrets import scan_repo_secrets

logger = logging.getLogger(__name__)


async def run_all_scanners(
    db: AsyncSession,
    repository_id: int,
    commit_sha: str,
    repo_path: str,
) -> dict:
    """
    Run all code-quality scanners against a local clone.
    Returns a summary dict for the sync-status API.
    """
    results = {}

    logger.info(f"[orchestrator] starting scans repo={repository_id} commit={commit_sha[:7]}")

    try:
        results["complexity_files"] = await scan_repo_complexity(
            db, repository_id, commit_sha, repo_path
        )
    except Exception as e:
        logger.error(f"[orchestrator] complexity scanner failed: {e}")
        results["complexity_error"] = str(e)

    try:
        results["churn_files"] = await scan_repo_churn(
            db, repository_id, commit_sha, repo_path
        )
    except Exception as e:
        logger.error(f"[orchestrator] churn scanner failed: {e}")
        results["churn_error"] = str(e)

    try:
        results["lint_findings"] = await scan_repo_lint(
            db, repository_id, commit_sha, repo_path
        )
    except Exception as e:
        logger.error(f"[orchestrator] lint scanner failed: {e}")
        results["lint_error"] = str(e)

    try:
        results["secret_alerts"] = await scan_repo_secrets(
            db, repository_id, commit_sha, repo_path
        )
    except Exception as e:
        logger.error(f"[orchestrator] secrets scanner failed: {e}")
        results["secrets_error"] = str(e)

    logger.info(f"[orchestrator] done repo={repository_id} results={results}")
    return results