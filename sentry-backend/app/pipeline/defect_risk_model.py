import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import precision_score, recall_score, roc_auc_score
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

FEATURES = ["churn_30d", "churn_90d", "complexity_score", "distinct_authors_30d", "commit_count_90d"]


async def build_training_dataset(db: AsyncSession) -> pd.DataFrame:
    """
    Build a per-file dataset joining code_file_metric with bug history
    derived from szz_trace (a file is labeled buggy if it appears as the
    filename of a bug-introducing commit in szz_trace).
    """
    result = await db.execute(text("""
        SELECT
            cfm.id,
            cfm.repository_id,
            cfm.filename,
            cfm.commit_sha,
            cfm.churn_30d,
            cfm.churn_90d,
            cfm.complexity_score,
            cfm.distinct_authors_30d,
            cfm.commit_count_90d,
            cfm.snapshotted_at,
            EXISTS (
                SELECT 1 FROM szz_trace s
                WHERE s.filename = cfm.filename
            ) AS is_buggy
        FROM code_file_metric cfm
    """))
    rows = result.fetchall()
    df = pd.DataFrame([dict(row._mapping) for row in rows])
    return df


def chronological_split(df: pd.DataFrame, test_frac: float = 0.2):
    """
    Split data chronologically by snapshotted_at — train on older snapshots,
    test on the most recent ones, to avoid leaking future info into training.
    """
    df = df.sort_values("snapshotted_at").reset_index(drop=True)
    split_idx = int(len(df) * (1 - test_frac))
    return df.iloc[:split_idx], df.iloc[split_idx:]


def train_defect_model(df: pd.DataFrame):
    """Train a Gradient Boosting classifier on churn/complexity/author/bug-history features."""
    df = df.copy()
    for col in FEATURES:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["is_buggy"] = df["is_buggy"].astype(int)

    X = df[FEATURES]
    y = df["is_buggy"]

    if y.nunique() < 2:
        logger.warning("Only one class present in labels — cannot train a meaningful classifier yet")
        return None, None, None

    train_df, test_df = chronological_split(df)
    X_train, y_train = train_df[FEATURES], train_df["is_buggy"].astype(int)
    X_test, y_test = test_df[FEATURES], test_df["is_buggy"].astype(int)

    model = GradientBoostingClassifier(
        n_estimators=100,
        max_depth=3,
        learning_rate=0.1,
        random_state=42,
    )
    model.fit(X_train, y_train)

    metrics = {"precision": None, "recall": None, "roc_auc": None, "test_size": len(test_df)}
    if len(test_df) > 0 and y_test.nunique() > 1:
        y_pred = model.predict(X_test)
        y_proba = model.predict_proba(X_test)[:, 1]
        metrics["precision"] = round(precision_score(y_test, y_pred, zero_division=0), 4)
        metrics["recall"] = round(recall_score(y_test, y_pred, zero_division=0), 4)
        metrics["roc_auc"] = round(roc_auc_score(y_test, y_proba), 4)
    else:
        logger.warning("Test set too small or single-class — metrics unavailable for this run")

    return model, df, metrics


async def score_and_save(db: AsyncSession, model, df: pd.DataFrame) -> int:
    """Score every file with the trained model and write the 0-1 risk score back to code_file_metric."""
    X_all = df[FEATURES].copy()
    for col in FEATURES:
        X_all[col] = pd.to_numeric(X_all[col], errors="coerce").fillna(0)

    risk_scores = model.predict_proba(X_all)[:, 1]
    df["defect_risk_score"] = risk_scores

    updated = 0
    for _, row in df.iterrows():
        await db.execute(text("""
            UPDATE code_file_metric
            SET defect_risk_score = :score,
                defect_risk_label = :label,
                defect_risk_scored_at = NOW()
            WHERE id = :id
        """), {
            "score": round(float(row["defect_risk_score"]), 4),
            "label": bool(row["is_buggy"]),
            "id": int(row["id"]),
        })
        updated += 1

    await db.commit()
    logger.info(f"Updated defect risk scores for {updated} files")
    return updated


async def run_defect_prediction(db: AsyncSession) -> dict:
    """
    F-E6: Full defect-risk prediction pipeline.
    Trains a GradientBoostingClassifier on churn, complexity, distinct authors,
    commit frequency and SZZ-derived bug history, with a chronological train/test
    split, and writes a 0-1 risk score per file back to code_file_metric.
    """
    logger.info("Building defect-risk training dataset")
    df = await build_training_dataset(db)

    if df.empty:
        return {
            "status": "no_data",
            "message": "code_file_metric is empty — run code-quality scanners first",
            "files_scored": 0,
        }

    model, df_with_labels, metrics = train_defect_model(df)

    if model is None:
        return {
            "status": "insufficient_labels",
            "message": "Need at least one buggy and one non-buggy file to train. "
                       "Run SZZ tracing (F7) first to populate szz_trace.",
            "total_files": len(df),
            "buggy_files": int(df["is_buggy"].sum()),
        }

    updated = await score_and_save(db, model, df_with_labels)

    return {
        "status": "success",
        "total_files": len(df),
        "buggy_files": int(df_with_labels["is_buggy"].sum()),
        "files_scored": updated,
        "metrics": metrics,
        "features_used": FEATURES,
    }
