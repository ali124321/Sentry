from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/defect-risk", tags=["defect-risk"])


@router.post("/run")
async def run_defect_risk_model(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """E6 — Train the defect-risk model and score every file in code_file_metric."""
    from app.pipeline.defect_risk_model import run_defect_prediction
    result = await run_defect_prediction(db)
    return result


@router.get("/scores")
async def get_defect_risk_scores(
    repository_id: int = None,
    min_score: float = None,
    limit: int = 50,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get files ranked by defect risk score, highest first."""
    query = """
        SELECT filename, repository_id, defect_risk_score, defect_risk_label,
               churn_30d, complexity_score, distinct_authors_30d, defect_risk_scored_at
        FROM code_file_metric
        WHERE defect_risk_score IS NOT NULL
    """
    params = {"limit": limit}
    if repository_id:
        query += " AND repository_id = :repository_id"
        params["repository_id"] = repository_id
    if min_score is not None:
        query += " AND defect_risk_score >= :min_score"
        params["min_score"] = min_score
    query += " ORDER BY defect_risk_score DESC LIMIT :limit"

    result = await db.execute(text(query), params)
    rows = result.fetchall()
    return [
        {
            "filename": row.filename,
            "repository_id": row.repository_id,
            "defect_risk_score": float(row.defect_risk_score) if row.defect_risk_score is not None else None,
            "defect_risk_label": row.defect_risk_label,
            "churn_30d": row.churn_30d,
            "complexity_score": float(row.complexity_score) if row.complexity_score is not None else None,
            "distinct_authors_30d": row.distinct_authors_30d,
            "scored_at": str(row.defect_risk_scored_at) if row.defect_risk_scored_at else None,
        }
        for row in rows
    ]


@router.get("/watchlist")
async def get_risk_watchlist(
    repository_id: int = None,
    limit: int = 20,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ranked watchlist of files by predicted defect risk, for code review prioritization."""
    query = """
        SELECT
            filename, repository_id, defect_risk_score, defect_risk_label,
            churn_30d, churn_90d, complexity_score, distinct_authors_30d,
            commit_count_90d, defect_risk_scored_at
        FROM code_file_metric
        WHERE defect_risk_score IS NOT NULL
    """
    params = {"limit": limit}
    if repository_id:
        query += " AND repository_id = :repository_id"
        params["repository_id"] = repository_id
    query += " ORDER BY defect_risk_score DESC LIMIT :limit"

    result = await db.execute(text(query), params)
    rows = result.fetchall()

    watchlist = [
        {
            "rank": i + 1,
            "filename": row.filename,
            "repository_id": row.repository_id,
            "risk_score": round(float(row.defect_risk_score), 4) if row.defect_risk_score is not None else None,
            "risk_level": (
                "high" if row.defect_risk_score >= 0.7
                else "medium" if row.defect_risk_score >= 0.4
                else "low"
            ) if row.defect_risk_score is not None else None,
            "is_known_buggy": row.defect_risk_label,
            "churn_30d": row.churn_30d,
            "churn_90d": row.churn_90d,
            "complexity_score": float(row.complexity_score) if row.complexity_score is not None else None,
            "distinct_authors_30d": row.distinct_authors_30d,
            "commit_count_90d": row.commit_count_90d,
            "scored_at": str(row.defect_risk_scored_at) if row.defect_risk_scored_at else None,
        }
        for i, row in enumerate(rows)
    ]

    return {
        "total": len(watchlist),
        "note": "Files require code-quality scanners and defect-risk model run (E6) before scores appear here.",
        "watchlist": watchlist,
    }