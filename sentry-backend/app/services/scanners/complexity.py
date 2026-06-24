"""
SENTRY-32: Cyclomatic complexity scanner using lizard.
Run against a local clone of the repo.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import lizard
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.code_quality import CodeFileMetric

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {
    ".py", ".js", ".ts", ".tsx", ".jsx", ".java", ".go",
    ".cpp", ".c", ".cs", ".rb", ".swift", ".kt",
}

LANGUAGE_MAP = {
    ".py": "python", ".js": "javascript", ".ts": "typescript",
    ".tsx": "typescript", ".jsx": "javascript", ".java": "java",
    ".go": "go", ".cpp": "cpp", ".c": "c", ".cs": "csharp",
    ".rb": "ruby", ".swift": "swift", ".kt": "kotlin",
}


def scan_file_complexity(file_path: str) -> Optional[dict]:
    """Run lizard on a single file and return aggregated metrics."""
    try:
        result = lizard.analyze_file(file_path)
        if not result:
            return None

        functions = result.function_list
        complexity_scores = [f.cyclomatic_complexity for f in functions]

        return {
            "complexity_score": max(complexity_scores) if complexity_scores else 0,
            "cognitive_complexity": sum(complexity_scores) / len(complexity_scores) if complexity_scores else 0,
            "loc": result.nloc,
            "functions_count": len(functions),
            "classes_count": len(set(
                f.filename for f in functions if hasattr(f, "top_nesting_level") and f.top_nesting_level == 0
            )),
        }
    except Exception as e:
        logger.warning(f"lizard failed on {file_path}: {e}")
        return None


async def scan_repo_complexity(
    db: AsyncSession,
    repository_id: int,
    commit_sha: str,
    repo_path: str,
    snapshotted_at: Optional[datetime] = None,
) -> int:
    """
    Walk a local repo clone, run lizard on each supported file,
    and upsert results into code_file_metric.
    Returns number of files scanned.
    """
    root = Path(repo_path)
    snapshotted_at = snapshotted_at or datetime.now(timezone.utc)
    count = 0

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue
        if file_path.suffix not in SUPPORTED_EXTENSIONS:
            continue
        # skip vendor / generated dirs
        parts = file_path.parts
        if any(p in parts for p in ("node_modules", "venv", ".git", "dist", "build", "__pycache__")):
            continue

        relative = str(file_path.relative_to(root))
        metrics = scan_file_complexity(str(file_path))
        if not metrics:
            continue

        language = LANGUAGE_MAP.get(file_path.suffix)

        await db.execute(
            text("""
            INSERT INTO code_file_metric
                (repository_id, commit_sha, filename, language,
                 complexity_score, cognitive_complexity, loc,
                 functions_count, snapshotted_at)
            VALUES
                (:repository_id, :commit_sha, :filename, :language,
                 :complexity_score, :cognitive_complexity, :loc,
                 :functions_count, :snapshotted_at)
            ON CONFLICT (repository_id, filename, commit_sha)
            DO UPDATE SET
                complexity_score     = EXCLUDED.complexity_score,
                cognitive_complexity = EXCLUDED.cognitive_complexity,
                loc                  = EXCLUDED.loc,
                functions_count      = EXCLUDED.functions_count,
                snapshotted_at       = EXCLUDED.snapshotted_at
            """),
            {
                "repository_id": repository_id,
                "commit_sha": commit_sha,
                "filename": relative,
                "language": language,
                **metrics,
                "snapshotted_at": snapshotted_at,
            },
        )
        count += 1

    await db.commit()
    logger.info(f"[complexity] repo={repository_id} commit={commit_sha[:7]} files={count}")
    return count