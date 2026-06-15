"""
PitchGuard — Feature Engineering Pipeline v2
=============================================
Takes cleaned data and builds the final ML-ready dataset.

Input files:
  src/scrapers/data/processed/players_clean.csv
  src/scrapers/data/processed/injuries_clean.csv
  src/scrapers/data/raw/player_season_stats.csv   (partial ok)
  src/scrapers/data/raw/stadium_surfaces.csv

Key design decision:
  We derive surface type directly from the injury CSV using:
    - current_club  → home stadium surface (player's club at time of injury)
    - opponent_mapped → away stadium surface (opponent's stadium)
  No fixture list needed.

Output:
  data/processed/model_dataset.csv
  One row per player-injury event with all features computed.
  Also outputs data/processed/player_season_features.csv
  One row per player-season (for players with no injuries too).

Usage:
    cd C:\\Users\\Aarya\\Downloads\\Pitchguard\\pitchguard
    python src/features/build_features.py
"""

import logging
from pathlib import Path
from datetime import datetime

import numpy as np
import pandas as pd

# ── Logging ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("feature_eng")

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRAPERS_DATA = Path("src/scrapers/data")
RAW = SCRAPERS_DATA / "raw"
PROC = SCRAPERS_DATA / "processed"
OUT_DIR = Path("data/processed")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Season label → start year ─────────────────────────────────────────────────
SEASON_START_YEAR = {
    "19/20": 2019,
    "20/21": 2020,
    "21/22": 2021,
    "22/23": 2022,
    "23/24": 2023,
    "24/25": 2024,
    "25/26": 2025,
}

TARGET_SEASONS = set(SEASON_START_YEAR.keys())

# ── Impact injury keywords ────────────────────────────────────────────────────
IMPACT_KW = [
    "acl",
    "anterior cruciate",
    "cruciate ligament",
    "hamstring",
    "ankle ligament",
    "ankle injury",
    "meniscus",
    "meniscal",
    "knee ligament",
    "muscle tear",
    "muscle rupture",
    "adductor",
    "calf",
    "thigh",
    "groin",
    "quadricep",
]


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_date(val) -> pd.Timestamp | None:
    if pd.isna(val) or str(val).strip() == "":
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return pd.to_datetime(val, format=fmt)
        except Exception:
            continue
    try:
        return pd.to_datetime(val, dayfirst=True)
    except Exception:
        return None


def is_impact(injury_type: str) -> bool:
    if not isinstance(injury_type, str):
        return False
    return any(kw in injury_type.lower() for kw in IMPACT_KW)


def position_flags(position: str) -> dict:
    pos = str(position).lower()
    return {
        "is_goalkeeper": int("goalkeeper" in pos or pos.strip() in ("gk",)),
        "is_defender": int(
            any(
                x in pos
                for x in [
                    "back",
                    "defender",
                    "centre-back",
                    "cb",
                    "lb",
                    "rb",
                    "wing-back",
                ]
            )
        ),
        "is_midfielder": int(
            any(
                x in pos
                for x in [
                    "mid",
                    "midfielder",
                    "winger",
                    "attacking mid",
                    "defensive mid",
                ]
            )
        ),
        "is_forward": int(
            any(
                x in pos
                for x in [
                    "forward",
                    "striker",
                    "attacker",
                    "centre-forward",
                    "st",
                    "cf",
                    "fw",
                    "second striker",
                ]
            )
        ),
    }


def season_from_date(dt: pd.Timestamp) -> str | None:
    """Map a date to a season label like '24/25'."""
    if dt is None:
        return None
    year = dt.year
    month = dt.month
    # Season runs Aug–Jul
    if month >= 8:
        start = year
    else:
        start = year - 1
    end_short = str(start + 1)[-2:]
    label = f"{str(start)[-2:]}/{end_short}"
    return label if label in TARGET_SEASONS else None


