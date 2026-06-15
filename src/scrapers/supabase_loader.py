"""
PitchGuard — Supabase Data Loader
===================================
Loads all cleaned CSVs into Supabase tables.

Tables loaded:
  1. stadiums      <- data/raw/stadium_surfaces.csv
  2. players       <- data/processed/players_clean.csv
  3. injuries      <- data/processed/injuries_clean.csv
  4. player_stats  <- data/raw/player_season_stats.csv

Usage:
    cd C:\\Users\\Aarya\\Downloads\\Pitchguard\\pitchguard
    python src/scrapers/supabase_loader.py
"""

import logging
import math
import os
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("supabase_loader")

# ── Config ────────────────────────────────────────────────────────────────────
load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY", "")

for suffix in ["/rest/v1", "/rest"]:
    if SUPABASE_URL.endswith(suffix):
        SUPABASE_URL = SUPABASE_URL[: -len(suffix)]

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRAPERS_DATA = Path("src/scrapers/data")
RAW = SCRAPERS_DATA / "raw"
PROC = SCRAPERS_DATA / "processed"

BATCH_SIZE = 500

# ── Exact column mapping: CSV columns → Supabase table columns ────────────────
PLAYERS_COLS = [
    "tm_player_id",
    "player_name",
    "player_name_normalised",
    "club_name",
    "club_tm_id",
    "position",
    "detailed_position",
    "nationality",
    "second_nationality",
    "dob",
    "age",
    "height_cm",
    "strong_foot",
    "market_value",
    "shirt_number",
    "current_club",
    "profile_url",
]

INJURIES_COLS = [
    "player_tm_id",
    "player_name",
    "current_club",
    "season",
    "injury_type",
    "injury_date",
    "return_date",
    "games_missed",
    "is_impact_injury",
]

STADIUMS_COLS = ["club_name", "stadium_name", "surface_type"]

PLAYER_STATS_COLS = [
    "player_tm_id",
    "player_name",
    "season",
    "competition",
    "club",
    "appearances",
    "minutes_played",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def get_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY not set in .env")
    log.info(f"  Connecting to: {SUPABASE_URL}")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def prepare_records(df: pd.DataFrame) -> list[dict]:
    """
    Bypasses Pandas float upcasting by cleaning the final Python dictionaries.
    Converts NaNs to None and floats like 1.0 back to strict integer 1.
    """
    records = df.to_dict(orient="records")
    clean = []
    for row in records:
        clean_row = {}
        for k, v in row.items():
            # Handle Pandas nulls and empty strings
            if pd.isna(v) or str(v).strip() == "":
                clean_row[k] = None
            # Convert floats that are whole numbers (e.g. 21.0 -> 21)
            elif isinstance(v, float) and v.is_integer():
                clean_row[k] = int(v)
            # Convert strings that are strictly formatted as ".0" floats
            elif (
                isinstance(v, str) and v.endswith(".0") and v[:-2].lstrip("-").isdigit()
            ):
                clean_row[k] = int(v[:-2])
            else:
                clean_row[k] = v
        clean.append(clean_row)
    return clean


def keep_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """Keep only columns that exist in both the df and the target list."""
    existing = [c for c in cols if c in df.columns]
    missing = [c for c in cols if c not in df.columns]
    if missing:
        log.warning(f"  Columns not found in CSV (will be skipped): {missing}")
    return df[existing].copy()


def load_csv(path: Path) -> pd.DataFrame | None:
    if not path.exists():
        log.warning(f"  File not found: {path} — skipping.")
        return None
    if path.stat().st_size == 0:
        log.warning(f"  File is empty: {path} — skipping.")
        return None
    df = pd.read_csv(path, dtype=str)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.fillna("")
    return df


def batch_upsert(
    sb: Client, table: str, records: list[dict], conflict_col: str
) -> None:
    total = len(records)
    batches = math.ceil(total / BATCH_SIZE)
    for i in range(batches):
        batch = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        sb.table(table).upsert(batch, on_conflict=conflict_col).execute()
        log.info(f"  Batch {i + 1}/{batches} — {len(batch)} rows → '{table}'")


def batch_insert(sb: Client, table: str, records: list[dict]) -> None:
    total = len(records)
    batches = math.ceil(total / BATCH_SIZE)
    for i in range(batches):
        batch = records[i * BATCH_SIZE : (i + 1) * BATCH_SIZE]
        sb.table(table).insert(batch).execute()
        log.info(f"  Batch {i + 1}/{batches} — {len(batch)} rows → '{table}'")


# ── Loaders ───────────────────────────────────────────────────────────────────
def load_stadiums(sb: Client) -> None:
    log.info("Loading stadiums...")
    df = load_csv(RAW / "stadium_surfaces.csv")
    if df is None:
        return
    df = keep_cols(df, STADIUMS_COLS)

    if "surface_type" in df.columns:
        df["surface_type"] = pd.to_numeric(df["surface_type"], errors="coerce")

    records = prepare_records(df)
    batch_upsert(sb, "stadiums", records, "club_name")
    log.info(f"  OK — {len(records)} stadiums loaded.")


def load_players(sb: Client) -> None:
    log.info("Loading players...")
    df = load_csv(PROC / "players_clean.csv")
    if df is None:
        return

    # Rename player_tm_id → tm_player_id to match Supabase schema
    if "player_tm_id" in df.columns:
        df = df.rename(columns={"player_tm_id": "tm_player_id"})

    df = keep_cols(df, PLAYERS_COLS)

    int_cols = [
        "tm_player_id",
        "club_tm_id",
        "age",
        "height_cm",
        "shirt_number",
        "market_value",
    ]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    records = prepare_records(df)
    batch_upsert(sb, "players", records, "tm_player_id")
    log.info(f"  OK — {len(records)} players loaded.")


def load_injuries(sb: Client) -> None:
    log.info("Loading injuries...")
    df = load_csv(PROC / "injuries_clean.csv")
    if df is None:
        return
    df = keep_cols(df, INJURIES_COLS)

    int_cols = ["player_tm_id", "games_missed", "is_impact_injury"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    log.info("  Clearing injuries table...")
    try:
        sb.table("injuries").delete().gte("id", 0).execute()
    except Exception as exc:
        log.warning(f"  Could not clear injuries: {exc}")

    records = prepare_records(df)
    batch_insert(sb, "injuries", records)
    log.info(f"  OK — {len(records)} injury records loaded.")


def load_player_stats(sb: Client) -> None:
    log.info("Loading player season stats...")
    df = load_csv(RAW / "player_season_stats.csv")
    if df is None:
        return
    df = keep_cols(df, PLAYER_STATS_COLS)

    int_cols = ["player_tm_id", "appearances", "minutes_played"]
    for col in int_cols:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    log.info("  Clearing player_stats table...")
    try:
        sb.table("player_stats").delete().gte("id", 0).execute()
    except Exception as exc:
        log.warning(f"  Could not clear player_stats: {exc}")

    records = prepare_records(df)
    batch_insert(sb, "player_stats", records)
    log.info(f"  OK — {len(records)} player stat rows loaded.")


# ── Main ──────────────────────────────────────────────────────────────────────
def run() -> None:
    log.info("Connecting to Supabase...")
    sb = get_client()
    log.info("Connected.")

    load_stadiums(sb)
    load_players(sb)
    load_injuries(sb)
    load_player_stats(sb)

    log.info("\nAll data loaded into Supabase successfully.")


if __name__ == "__main__":
    run()
