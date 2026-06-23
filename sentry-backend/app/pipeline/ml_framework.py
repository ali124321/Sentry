"""
Shared ML train/test & drift-monitoring framework.
Reused by Isolation Forest, defect-risk, and future models.
"""
import logging
import json
from datetime import datetime
from typing import Callable
import pandas as pd
import numpy as np
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)


# ── Chronological Split ──────────────────────────────────────────────────────

def chronological_split(
    df: pd.DataFrame,
    time_col: str,
    test_frac: float = 0.2,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Split data by time — train on older records, test on most recent.
    Prevents future data leaking into training (standard for time-series ML).
    """
    df = df.sort_values(time_col).reset_index(drop=True)
    split_idx = int(len(df) * (1 - test_frac))
    train = df.iloc[:split_idx].copy()
    test = df.iloc[split_idx:].copy()
    logger.info(f"Chronological split: {len(train)} train / {len(test)} test rows")
    return train, test


# ── Evaluation ───────────────────────────────────────────────────────────────

def evaluate_classifier(
    y_true,
    y_pred,
    y_proba=None,
) -> dict:
    """
    Evaluate a binary classifier with precision, recall and ROC-AUC.
    Returns None for ROC-AUC if only one class present in y_true.
    """
    metrics = {
        "precision": round(float(precision_score(y_true, y_pred, zero_division=0)), 4),
        "recall": round(float(recall_score(y_true, y_pred, zero_division=0)), 4),
        "roc_auc": None,
        "test_size": int(len(y_true)),
        "positive_rate": round(float(np.mean(y_true)), 4),
    }
    if y_proba is not None and len(np.unique(y_true)) > 1:
        metrics["roc_auc"] = round(float(roc_auc_score(y_true, y_proba)), 4)
    else:
        logger.warning("ROC-AUC unavailable — only one class in test set")
    return metrics


# ── Feature Drift Monitoring ─────────────────────────────────────────────────

def compute_feature_drift(
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_cols: list[str],
    drift_threshold: float = 0.2,
) -> dict:
    """
    Detect feature drift by comparing mean/std of each feature between
    a reference (training) dataset and the current (production) dataset.
    Flags a feature as drifted if relative mean shift > drift_threshold.
    """
    drift_report = {}
    any_drift = False

    for col in feature_cols:
        if col not in reference_df.columns or col not in current_df.columns:
            continue

        ref_mean = float(reference_df[col].mean())
        cur_mean = float(current_df[col].mean())
        ref_std = float(reference_df[col].std())
        cur_std = float(current_df[col].std())

        # Relative shift in mean
        relative_shift = abs(cur_mean - ref_mean) / (abs(ref_mean) + 1e-9)
        drifted = relative_shift > drift_threshold

        if drifted:
            any_drift = True
            logger.warning(f"Feature drift detected in '{col}': "
                           f"ref_mean={ref_mean:.3f} cur_mean={cur_mean:.3f} "
                           f"shift={relative_shift:.2%}")

        drift_report[col] = {
            "ref_mean": round(ref_mean, 4),
            "cur_mean": round(cur_mean, 4),
            "ref_std": round(ref_std, 4),
            "cur_std": round(cur_std, 4),
            "relative_shift": round(relative_shift, 4),
            "drifted": drifted,
        }

    return {
        "any_drift_detected": any_drift,
        "drift_threshold": drift_threshold,
        "features": drift_report,
    }


# ── Sample Auditing ───────────────────────────────────────────────────────────

def audit_model_outputs(
    df: pd.DataFrame,
    score_col: str,
    label_col: str = None,
    sample_size: int = 10,
) -> dict:
    """
    Sample-audit model outputs:
    - Top N highest-scored rows (most risky/anomalous)
    - Bottom N lowest-scored rows (least risky)
    - Score distribution stats
    """
    if score_col not in df.columns:
        return {"error": f"Column '{score_col}' not found"}

    scores = df[score_col].dropna()

    audit = {
        "total_scored": int(len(scores)),
        "score_distribution": {
            "min": round(float(scores.min()), 4),
            "max": round(float(scores.max()), 4),
            "mean": round(float(scores.mean()), 4),
            "median": round(float(scores.median()), 4),
            "std": round(float(scores.std()), 4),
            "p25": round(float(scores.quantile(0.25)), 4),
            "p75": round(float(scores.quantile(0.75)), 4),
            "p90": round(float(scores.quantile(0.90)), 4),
            "p95": round(float(scores.quantile(0.95)), 4),
        },
        "top_high_risk": df.nlargest(sample_size, score_col)[
            [c for c in ["filename", "person_id", score_col, label_col] if c and c in df.columns]
        ].to_dict(orient="records"),
        "top_low_risk": df.nsmallest(sample_size, score_col)[
            [c for c in ["filename", "person_id", score_col, label_col] if c and c in df.columns]
        ].to_dict(orient="records"),
    }
    return audit


# ── Model Run Registry ────────────────────────────────────────────────────────

async def log_model_run(
    db: AsyncSession,
    model_name: str,
    status: str,
    metrics: dict = None,
    drift_report: dict = None,
    rows_scored: int = 0,
    error_message: str = None,
):
    """
    Log every model run to sync_status table for audit trail and scheduling.
    """
    details = json.dumps({
        "metrics": metrics,
        "drift": drift_report,
        "rows_scored": rows_scored,
    }, default=str)

    await db.execute(text("""
        INSERT INTO sync_status
            (id, job_name, status, started_at, finished_at, rows_synced, error_message)
        VALUES
            (gen_random_uuid(), :job_name, :status, NOW(), NOW(), :rows_synced, :error_message)
    """), {
        "job_name": model_name,
        "status": status,
        "rows_synced": rows_scored,
        "error_message": error_message or details,
    })
    await db.commit()
    logger.info(f"Model run logged: {model_name} → {status}")


# ── Scheduled Retraining Wrapper ──────────────────────────────────────────────

async def run_with_drift_check(
    db: AsyncSession,
    model_name: str,
    train_fn: Callable,
    reference_df: pd.DataFrame,
    current_df: pd.DataFrame,
    feature_cols: list[str],
    force_retrain: bool = False,
) -> dict:
    """
    Check for feature drift first. If drift detected (or force_retrain=True),
    retrain the model. Always logs the run.
    """
    drift = compute_feature_drift(reference_df, current_df, feature_cols)

    if drift["any_drift_detected"] or force_retrain:
        reason = "drift detected" if drift["any_drift_detected"] else "forced retrain"
        logger.info(f"Retraining {model_name} — {reason}")
        try:
            result = await train_fn(db)
            await log_model_run(
                db, model_name, "success",
                metrics=result.get("metrics"),
                drift_report=drift,
                rows_scored=result.get("files_scored", 0),
            )
            return {"retrained": True, "reason": reason, "drift": drift, "result": result}
        except Exception as e:
            await log_model_run(db, model_name, "failed", error_message=str(e))
            raise
    else:
        logger.info(f"No drift detected for {model_name} — skipping retrain")
        await log_model_run(db, model_name, "skipped_no_drift", drift_report=drift)
        return {"retrained": False, "reason": "no drift detected", "drift": drift}