# ── Load data ─────────────────────────────────────────────────────────────────
def load_data():
    log.info("Loading input files...")

    players = pd.read_csv(PROC / "players_clean.csv", dtype=str).fillna("")
    players.columns = [c.strip().lower().replace(" ", "_") for c in players.columns]
    log.info(f"  Players:  {len(players)} rows")

    injuries = pd.read_csv(PROC / "injuries_clean.csv", dtype=str).fillna("")
    injuries.columns = [c.strip().lower().replace(" ", "_") for c in injuries.columns]
    log.info(f"  Injuries: {len(injuries)} rows")

    stats_path = RAW / "player_season_stats.csv"
    if stats_path.exists() and stats_path.stat().st_size > 100:
        stats = pd.read_csv(stats_path, dtype=str).fillna("")
        stats.columns = [c.strip().lower().replace(" ", "_") for c in stats.columns]
        log.info(f"  Stats:    {len(stats)} rows")
    else:
        log.warning(
            "  player_season_stats.csv not found or empty — stats features will be null."
        )
        stats = pd.DataFrame()

    surfaces = pd.read_csv(RAW / "stadium_surfaces.csv", dtype=str).fillna("")
    surfaces.columns = [c.strip().lower().replace(" ", "_") for c in surfaces.columns]
    surfaces["surface_type"] = (
        pd.to_numeric(surfaces["surface_type"], errors="coerce").fillna(0).astype(int)
    )
    # Build lookup: club_name (lowercase stripped) → surface_type
    surface_map = {
        row["club_name"].strip().lower(): int(row["surface_type"])
        for _, row in surfaces.iterrows()
    }
    log.info(f"  Surfaces: {len(surfaces)} clubs mapped")

    return players, injuries, stats, surface_map


# ── Build player bio features ─────────────────────────────────────────────────
def build_player_features(players: pd.DataFrame) -> pd.DataFrame:
    log.info("Building player bio features...")
    df = players.copy()
    df["player_tm_id"] = df["player_tm_id"].astype(str).str.strip()

    # DOB → datetime
    df["dob_parsed"] = df["dob"].apply(parse_date)

    # Height
    df["height_cm"] = pd.to_numeric(df["height_cm"], errors="coerce")
    df.loc[
        df["height_cm"].notna() & ((df["height_cm"] < 155) | (df["height_cm"] > 215)),
        "height_cm",
    ] = np.nan

    # Position flags
    pos_col = df["detailed_position"].where(
        df["detailed_position"] != "", df["position"]
    )
    pos_flags = pos_col.apply(position_flags)
    pos_df = pd.DataFrame(pos_flags.tolist())
    df = pd.concat([df.reset_index(drop=True), pos_df.reset_index(drop=True)], axis=1)

    # Foot
    df["strong_foot_right"] = (df["strong_foot"].str.lower() == "right").astype(int)
    df["strong_foot_left"] = (df["strong_foot"].str.lower() == "left").astype(int)

    # Impute height with positional median
    for pos in ["is_goalkeeper", "is_defender", "is_midfielder", "is_forward"]:
        mask = df[pos] == 1
        median = df.loc[mask, "height_cm"].median()
        df.loc[mask & df["height_cm"].isna(), "height_cm"] = median
    df["height_cm"] = (
        df["height_cm"].fillna(df["height_cm"].median()).round(0).astype("Int64")
    )

    log.info(f"  Built bio features for {len(df)} players.")
    return df


