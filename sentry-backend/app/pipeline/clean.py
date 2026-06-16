import pandas as pd
import pytz
import re
import logging
from datetime import timedelta

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

SCAFFOLD_ROWS = 5
IST = pytz.timezone("Asia/Kolkata")
DOUBLE_TAP_SECONDS = 5
VALID_DIRECTIONS = {"IN", "OUT"}


def strip_scaffold_rows(df: pd.DataFrame) -> pd.DataFrame:
    """Skip the first 5 scaffold rows and reset header."""
    logger.info(f"Stripping {SCAFFOLD_ROWS} scaffold rows")
    return df.iloc[SCAFFOLD_ROWS:].reset_index(drop=True)


def set_header(df: pd.DataFrame) -> pd.DataFrame:
    """Use first row as header after stripping scaffold."""
    df.columns = df.iloc[0]
    df = df.iloc[1:].reset_index(drop=True)
    df.columns = [str(c).strip().lower() for c in df.columns]
    return df


def neutralize_formula_injection(df: pd.DataFrame) -> pd.DataFrame:
    """Remove formula injection attempts from string columns."""
    formula_pattern = re.compile(r'^[=+\-@]')

    def neutralize(val):
        if isinstance(val, str) and formula_pattern.match(val):
            logger.warning(f"Formula injection neutralized: {val}")
            return None
        return val

    for col in df.select_dtypes(include="str").columns:
        df[col] = df[col].apply(neutralize)

    return df


def map_sentinels_to_null(df: pd.DataFrame) -> pd.DataFrame:
    """Map '--' sentinel values to None/NULL."""
    logger.info("Mapping '--' sentinels to NULL")
    df = df.replace("--", None)
    return df


def normalize_badge_codes(df: pd.DataFrame) -> pd.DataFrame:
    """Strip whitespace and uppercase badge codes."""
    if "badge_code" in df.columns:
        logger.info("Normalizing badge codes")
        df["badge_code"] = df["badge_code"].apply(
            lambda x: str(x).strip().upper() if pd.notna(x) else None
        )
    return df


def coerce_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce event_ts to tz-aware timestamps in Asia/Kolkata."""
    if "event_ts" not in df.columns:
        return df

    logger.info("Coercing timestamps to Asia/Kolkata timezone")

    def parse_ts(val):
        if pd.isna(val) or val is None:
            return None
        try:
            ts = pd.to_datetime(val)
            if ts.tzinfo is None:
                ts = IST.localize(ts)
            else:
                ts = ts.astimezone(IST)
            return ts
        except Exception:
            logger.warning(f"Invalid timestamp skipped: {val}")
            return None

    df["event_ts"] = df["event_ts"].apply(parse_ts)
    return df


def validate_direction(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only rows with valid direction (IN/OUT)."""
    if "direction" not in df.columns:
        return df

    logger.info("Validating direction column")
    df["direction"] = df["direction"].apply(
        lambda x: str(x).strip().upper() if pd.notna(x) and x else None
    )
    before = len(df)
    df = df[df["direction"].isin(VALID_DIRECTIONS)].reset_index(drop=True)
    logger.info(f"Removed {before - len(df)} rows with invalid direction")
    return df


def drop_invalid_timestamps(df: pd.DataFrame) -> pd.DataFrame:
    """Drop rows where event_ts could not be parsed."""
    before = len(df)
    df = df[df["event_ts"].notna()].reset_index(drop=True)
    logger.info(f"Removed {before - len(df)} rows with invalid timestamps")
    return df


def dedupe_double_tap(df: pd.DataFrame) -> pd.DataFrame:
    """Remove double-tap swipes: same person, same direction within 5 seconds."""
    if "person_id" not in df.columns or "event_ts" not in df.columns:
        return df

    logger.info("Deduplicating double-tap swipes")
    df = df.sort_values(["person_id", "event_ts"]).reset_index(drop=True)

    keep = [True] * len(df)
    for i in range(1, len(df)):
        prev = df.iloc[i - 1]
        curr = df.iloc[i]
        if (
            prev["person_id"] == curr["person_id"]
            and prev["direction"] == curr["direction"]
            and pd.notna(prev["event_ts"])
            and pd.notna(curr["event_ts"])
            and (curr["event_ts"] - prev["event_ts"]) <= timedelta(seconds=DOUBLE_TAP_SECONDS)
        ):
            logger.warning(f"Double-tap removed: {curr['person_id']} at {curr['event_ts']}")
            keep[i] = False

    before = len(df)
    df = df[keep].reset_index(drop=True)
    logger.info(f"Removed {before - len(df)} double-tap duplicates")
    return df


def validate_range_balance(df: pd.DataFrame) -> pd.DataFrame:
    """Warn if IN/OUT counts are heavily imbalanced per person."""
    if "person_id" not in df.columns or "direction" not in df.columns:
        return df

    logger.info("Running range/balance validation")
    for person_id, group in df.groupby("person_id"):
        in_count = (group["direction"] == "IN").sum()
        out_count = (group["direction"] == "OUT").sum()
        diff = abs(in_count - out_count)
        if diff > 3:
            logger.warning(
                f"Balance issue for {person_id}: {in_count} IN, {out_count} OUT"
            )
    return df


def clean(input_path: str, output_path: str = None) -> pd.DataFrame:
    """Full cleaning pipeline."""
    logger.info(f"Loading xlsx: {input_path}")
    raw = pd.read_excel(input_path, header=None)

    df = strip_scaffold_rows(raw)
    df = set_header(df)
    df = neutralize_formula_injection(df)
    df = map_sentinels_to_null(df)
    df = normalize_badge_codes(df)
    df = coerce_timestamps(df)
    df = validate_direction(df)
    df = drop_invalid_timestamps(df)
    df = dedupe_double_tap(df)
    df = validate_range_balance(df)

    logger.info(f"Clean pipeline complete. {len(df)} rows ready for DB load.")

    if output_path:
        df.to_csv(output_path, index=False)
        logger.info(f"Output saved to {output_path}")

    return df


if __name__ == "__main__":
    from app.pipeline.generate_sample import generate_sample_xlsx
    generate_sample_xlsx()
    df = clean(
        input_path="app/pipeline/sample_access_log.xlsx",
        output_path="app/pipeline/clean_output.csv"
    )
    print("\n✅ Clean Data:")
    print(df.to_string())
