"""
C5 — Behavioural Cohort Model
K-means clustering over arrival time and session length.
Cohorts emerge from data — descriptive only, never a ranking.
"""
import logging
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

COHORT_LABELS = {
    "early_long": "Early & Long",
    "late_short": "Late & Short",
    "hybrid": "Hybrid",
    "early_short": "Early & Short",
    "late_long": "Late & Long",
}


# ── Elbow + Silhouette to pick optimal k ─────────────────────────────────────

def pick_optimal_k(X_scaled: np.ndarray, k_min: int = 2, k_max: int = 6) -> dict:
    """
    Run K-means for k_min..k_max, compute inertia (elbow) and
    silhouette score. Return the k with the best silhouette.
    """
    results = []
    for k in range(k_min, k_max + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(X_scaled)
        inertia = km.inertia_
        sil = silhouette_score(X_scaled, labels) if len(set(labels)) > 1 else 0.0
        results.append({"k": k, "inertia": round(inertia, 4), "silhouette": round(sil, 4)})
        logger.info(f"k={k} inertia={inertia:.2f} silhouette={sil:.4f}")

    best = max(results, key=lambda x: x["silhouette"])
    logger.info(f"Optimal k={best['k']} (silhouette={best['silhouette']})")
    return {"optimal_k": best["k"], "scores": results}


# ── Descriptive label from cluster centroid ───────────────────────────────────

def label_cluster(avg_arrival_hour: float, avg_session_hours: float) -> str:
    """
    Assign a descriptive label based on centroid position.
    Early = arrival before 9am, Late = after 10am.
    Long = session > 7h, Short = session < 5h.
    Never implies performance or ranking.
    """
    early = avg_arrival_hour < 9.0
    long_session = avg_session_hours > 7.0

    if early and long_session:
        return "Early & Long"
    elif early and not long_session:
        return "Early & Short"
    elif not early and long_session:
        return "Late & Long"
    elif not early and not long_session:
        return "Late & Short"
    else:
        return "Hybrid"


# ── Main clustering pipeline ──────────────────────────────────────────────────

async def run_cohort_clustering(db: AsyncSession) -> dict:
    """
    C5: Fetch arrival time + session length per person,
    run K-means, persist cluster assignments to person_cohort table.
    """
    # Fetch features
    result = await db.execute(text("""
        SELECT
            f.person_id,
            AVG(EXTRACT(EPOCH FROM f.first_entry::time) / 3600.0) AS avg_arrival_hour,
            AVG(s.hours_spent) AS avg_session_hours,
            COUNT(DISTINCT f.day) AS days_present
        FROM mv_first_entry_per_day f
        JOIN mv_daily_sessions s
            ON f.person_id = s.person_id AND f.day = s.day
        WHERE s.hours_spent IS NOT NULL
        GROUP BY f.person_id
        HAVING COUNT(DISTINCT f.day) >= 5
    """))
    rows = result.fetchall()

    if len(rows) < 10:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 10 people with 5+ days of data. Found {len(rows)}.",
            "persons_found": len(rows),
        }

    df = pd.DataFrame([{
        "person_id": r.person_id,
        "avg_arrival_hour": float(r.avg_arrival_hour),
        "avg_session_hours": float(r.avg_session_hours),
        "days_present": int(r.days_present),
    } for r in rows])

    # Scale features
    scaler = StandardScaler()
    X = df[["avg_arrival_hour", "avg_session_hours"]].values
    X_scaled = scaler.fit_transform(X)

    # Pick optimal k
    k_analysis = pick_optimal_k(X_scaled)
    optimal_k = k_analysis["optimal_k"]

    # Final K-means with optimal k
    km = KMeans(n_clusters=optimal_k, random_state=42, n_init=10)
    df["cluster"] = km.fit_predict(X_scaled)

    # Label each cluster descriptively
    centroids = scaler.inverse_transform(km.cluster_centers_)
    cluster_labels = {}
    cluster_stats = []

    for i, centroid in enumerate(centroids):
        arrival, session = centroid[0], centroid[1]
        label = label_cluster(arrival, session)
        cluster_labels[i] = label
        members = df[df["cluster"] == i]
        cluster_stats.append({
            "cluster_id": i,
            "label": label,
            "size": len(members),
            "avg_arrival_hour": round(arrival, 2),
            "avg_arrival_time": f"{int(arrival):02d}:{int((arrival % 1) * 60):02d}",
            "avg_session_hours": round(session, 2),
            "note": "Descriptive pattern only — not a performance indicator",
        })

    df["cohort_label"] = df["cluster"].map(cluster_labels)

    # Persist to person_cohort table
    await db.execute(text("""
        CREATE TABLE IF NOT EXISTS person_cohort (
            person_id TEXT PRIMARY KEY,
            cluster_id INTEGER,
            cohort_label TEXT,
            avg_arrival_hour FLOAT,
            avg_session_hours FLOAT,
            days_present INTEGER,
            scored_at TIMESTAMPTZ DEFAULT NOW()
        )
    """))

    for _, row in df.iterrows():
        await db.execute(text("""
            INSERT INTO person_cohort
                (person_id, cluster_id, cohort_label, avg_arrival_hour, avg_session_hours, days_present, scored_at)
            VALUES
                (:person_id, :cluster_id, :cohort_label, :avg_arrival_hour, :avg_session_hours, :days_present, NOW())
            ON CONFLICT (person_id) DO UPDATE SET
                cluster_id = EXCLUDED.cluster_id,
                cohort_label = EXCLUDED.cohort_label,
                avg_arrival_hour = EXCLUDED.avg_arrival_hour,
                avg_session_hours = EXCLUDED.avg_session_hours,
                days_present = EXCLUDED.days_present,
                scored_at = NOW()
        """), {
            "person_id": str(row.person_id),
            "cluster_id": int(row.cluster),
            "cohort_label": row.cohort_label,
            "avg_arrival_hour": row.avg_arrival_hour,
            "avg_session_hours": row.avg_session_hours,
            "days_present": row.days_present,
        })

    await db.commit()

    return {
        "status": "success",
        "persons_clustered": len(df),
        "optimal_k": optimal_k,
        "k_analysis": k_analysis,
        "clusters": cluster_stats,
        "governance": "Cohorts are descriptive behavioural patterns only. They are not rankings or performance indicators.",
    }