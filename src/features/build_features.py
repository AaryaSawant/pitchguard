"""
Feature Engineering Pipeline
-----------------------------
Merges raw scraped data and computes the full ML feature set
as defined in PitchGuard PRD Section 5.

Usage:
    python src/features/build_features.py
"""

import logging

import pandas as pd
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

POSITION_MAP = {"GK": 0, "DEF": 1, "MID": 2, "FWD": 3}

IMPACT_INJURY_KEYWORDS = {
    "acl": ["acl", "anterior cruciate", "cruciate ligament"],
    "hamstring": ["hamstring"],
    "ankle": ["ankle", "ankle ligament"],
    "meniscus": ["meniscus", "meniscal"],
}

LEAGUES = ["pl", "la_liga", "bundesliga", "serie_a", "ligue_1", "super_lig"]


def load_surface_map(
    surface_file: str = "data/surface_mapping/stadium_surfaces.csv",
) -> dict:
    """
    Load the manual stadium surface lookup table.
    Returns dict: {club_name: surface_type}  where surface_type in {0, 1}
    (0 = natural grass, 1 = artificial turf)
    """
    df = pd.read_csv(surface_file)
    df["surface_type"] = pd.to_numeric(df["surface_type"], errors="coerce")
    return dict(zip(df["club_name"], df["surface_type"]))


def encode_injury_history(injury_df: pd.DataFrame) -> dict:
    """
    Given a player's injury history DataFrame, return binary flags
    for each impact injury type and count/recency features.
    """
    if injury_df.empty:
        return {
            "injury_count_2y": 0,
            "days_since_last_injury": None,
            "has_acl": 0,
            "has_hamstring": 0,
            "has_ankle": 0,
            "has_meniscus": 0,
        }

    injury_df = injury_df.copy()
    injury_df["from_date"] = pd.to_datetime(injury_df["from_date"], errors="coerce")
    cutoff = pd.Timestamp.now() - pd.DateOffset(years=2)
    recent = injury_df[injury_df["from_date"] >= cutoff]

    flags = {"acl": 0, "hamstring": 0, "ankle": 0, "meniscus": 0}
    for _, row in injury_df.iterrows():
        injury_lower = str(row.get("injury_type", "")).lower()
        for key, keywords in IMPACT_INJURY_KEYWORDS.items():
            if any(kw in injury_lower for kw in keywords):
                flags[key] = 1

    last_injury_date = injury_df["from_date"].dropna().max()
    days_since = (
        (pd.Timestamp.now() - last_injury_date).days
        if pd.notna(last_injury_date)
        else None
    )

    return {
        "injury_count_2y": len(recent),
        "days_since_last_injury": days_since,
        "has_acl": flags["acl"],
        "has_hamstring": flags["hamstring"],
        "has_ankle": flags["ankle"],
        "has_meniscus": flags["meniscus"],
    }


def compute_congestion(logs: pd.DataFrame, reference: pd.Timestamp) -> dict:
    """
    Compute recent match congestion features.
    """

    last_14d = logs[
        (logs["date"] >= reference - pd.Timedelta(days=14)) & (logs["date"] < reference)
    ]

    last_30d = logs[
        (logs["date"] >= reference - pd.Timedelta(days=30)) & (logs["date"] < reference)
    ]

    return {
        "games_last_14d": len(last_14d),
        "minutes_last_30d": int(last_30d["minutes_played"].sum()),
    }


def build_player_features(
    bio_df: pd.DataFrame,
    injury_df: pd.DataFrame,
    match_log_df: pd.DataFrame,
    surface_map: dict,
    reference_date: pd.Timestamp,
    upcoming_venue_club: str,
    is_home: bool,
    league: str,
) -> pd.DataFrame:
    """
    Build the full feature vector for each player in bio_df.
    Returns a DataFrame ready for model inference or training.
    """
    records = []

    for _, player in bio_df.iterrows():
        player_id = player.get("player_id")

        # ---- Player bio features ----
        position_raw = str(player.get("position", "")).upper()
        position_code = POSITION_MAP.get(position_raw, -1)

        try:
            age = int(str(player.get("age", "")).strip())
        except (ValueError, TypeError):
            age = np.nan

        try:
            height = float(
                str(player.get("height", "")).replace("m", "").replace(",", ".").strip()
            )
        except (ValueError, TypeError):
            height = np.nan

        try:
            weight = float(str(player.get("weight", "")).replace("kg", "").strip())
        except (ValueError, TypeError):
            weight = np.nan

        # ---- Injury history ----
        player_injuries = (
            injury_df[injury_df["player_id"] == player_id]
            if "player_id" in injury_df.columns
            else pd.DataFrame()
        )
        injury_feats = encode_injury_history(player_injuries)

        # ---- Workload / congestion ----
        player_logs = (
            match_log_df[match_log_df["player_id"] == player_id]
            if "player_id" in match_log_df.columns
            else pd.DataFrame()
        )
        if not player_logs.empty:
            past = player_logs[player_logs["date"] < reference_date].sort_values(
                "date", ascending=False
            )
            last_30d = past[past["date"] >= reference_date - pd.Timedelta(days=30)]
            last_14d = past[past["date"] >= reference_date - pd.Timedelta(days=14)]
            season_mins = past["minutes_played"].sum()
            avg_mins = past["minutes_played"].mean() if len(past) > 0 else 0
        else:
            last_30d = pd.DataFrame()
            last_14d = pd.DataFrame()
            season_mins = np.nan
            avg_mins = np.nan

        # ---- Surface features ----
        upcoming_surface = surface_map.get(upcoming_venue_club, np.nan)
        home_surface = surface_map.get(str(player.get("club", "")), np.nan)

        # ---- League one-hot ----
        league_ohe = {f"league_{lg}": int(league == lg) for lg in LEAGUES}

        record = {
            "player_id": player_id,
            "player_name": player.get("name"),
            "club": player.get("club"),
            "league": league,
            "reference_date": reference_date,
            # Bio
            "age": age,
            "height_cm": height,
            "weight_kg": weight,
            "position_code": position_code,
            # Injury history
            **injury_feats,
            # Workload
            "minutes_last_30d": (
                last_30d["minutes_played"].sum() if not last_30d.empty else np.nan
            ),
            "games_last_14d": len(last_14d),
            "season_minutes": season_mins,
            "avg_minutes_per_game": avg_mins,
            # Surface & context
            "upcoming_surface": upcoming_surface,
            "home_surface": home_surface,
            "is_home": int(is_home),
            **league_ohe,
        }
        records.append(record)

    return pd.DataFrame(records)


if __name__ == "__main__":
    logger.info("Feature engineering pipeline — run after scraping is complete.")
    logger.info("Call build_player_features() with your merged DataFrames.")