# ── Build injury features ─────────────────────────────────────────────────────
def build_injury_features(
    injuries: pd.DataFrame,
    players_df: pd.DataFrame,
    surface_map: dict,
) -> pd.DataFrame:
    log.info("Building injury-level features...")

    inj = injuries.copy()
    inj["player_tm_id"] = inj["player_tm_id"].astype(str).str.strip()
    inj["injury_date_dt"] = inj["injury_date"].apply(parse_date)
    inj["return_date_dt"] = inj["return_date"].apply(parse_date)
    inj["is_impact"] = inj["injury_type"].apply(is_impact).astype(int)

    # Map season from injury date
    inj["season_mapped"] = inj["injury_date_dt"].apply(season_from_date)

    # Use season column from CSV as fallback
    if "season" in inj.columns:
        inj["season_final"] = inj["season_mapped"].where(
            inj["season_mapped"].notna(), inj["season"]
        )
    else:
        inj["season_final"] = inj["season_mapped"]

    # ── Surface at time of injury ─────────────────────────────────────────────
    # Home surface = player's club at time of injury
    # Opponent surface = opponent's stadium surface
    # If no opponent info → use home surface as default

    def get_surface(club_name: str) -> int:
        if not isinstance(club_name, str):
            return 0
        return surface_map.get(club_name.strip().lower(), 0)

    # current_club = club player was at when injured
    if "current_club" in inj.columns:
        inj["home_surface"] = inj["current_club"].apply(get_surface)
    else:
        inj["home_surface"] = 0

    # opponent surface — use opponent_mapped if available, else opponent_club
    opp_col = None
    for col in ["opponent_mapped", "opponent_club", "opponent"]:
        if col in inj.columns:
            opp_col = col
            break

    if opp_col:
        inj["opponent_surface"] = inj[opp_col].apply(get_surface)
    else:
        inj["opponent_surface"] = inj["home_surface"]

    # injury_surface = surface where injury likely occurred
    # If opponent surface is known and different, use it (away match)
    # Otherwise use home surface
    inj["injury_surface"] = inj.apply(
        lambda r: (
            r["opponent_surface"]
            if r["opponent_surface"] != r["home_surface"]
            else r["home_surface"]
        ),
        axis=1,
    )

    # ── Per-player injury history features (cumulative at time of each injury) ──
    log.info("  Computing cumulative injury history per player...")
    inj_sorted = inj.sort_values(["player_tm_id", "injury_date_dt"])

    rows = []
    for tm_id, grp in inj_sorted.groupby("player_tm_id"):
        grp = grp.reset_index(drop=True)

        for idx, row in grp.iterrows():
            injury_dt = row["injury_date_dt"]

            # All prior injuries for this player
            prior = grp.iloc[:idx]

            # Injury counts
            count_career = idx  # number of prior injuries
            count_impact = prior["is_impact"].sum() if len(prior) > 0 else 0

            # 2-year window
            if injury_dt is not None and len(prior) > 0:
                two_yr_ago = injury_dt - pd.Timedelta(days=730)
                prior_2yr = prior[prior["injury_date_dt"] >= two_yr_ago]
                count_2yr = len(prior_2yr)
            else:
                count_2yr = 0

            # Days since last injury
            if len(prior) > 0 and prior["return_date_dt"].notna().any():
                last_return = prior["return_date_dt"].dropna().iloc[-1]
                days_since = (injury_dt - last_return).days if injury_dt else -1
                days_since = max(0, days_since)
            else:
                days_since = -1  # no prior injury

            # Type flags (ever had this type before)
            prior_types = (
                prior["injury_type"].str.lower().str.cat(sep=" ")
                if len(prior) > 0
                else ""
            )
            has_acl = int("acl" in prior_types or "cruciate" in prior_types)
            has_hamstring = int("hamstring" in prior_types)
            has_ankle = int("ankle" in prior_types)
            has_meniscus = int("meniscus" in prior_types or "meniscal" in prior_types)

            rows.append(
                {
                    "player_tm_id": str(tm_id),
                    "player_name": row.get("player_name", ""),
                    "current_club": row.get("current_club", ""),
                    "season": row.get("season_final", ""),
                    "injury_date": row.get("injury_date", ""),
                    "return_date": row.get("return_date", ""),
                    "injury_type": row.get("injury_type", ""),
                    "games_missed": pd.to_numeric(
                        row.get("games_missed", 0), errors="coerce"
                    ),
                    "is_impact_injury": int(row["is_impact"]),
                    "injury_surface": int(row["injury_surface"]),
                    "home_surface": int(row["home_surface"]),
                    "opponent_surface": int(row["opponent_surface"]),
                    "injury_count_prior": int(count_career),
                    "injury_count_impact_prior": int(count_impact),
                    "injury_count_2yr": int(count_2yr),
                    "days_since_last_injury": int(days_since),
                    "has_acl": has_acl,
                    "has_hamstring": has_hamstring,
                    "has_ankle": has_ankle,
                    "has_meniscus": has_meniscus,
                }
            )

    result = pd.DataFrame(rows)
    log.info(f"  Built injury features for {len(result)} injury events.")
    return result


