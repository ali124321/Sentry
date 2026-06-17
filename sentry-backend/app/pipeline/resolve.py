"""
SENTRY-14: Identity Resolution Service
Resolves badge codes, reconciles identities, stitches sessions,
and builds the email-based badge<->GitHub join key.
"""

import uuid
import logging
from datetime import timedelta
from typing import Optional
import pandas as pd

logger = logging.getLogger(__name__)

MAX_SESSION_GAP_HOURS = 16       # cap sessions longer than this
UNRESOLVED_THRESHOLD = 0.02      # <2% unresolved badge codes allowed
UNMATCHED_SESSION_THRESHOLD = 0.05  # <5% unmatched entry/exit allowed


# -------------------------------------------------------
# 1. Normalize badge codes
# -------------------------------------------------------
def normalize_badge_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Strip, uppercase, and standardize badge codes."""
    if "badge_code" not in df.columns:
        return df

    df["badge_code"] = df["badge_code"].apply(
        lambda x: str(x).strip().upper() if pd.notna(x) else None
    )

    total = len(df)
    unresolved = df["badge_code"].isna().sum()
    pct = unresolved / total if total > 0 else 0

    if pct > UNRESOLVED_THRESHOLD:
        logger.warning(
            f"Unresolved badge codes: {unresolved}/{total} ({pct:.1%}) — exceeds 2% threshold"
        )
    else:
        logger.info(f"Badge code normalization OK: {pct:.1%} unresolved")

    return df


# -------------------------------------------------------
# 2. Reconcile name/email/badge into one person_id
# -------------------------------------------------------
def reconcile_identities(
    df: pd.DataFrame,
    dim_person: pd.DataFrame,
) -> pd.DataFrame:
    """
    Match each row to a single person_id from dim_person.
    Match priority: email → badge_code → full_name
    1 employee = 1 person_id.
    """
    logger.info("Reconciling identities...")

    # Build lookup maps from dim_person
    email_map = dict(zip(dim_person["email"].str.lower(), dim_person["person_id"]))
    name_map = dict(zip(dim_person["full_name"].str.lower(), dim_person["person_id"]))

    def resolve(row):
        # Try email first
        if pd.notna(row.get("email")):
            pid = email_map.get(str(row["email"]).strip().lower())
            if pid:
                return pid

        # Try full_name
        if pd.notna(row.get("full_name")):
            pid = name_map.get(str(row["full_name"]).strip().lower())
            if pid:
                return pid

        # Assign new person_id for unknown persons
        logger.warning(f"Unresolved identity for row: {row.get('email') or row.get('full_name')}")
        return str(uuid.uuid4())

    df["person_id"] = df.apply(resolve, axis=1)

    total = len(df)
    resolved = df["person_id"].notna().sum()
    logger.info(f"Resolved {resolved}/{total} identities")

    return df


# -------------------------------------------------------
# 3. Exclude bots and shared accounts
# -------------------------------------------------------
def exclude_allowlist(
    df: pd.DataFrame,
    allowlist: pd.DataFrame,
) -> pd.DataFrame:
    """Remove rows where person is a bot or shared account."""
    if allowlist.empty:
        return df

    logger.info("Excluding bots and shared accounts...")
    blocked = set(allowlist["identifier"].str.lower())

    before = len(df)
    df = df[~df["email"].str.lower().isin(blocked)].reset_index(drop=True)
    logger.info(f"Excluded {before - len(df)} bot/shared account rows")

    return df


# -------------------------------------------------------
# 4. Stitch Entry->Exit sessions
# -------------------------------------------------------
def stitch_sessions(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pair each IN with the next OUT for the same person.
    Cap sessions longer than MAX_SESSION_GAP_HOURS.
    Warn if >5% of entries are unmatched.
    """
    logger.info("Stitching Entry->Exit sessions...")

    df = df.sort_values(["person_id", "event_ts"]).reset_index(drop=True)
    sessions = []
    unmatched = 0
    total_entries = 0

    for person_id, group in df.groupby("person_id"):
        group = group.reset_index(drop=True)
        i = 0
        while i < len(group):
            row = group.iloc[i]
            if row["direction"] == "IN":
                total_entries += 1
                # Look for matching OUT
                matched = False
                for j in range(i + 1, len(group)):
                    next_row = group.iloc[j]
                    if next_row["direction"] == "OUT":
                        gap = (next_row["event_ts"] - row["event_ts"]).total_seconds() / 3600
                        if gap > MAX_SESSION_GAP_HOURS:
                            logger.warning(
                                f"Session gap {gap:.1f}h for {person_id} — capped at {MAX_SESSION_GAP_HOURS}h"
                            )
                        sessions.append({
                            "person_id": person_id,
                            "entry_ts": row["event_ts"],
                            "exit_ts": next_row["event_ts"],
                            "location": row.get("location"),
                            "device_id": row.get("device_id"),
                            "duration_hours": min(gap, MAX_SESSION_GAP_HOURS),
                            "capped": gap > MAX_SESSION_GAP_HOURS,
                        })
                        matched = True
                        i = j + 1
                        break
                if not matched:
                    unmatched += 1
                    logger.warning(f"Unmatched IN for {person_id} at {row['event_ts']}")
                    i += 1
            else:
                i += 1

    unmatched_pct = unmatched / total_entries if total_entries > 0 else 0
    if unmatched_pct > UNMATCHED_SESSION_THRESHOLD:
        logger.warning(
            f"Unmatched sessions: {unmatched}/{total_entries} ({unmatched_pct:.1%}) — exceeds 5% threshold"
        )
    else:
        logger.info(f"Session stitching OK: {unmatched_pct:.1%} unmatched")

    return pd.DataFrame(sessions)


# -------------------------------------------------------
# 5. Build email-based badge<->GitHub join key
# -------------------------------------------------------
def build_join_key(
    df: pd.DataFrame,
    dim_person: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build a join key table: email -> badge_code + github_login.
    This is the master reference for downstream metrics.
    """
    logger.info("Building email-based badge<->GitHub join key...")

    join_key = dim_person[["person_id", "email", "github_login"]].copy()

    # Attach badge codes from access events
    badge_map = (
        df.dropna(subset=["badge_code"])
        .groupby("person_id")["badge_code"]
        .first()
        .reset_index()
    )

    join_key = join_key.merge(badge_map, on="person_id", how="left")
    join_key = join_key.rename(columns={"email": "email", "github_login": "github_login"})

    logger.info(f"Join key built with {len(join_key)} entries")
    return join_key


# -------------------------------------------------------
# Main resolver
# -------------------------------------------------------
def resolve(
    df: pd.DataFrame,
    dim_person: pd.DataFrame,
    allowlist: pd.DataFrame,
) -> dict:
    """
    Full identity resolution pipeline.
    Returns cleaned df, sessions df, and join key df.
    """
    logger.info("=== SENTRY-14: Identity Resolution Started ===")

    df = normalize_badge_codes(df)
    df = reconcile_identities(df, dim_person)
    df = exclude_allowlist(df, allowlist)
    sessions = stitch_sessions(df)
    join_key = build_join_key(df, dim_person)

    logger.info("=== Identity Resolution Complete ===")

    return {
        "resolved_df": df,
        "sessions": sessions,
        "join_key": join_key,
        "stats": {
            "total_rows": len(df),
            "total_sessions": len(sessions),
            "join_key_entries": len(join_key),
        }
    }
