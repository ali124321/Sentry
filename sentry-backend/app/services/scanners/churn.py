"""
SENTRY-32: Churn scanner — rolling 30d/90d additions+deletions per file
using git log --numstat so no API quota is consumed.
"""

import logging
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


def _run_git(args: list[str], cwd: str) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr}")
    return result.stdout


def compute_churn(repo_path: str, days: int = 30) -> dict[str, dict]:
    """
    Returns {filename: {additions, deletions, churn, commit_count, authors}}
    for all commits in the last `days` days.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    output = _run_git(
        ["log", f"--since={since}", "--numstat", "--format=%H %ae"],
        cwd=repo_path,
    )

    file_stats: dict[str, dict] = {}
    current_author = None

    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue

        # commit header line: "<sha> <email>"
        parts = line.split()
        if len(parts) == 2 and len(parts[0]) == 40:
            current_author = parts[1]
            continue

        # numstat line: "<additions>\t<deletions>\t<filename>"
        cols = line.split("\t")
        if len(cols) != 3:
            continue

        additions_raw, deletions_raw, filename = cols
        if additions_raw == "-" or deletions_raw == "-":
            # binary file
            continue

        try:
            additions = int(additions_raw)
            deletions = int(deletions_raw)
        except ValueError:
            continue

        if filename not in file_stats:
            file_stats[filename] = {
                "additions": 0,
                "deletions": 0,
                "commit_count": 0,
                "authors": set(),
            }

        file_stats[filename]["additions"] += additions
        file_stats[filename]["deletions"] += deletions
        file_stats[filename]["commit_count"] += 1
        if current_author:
            file_stats[filename]["authors"].add(current_author)

    return file_stats


async def scan_repo_churn(
    db: AsyncSession,
    repository_id: int,
    commit_sha: str,
    repo_path: str,
) -> int:
    """
    Compute 30d and 90d churn for every file and update code_file_metric.
    Also updates churn_complexity_score = churn_30d * complexity_score.
    """
    stats_30 = compute_churn(repo_path, days=30)
    stats_90 = compute_churn(repo_path, days=90)

    all_files = set(stats_30.keys()) | set(stats_90.keys())
    count = 0

    for filename in all_files:
        s30 = stats_30.get(filename, {})
        s90 = stats_90.get(filename, {})

        churn_30d = s30.get("additions", 0) + s30.get("deletions", 0)
        churn_90d = s90.get("additions", 0) + s90.get("deletions", 0)

        await db.execute(
            text("""
            INSERT INTO code_file_metric
                (repository_id, commit_sha, filename,
                 churn_30d, churn_90d,
                 commit_count_30d, commit_count_90d,
                 distinct_authors_30d, snapshotted_at)
            VALUES
                (:repository_id, :commit_sha, :filename,
                 :churn_30d, :churn_90d,
                 :commit_count_30d, :commit_count_90d,
                 :distinct_authors_30d, now())
            ON CONFLICT (repository_id, filename, commit_sha)
            DO UPDATE SET
                churn_30d             = EXCLUDED.churn_30d,
                churn_90d             = EXCLUDED.churn_90d,
                commit_count_30d      = EXCLUDED.commit_count_30d,
                commit_count_90d      = EXCLUDED.commit_count_90d,
                distinct_authors_30d  = EXCLUDED.distinct_authors_30d,
                churn_complexity_score = EXCLUDED.churn_30d * COALESCE(code_file_metric.complexity_score, 0)
            """),
            {
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "filename": filename,
                "churn_30d": churn_30d,
                "churn_90d": churn_90d,
                "commit_count_30d": s30.get("commit_count", 0),
                "commit_count_90d": s90.get("commit_count", 0),
                "distinct_authors_30d": len(s30.get("authors", set())),
            },
        )
        count += 1

    await db.commit()
    logger.info(f"[churn] repo={repository_id} commit={commit_sha[:7]} files={count}")
    return count