# ── Build season stats features ───────────────────────────────────────────────
def build_stats_features(stats: pd.DataFrame) -> pd.DataFrame:
    if stats.empty:
        return pd.DataFrame()

    log.info("Building season stats features...")
    df = stats.copy()
    df["appearances"] = pd.to_numeric(df.get("appearances", 0), errors="coerce").fillna(
        0
    )
    df["minutes_played"] = pd.to_numeric(
        df.get("minutes_played", 0), errors="coerce"
    ).fillna(0)

    agg = (
        df.groupby(["player_tm_id", "season"])
        .agg(
            total_appearances=("appearances", "sum"),
            total_minutes=("minutes_played", "sum"),
        )
        .reset_index()
    )
    agg["avg_minutes_per_game"] = (
        agg["total_minutes"] / agg["total_appearances"].replace(0, np.nan)
    ).round(1)

    log.info(f"  Built stats for {len(agg)} player-season rows.")
    return agg


# ── Build player-season features (all players, all seasons) ──────────────────
def build_player_season_features(
    players_df: pd.DataFrame,
    injury_feats: pd.DataFrame,
    stats_feats: pd.DataFrame,
    surface_map: dict,
) -> pd.DataFrame:
    log.info("Building player-season master table...")

    # Aggregate injury features per player per season
    if not injury_feats.empty:
        # Per player-season: max cumulative counts (last injury of that season)
        inj_agg = (
            injury_feats.groupby(["player_tm_id", "season"])
            .agg(
                injury_count_season=("is_impact_injury", "count"),
                impact_injuries_season=("is_impact_injury", "sum"),
                injury_count_prior=("injury_count_prior", "max"),
                injury_count_2yr=("injury_count_2yr", "max"),
                days_since_last_injury=("days_since_last_injury", "min"),
                has_acl=("has_acl", "max"),
                has_hamstring=("has_hamstring", "max"),
                has_ankle=("has_ankle", "max"),
                has_meniscus=("has_meniscus", "max"),
                injury_surface=("injury_surface", "mean"),
            )
            .reset_index()
        )
    else:
        inj_agg = pd.DataFrame()

    seasons = list(SEASON_START_YEAR.keys())
    rows = []

    for _, player in players_df.iterrows():
        tm_id = str(player["player_tm_id"])
        club = str(player.get("club_name", ""))
        home_surface = surface_map.get(club.strip().lower(), 0)

        for season in seasons:
            start_year = SEASON_START_YEAR[season]

            # Age at season start
            dob = player.get("dob_parsed")
            if dob is not None and not (isinstance(dob, float) and np.isnan(dob)):
                try:
                    age_at_season = round(
                        (datetime(start_year, 8, 1) - dob.to_pydatetime()).days
                        / 365.25,
                        1,
                    )
                except Exception:
                    age_at_season = np.nan
            else:
                age_at_season = np.nan

            row = {
                "player_tm_id": tm_id,
                "player_name": player.get("player_name", ""),
                "club_name": club,
                "season": season,
                "age_at_season_start": age_at_season,
                "height_cm": player.get("height_cm"),
                "is_goalkeeper": player.get("is_goalkeeper", 0),
                "is_defender": player.get("is_defender", 0),
                "is_midfielder": player.get("is_midfielder", 0),
                "is_forward": player.get("is_forward", 0),
                "strong_foot_right": player.get("strong_foot_right", 0),
                "strong_foot_left": player.get("strong_foot_left", 0),
                "home_surface_type": home_surface,
            }

            # Merge injury agg for this player-season
            if not inj_agg.empty:
                match = inj_agg[
                    (inj_agg["player_tm_id"] == tm_id) & (inj_agg["season"] == season)
                ]
                if not match.empty:
                    m = match.iloc[0]
                    row.update(
                        {
                            "injury_count_season": int(m["injury_count_season"]),
                            "impact_injuries_season": int(m["impact_injuries_season"]),
                            "injury_count_prior": int(m["injury_count_prior"]),
                            "injury_count_2yr": int(m["injury_count_2yr"]),
                            "days_since_last_injury": int(m["days_since_last_injury"]),
                            "has_acl": int(m["has_acl"]),
                            "has_hamstring": int(m["has_hamstring"]),
                            "has_ankle": int(m["has_ankle"]),
                            "has_meniscus": int(m["has_meniscus"]),
                            "avg_injury_surface": round(float(m["injury_surface"]), 2),
                        }
                    )
                else:
                    row.update(
                        {
                            "injury_count_season": 0,
                            "impact_injuries_season": 0,
                            "injury_count_prior": 0,
                            "injury_count_2yr": 0,
                            "days_since_last_injury": -1,
                            "has_acl": 0,
                            "has_hamstring": 0,
                            "has_ankle": 0,
                            "has_meniscus": 0,
                            "avg_injury_surface": home_surface,
                        }
                    )

            # Merge stats for this player-season
            if not stats_feats.empty:
                sm = stats_feats[
                    (stats_feats["player_tm_id"] == tm_id)
                    & (stats_feats["season"] == season)
                ]
                if not sm.empty:
                    row["total_appearances"] = int(sm.iloc[0]["total_appearances"])
                    row["total_minutes"] = int(sm.iloc[0]["total_minutes"])
                    row["avg_minutes_per_game"] = float(
                        sm.iloc[0]["avg_minutes_per_game"]
                    )
                else:
                    row["total_appearances"] = np.nan
                    row["total_minutes"] = np.nan
                    row["avg_minutes_per_game"] = np.nan
            else:
                row["total_appearances"] = np.nan
                row["total_minutes"] = np.nan
                row["avg_minutes_per_game"] = np.nan

            rows.append(row)

    master = pd.DataFrame(rows)

    # Impute missing stats with player mean then positional median
    for col in ["total_appearances", "total_minutes", "avg_minutes_per_game"]:
        master[col] = master.groupby("player_tm_id")[col].transform(
            lambda x: x.fillna(x.mean())
        )
        master[col] = master.groupby("is_goalkeeper")[col].transform(
            lambda x: x.fillna(x.median())
        )
        master[col] = master[col].fillna(master[col].median())

    # Impute missing age with positional median
    master["age_at_season_start"] = master.groupby("is_goalkeeper")[
        "age_at_season_start"
    ].transform(lambda x: x.fillna(x.median()))
    master["age_at_season_start"] = master["age_at_season_start"].fillna(
        master["age_at_season_start"].median()
    )

    log.info(f"  Master table: {len(master)} rows.")
    return master


