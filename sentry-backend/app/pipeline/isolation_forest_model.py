import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sklearn.ensemble import IsolationForest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

CONTAMINATION = 0.015  # ~1.5%, within the 1-2% target range


async def fetch_access_events(db: AsyncSession) -> pd.DataFrame:
    """Fetch all access events for feature engineering."""
    result = await db.execute(text("""
        SELECT id, person_id, event_ts, direction, location
        FROM fact_access_event
        ORDER BY person_id, event_ts
    """))
    rows = result.fetchall()
    df = pd.DataFrame([dict(row._mapping) for row in rows])
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Build feature set for Isolation Forest:
    - hour_of_day
    - weekday
    - per-person swipe frequency
    - gap-since-last-event (seconds)
    - entry/exit balance (running)
    """
    if df.empty:
        return df

    df = df.copy()
    df["event_ts"] = pd.to_datetime(df["event_ts"])
    df = df.sort_values(["person_id", "event_ts"]).reset_index(drop=True)

    # Time-based features
    df["hour_of_day"] = df["event_ts"].dt.hour
    df["weekday"] = df["event_ts"].dt.weekday  # 0=Monday

    # Gap since last event per person (in seconds)
    df["gap_since_last_event"] = (
        df.groupby("person_id")["event_ts"].diff().dt.total_seconds()
    )
    df["gap_since_last_event"] = df["gap_since_last_event"].fillna(
        df["gap_since_last_event"].median() if not df["gap_since_last_event"].isna().all() else 0
    )

    # Per-person swipe frequency (total events per person)
    swipe_freq = df.groupby("person_id")["id"].count().rename("swipe_frequency")
    df = df.merge(swipe_freq, on="person_id", how="left")

    # Entry/exit balance — running cumulative balance per person
    df["direction_value"] = df["direction"].map({"IN": 1, "OUT": -1}).fillna(0)
    df["entry_exit_balance"] = df.groupby("person_id")["direction_value"].cumsum()

    return df


def run_isolation_forest(df: pd.DataFrame) -> pd.DataFrame:
    """Run Isolation Forest on engineered features."""
    if df.empty or len(df) < 10:
        logger.warning("Not enough data to run Isolation Forest (need >= 10 events)")
        df["anomaly_score"] = 0
        df["is_anomaly"] = False
        return df

    features = [
        "hour_of_day",
        "weekday",
        "swipe_frequency",
        "gap_since_last_event",
        "entry_exit_balance",
    ]

    X = df[features].fillna(0)

    model = IsolationForest(
        contamination=CONTAMINATION,
        random_state=42,
        n_estimators=200,
    )
    model.fit(X)

    # decision_function: lower score = more anomalous
    df["anomaly_score"] = model.decision_function(X)
    df["is_anomaly"] = model.predict(X) == -1  # -1 means anomaly

    logger.info(
        f"Isolation Forest scored {len(df)} events — "
        f"{df['is_anomaly'].sum()} flagged as anomalies ({CONTAMINATION*100:.1f}% contamination)"
    )
    return df


async def write_anomalies_to_queue(db: AsyncSession, df: pd.DataFrame):
    """
    Write lowest (most anomalous) scores to the review queue.
    NEVER auto-acts — only inserts as 'pending' for human review.
    """
    if df.empty:
        return 0

    anomalies = df[df["is_anomaly"]].copy()
    if anomalies.empty:
        logger.info("No anomalies detected — nothing written to queue")
        return 0

    # Normalize score to 0-1 range for consistency with existing queue (lower decision_function = more anomalous)
    min_score = df["anomaly_score"].min()
    max_score = df["anomaly_score"].max()
    score_range = max_score - min_score if max_score != min_score else 1

    written = 0
    for _, row in anomalies.iterrows():
        # Invert and normalize: most anomalous (lowest raw score) -> score close to 1.0
        normalized_score = 1 - ((row["anomaly_score"] - min_score) / score_range)

        await db.execute(text("""
            INSERT INTO anomaly_review_queue
                (id, event_ref, person_id, anomaly_type, score, status, created_at)
            VALUES
                (gen_random_uuid(), :event_ref, :person_id, :anomaly_type, :score, 'pending', NOW())
        """), {
            "event_ref": str(row["id"]),
            "person_id": row["person_id"],
            "anomaly_type": "isolation_forest",
            "score": round(float(normalized_score), 4),
        })
        written += 1

    await db.commit()
    logger.info(f"Wrote {written} isolation-forest anomalies to review queue")
    return written


async def run_anomaly_scoring_job(db: AsyncSession) -> dict:
    """
    Full scoring job:
    1. Fetch events
    2. Engineer features
    3. Run Isolation Forest
    4. Write lowest scores (most anomalous) to review queue
    Never auto-acts on access — only flags for human review.
    """
    logger.info("Starting Isolation Forest anomaly scoring job")

    df = await fetch_access_events(db)
    if df.empty:
        logger.warning("No access events found — skipping scoring")
        return {"total_events": 0, "anomalies_found": 0, "written_to_queue": 0}

    df = engineer_features(df)
    df = run_isolation_forest(df)
    written = await write_anomalies_to_queue(db, df)

    return {
        "total_events": len(df),
        "anomalies_found": int(df["is_anomaly"].sum()),
        "written_to_queue": written,
        "contamination_rate": CONTAMINATION,
    }