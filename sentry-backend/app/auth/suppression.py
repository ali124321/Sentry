"""
Shared suppression middleware.
Any aggregate cell representing fewer than MIN_GROUP_SIZE people
is suppressed (replaced with None) to protect individual privacy.
Reused by every KPI endpoint that returns per-cohort or per-group data.
"""

MIN_GROUP_SIZE = 5


def suppress_small_groups(
    rows: list[dict],
    count_field: str = "person_count",
    suppress_fields: list[str] = None,
) -> list[dict]:
    """
    Given a list of result dicts, suppress any row where count_field < MIN_GROUP_SIZE.
    Suppressed fields are replaced with None; the row is kept so the caller
    knows a group exists but its values are hidden.
    """
    result = []
    for row in rows:
        count = row.get(count_field, 0) or 0
        if count < MIN_GROUP_SIZE:
            suppressed = {k: v for k, v in row.items()}
            if suppress_fields:
                for f in suppress_fields:
                    suppressed[f] = None
            suppressed["suppressed"] = True
            suppressed["suppression_reason"] = f"Group size {count} < {MIN_GROUP_SIZE} (privacy threshold)"
            result.append(suppressed)
        else:
            row["suppressed"] = False
            result.append(row)
    return result


def suppress_value_if_small(value, count: int):
    """Suppress a single aggregate value if its group is too small."""
    if count is None or count < MIN_GROUP_SIZE:
        return None
    return value


def apply_suppression_to_dataframe(df, count_col: str, value_cols: list[str]):
    """
    Apply suppression to a pandas DataFrame in-place.
    Any row where count_col < MIN_GROUP_SIZE gets value_cols set to None.
    """
    mask = df[count_col] < MIN_GROUP_SIZE
    for col in value_cols:
        if col in df.columns:
            df.loc[mask, col] = None
    df["suppressed"] = mask
    return df