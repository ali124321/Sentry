from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.auth.dependencies import require_role, get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/ml", tags=["ml-framework"])


@router.get("/runs")
async def get_model_runs(
    limit: int = 20,
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Get recent model run history from sync_status."""
    result = await db.execute(text("""
        SELECT job_name, status, started_at, finished_at, rows_synced, error_message
        FROM sync_status
        WHERE job_name LIKE '%model%'
           OR job_name IN ('isolation_forest', 'defect_risk', 'github_sync')
        ORDER BY started_at DESC
        LIMIT :limit
    """), {"limit": limit})
    rows = result.fetchall()
    return [
        {
            "job_name": row.job_name,
            "status": row.status,
            "started_at": str(row.started_at) if row.started_at else None,
            "finished_at": str(row.finished_at) if row.finished_at else None,
            "rows_synced": row.rows_synced,
            "details": row.error_message,
        }
        for row in rows
    ]


@router.post("/drift-check")
async def run_drift_check(
    current_user=Depends(require_role("admin")),
    db: AsyncSession = Depends(get_db),
):
    """
    Run feature drift check on code_file_metric data.
    Compares oldest 50% of snapshots (reference) vs newest 50% (current).
    """
    result = await db.execute(text("""
        SELECT churn_30d, churn_90d, complexity_score,
               distinct_authors_30d, commit_count_90d, snapshotted_at
        FROM code_file_metric
        WHERE snapshotted_at IS NOT NULL
        ORDER BY snapshotted_at
    """))
    rows = result.fetchall()

    if len(rows) < 10:
        return {
            "status": "insufficient_data",
            "message": "Need at least 10 code_file_metric rows to compute drift."
        }

    import pandas as pd
    from app.pipeline.ml_framework import compute_feature_drift

    df = pd.DataFrame([dict(row._mapping) for row in rows])
    mid = len(df) // 2
    reference_df = df.iloc[:mid]
    current_df = df.iloc[mid:]

    feature_cols = ["churn_30d", "churn_90d", "complexity_score",
                    "distinct_authors_30d", "commit_count_90d"]
    drift = compute_feature_drift(reference_df, current_df, feature_cols)

    return {
        "reference_size": len(reference_df),
        "current_size": len(current_df),
        "drift_report": drift,
    }