# ── Main ──────────────────────────────────────────────────────────────────────
def run() -> None:
    players, injuries, stats, surface_map = load_data()

    players_df = build_player_features(players)
    injury_feats = build_injury_features(injuries, players_df, surface_map)
    stats_feats = build_stats_features(stats)
    master = build_player_season_features(
        players_df, injury_feats, stats_feats, surface_map
    )

    # ── Save injury-level dataset (main model input) ──────────────────────────
    injury_out = OUT_DIR / "model_dataset.csv"
    injury_feats_with_bio = injury_feats.merge(
        players_df[
            [
                "player_tm_id",
                "club_name",
                "height_cm",
                "is_goalkeeper",
                "is_defender",
                "is_midfielder",
                "is_forward",
                "strong_foot_right",
                "strong_foot_left",
                "dob_parsed",
            ]
        ],
        on="player_tm_id",
        how="left",
    )
    injury_feats_with_bio.to_csv(injury_out, index=False, encoding="utf-8-sig")
    log.info(f"\n✅ Injury-level model dataset → {injury_out}")
    log.info(f"   Rows    : {len(injury_feats_with_bio)}")
    log.info(f"   Columns : {len(injury_feats_with_bio.columns)}")

    # ── Save player-season dataset ────────────────────────────────────────────
    season_out = OUT_DIR / "player_season_features.csv"
    master.to_csv(season_out, index=False, encoding="utf-8-sig")
    log.info(f"\n✅ Player-season features → {season_out}")
    log.info(f"   Rows    : {len(master)}")
    log.info(f"   Columns : {len(master.columns)}")
    log.info(f"   Players : {master['player_tm_id'].nunique()}")

    # ── Column null summary ───────────────────────────────────────────────────
    log.info("\n   Null counts per column (injury dataset):")
    for col in injury_feats_with_bio.columns:
        nulls = injury_feats_with_bio[col].isna().sum()
        log.info(f"     {col:<40} nulls={nulls}")


if __name__ == "__main__":
    run()
