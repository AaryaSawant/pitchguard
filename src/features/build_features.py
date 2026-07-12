"""
PitchGuard — Feature Engineering Pipeline v6
=============================================
Fixed: DOB parsing, NaT handling, age computation.

Usage:
    python src/features/build_features.py
"""

import logging
import re
from pathlib import Path

import numpy as np
import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("feature_eng")

# ── Paths ─────────────────────────────────────────────────────────────────────
RAW = Path("src/scrapers/data/raw")
PROC = Path("src/scrapers/data/processed")
OUT = Path("data/processed")
OUT.mkdir(parents=True, exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
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
SEASON_ORDER = ["19/20", "20/21", "21/22", "22/23", "23/24", "24/25", "25/26"]

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

NO_PRIOR_INJURY_DAYS = 999


# ── Helpers ───────────────────────────────────────────────────────────────────
def parse_dob_series(series: pd.Series) -> pd.Series:
    """
    Parse a Series of DOB strings like '15/09/1995 (30)' into Timestamps.
    Strips the trailing age annotation first, then uses pd.to_datetime.
    """
    cleaned = (
        series.astype(str)
        .str.replace(r"\s*\(.*?\)", "", regex=True)
        .str.strip()
        .replace({"": pd.NaT, "nan": pd.NaT, "None": pd.NaT})
    )
    return pd.to_datetime(cleaned, dayfirst=True, errors="coerce")


def parse_date(val):
    """Parse a single date string — used for injury dates."""
    if pd.isna(val) or str(val).strip() == "":
        return pd.NaT
    val = re.sub(r"\s*\(.*?\)", "", str(val)).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%m/%d/%Y"):
        try:
            return pd.to_datetime(val, format=fmt)
        except Exception:
            continue
    try:
        return pd.to_datetime(val, dayfirst=True)
    except Exception:
        return pd.NaT


def is_impact(injury_type: str) -> bool:
    if not isinstance(injury_type, str):
        return False
    return any(kw in injury_type.lower() for kw in IMPACT_KW)


def position_flags(position: str) -> dict:
    pos = str(position).lower()
    return {
        "is_goalkeeper": int("goalkeeper" in pos or pos.strip() == "gk"),
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


def season_from_date(dt) -> str | None:
    if pd.isna(dt):
        return None
    start = dt.year if dt.month >= 8 else dt.year - 1
    label = f"{str(start)[-2:]}/{str(start + 1)[-2:]}"
    return label if label in TARGET_SEASONS else None


def calc_age(dob, reference_date) -> float:
    """Safe age calculation — returns np.nan if either value is NaT/None."""
    if pd.isna(dob) or pd.isna(reference_date):
        return np.nan
    try:
        return round(
            (pd.Timestamp(reference_date) - pd.Timestamp(dob)).days / 365.25, 1
        )
    except Exception:
        return np.nan


# ── Legacy helpers required by tests ─────────────────────────────────────────
def encode_injury_history(df: pd.DataFrame) -> dict:
    if df.empty:
        return {
            "injury_count_2y": 0,
            "has_acl": 0,
            "has_hamstring": 0,
            "has_ankle": 0,
            "has_meniscus": 0,
        }
    now = pd.Timestamp.now()
    two_yr_ago = now - pd.Timedelta(days=730)
    date_col = "from_date" if "from_date" in df.columns else "injury_date"
    df = df.copy()
    df["_date"] = pd.to_datetime(df[date_col], errors="coerce")
    recent = df[df["_date"] >= two_yr_ago]
    types = df["injury_type"].str.lower().str.cat(sep=" ") if len(df) > 0 else ""
    return {
        "injury_count_2y": len(recent),
        "has_acl": int("acl" in types or "cruciate" in types or "anterior" in types),
        "has_hamstring": int("hamstring" in types),
        "has_ankle": int("ankle" in types),
        "has_meniscus": int("meniscus" in types or "meniscal" in types),
    }


def compute_congestion(match_logs: pd.DataFrame, reference: pd.Timestamp) -> dict:
    if match_logs.empty:
        return {"games_last_14d": 0, "minutes_last_30d": 0}
    df = match_logs.copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    last_14 = df[df["date"] >= reference - pd.Timedelta(days=14)]
    last_30 = df[df["date"] >= reference - pd.Timedelta(days=30)]
    return {
        "games_last_14d": len(last_14),
        "minutes_last_30d": int(last_30["minutes_played"].sum()),
    }


# ── Load data ─────────────────────────────────────────────────────────────────
def load_data():
    log.info("Loading input files...")

    # Raw bios — has dob
    bios = pd.read_csv(RAW / "player_bios.csv", dtype=str).fillna("")
    bios.columns = [c.strip().lower().replace(" ", "_") for c in bios.columns]
    bios["player_tm_id"] = bios["player_tm_id"].astype(str).str.strip()
    log.info(f"  Bios:     {len(bios)} rows | cols: {list(bios.columns)}")

    # Players clean — height, position, foot
    players = pd.read_csv(PROC / "players_clean.csv", dtype=str).fillna("")
    players.columns = [c.strip().lower().replace(" ", "_") for c in players.columns]
    players["player_tm_id"] = players["player_tm_id"].astype(str).str.strip()
    log.info(f"  Players:  {len(players)} rows | cols: {list(players.columns)}")

    # Drop dob from players if it exists (avoid dob_x/dob_y collision)
    if "dob" in players.columns:
        players = players.drop(columns=["dob"])

    # Merge dob from bios
    players = players.merge(
        bios[["player_tm_id", "dob"]].drop_duplicates("player_tm_id"),
        on="player_tm_id",
        how="left",
    )
    log.info(
        f"  Merged:   {len(players)} rows with dob | dob coverage: {(players['dob'] != '').sum()}/{len(players)}"
    )

    # Injuries
    injuries = pd.read_csv(RAW / "injury_history.csv", dtype=str).fillna("")
    injuries.columns = [c.strip().lower().replace(" ", "_") for c in injuries.columns]
    injuries["player_tm_id"] = injuries["player_tm_id"].astype(str).str.strip()
    log.info(f"  Injuries: {len(injuries)} rows | cols: {list(injuries.columns)}")

    # Stats
    stats_path = RAW / "master_stats_final.csv"
    if stats_path.exists() and stats_path.stat().st_size > 100:
        stats = pd.read_csv(stats_path, dtype=str).fillna("")
        stats.columns = [c.strip().lower().replace(" ", "_") for c in stats.columns]
        if "tm_id" in stats.columns and "player_tm_id" not in stats.columns:
            stats = stats.rename(columns={"tm_id": "player_tm_id"})
        if "minutes" in stats.columns and "minutes_played" not in stats.columns:
            stats = stats.rename(columns={"minutes": "minutes_played"})
        stats["player_tm_id"] = stats["player_tm_id"].astype(str).str.strip()
        stats = stats[stats["season"].isin(TARGET_SEASONS)]
        log.info(
            f"  Stats:    {len(stats)} rows | {stats['player_tm_id'].nunique()} players"
        )
    else:
        log.warning("  master_stats_final.csv not found — skipping stats.")
        stats = pd.DataFrame()

    # Surfaces
    surfaces = pd.read_csv(RAW / "stadium_surfaces.csv", dtype=str).fillna("")
    surfaces.columns = [c.strip().lower().replace(" ", "_") for c in surfaces.columns]
    surfaces["surface_type"] = (
        pd.to_numeric(surfaces["surface_type"], errors="coerce").fillna(0).astype(int)
    )
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

    # Parse DOB using vectorised approach
    df["dob_parsed"] = parse_dob_series(df["dob"])
    log.info(f"  DOB parsed: {df['dob_parsed'].notna().sum()}/{len(df)}")

    df["height_cm"] = pd.to_numeric(
        df.get("height_cm", pd.Series(dtype=float)), errors="coerce"
    )
    df.loc[
        df["height_cm"].notna() & ((df["height_cm"] < 155) | (df["height_cm"] > 215)),
        "height_cm",
    ] = np.nan

    # Position flags
    pos_col = df.get("detailed_position", pd.Series("", index=df.index))
    pos_col = pos_col.where(
        pos_col != "", df.get("position", pd.Series("", index=df.index))
    )
    pos_df = pd.DataFrame(pos_col.apply(position_flags).tolist())
    df = pd.concat([df.reset_index(drop=True), pos_df.reset_index(drop=True)], axis=1)

    # Foot
    foot_col = df.get("strong_foot", pd.Series("", index=df.index))
    df["strong_foot_right"] = (foot_col.str.lower() == "right").astype(int)
    df["strong_foot_left"] = (foot_col.str.lower() == "left").astype(int)

    # Fill height by position
    for pos in ["is_goalkeeper", "is_defender", "is_midfielder", "is_forward"]:
        if pos in df.columns:
            mask = df[pos] == 1
            median = df.loc[mask, "height_cm"].median()
            df.loc[mask & df["height_cm"].isna(), "height_cm"] = median
    df["height_cm"] = df["height_cm"].fillna(df["height_cm"].median()).round(0)

    log.info(f"  Built bio features for {len(df)} players.")
    return df


# ── Build injury features ─────────────────────────────────────────────────────
def build_injury_features(
    injuries: pd.DataFrame, players_df: pd.DataFrame, surface_map: dict
) -> pd.DataFrame:
    log.info("Building injury-level features...")

    inj = injuries.copy()
    inj["player_tm_id"] = inj["player_tm_id"].astype(str).str.strip()
    inj["injury_date_dt"] = inj["injury_date"].apply(parse_date)
    inj["return_date_dt"] = (
        inj["return_date"].apply(parse_date) if "return_date" in inj.columns else pd.NaT
    )
    inj["is_impact"] = inj["injury_type"].apply(is_impact).astype(int)
    inj["season_mapped"] = inj["injury_date_dt"].apply(season_from_date)

    if "season" in inj.columns:
        inj["season_final"] = inj["season_mapped"].where(
            inj["season_mapped"].notna(), inj["season"]
        )
    else:
        inj["season_final"] = inj["season_mapped"]

    def get_surface(name):
        if not isinstance(name, str):
            return 0
        return surface_map.get(name.strip().lower(), 0)

    home_col = "current_club" if "current_club" in inj.columns else "club_name"
    inj["home_surface"] = (
        inj[home_col].apply(get_surface) if home_col in inj.columns else 0
    )
    opp_col = next(
        (
            c
            for c in ["opponent_mapped", "opponent_club", "opponent"]
            if c in inj.columns
        ),
        None,
    )
    inj["opponent_surface"] = (
        inj[opp_col].apply(get_surface) if opp_col else inj["home_surface"]
    )
    inj["injury_surface"] = inj.apply(
        lambda r: (
            r["opponent_surface"]
            if r["opponent_surface"] != r["home_surface"]
            else r["home_surface"]
        ),
        axis=1,
    )

    log.info("  Computing cumulative injury history per player...")
    inj_sorted = inj.sort_values(["player_tm_id", "injury_date_dt"])
    rows = []

    for tm_id, grp in inj_sorted.groupby("player_tm_id"):
        grp = grp.reset_index(drop=True)
        for idx, row in grp.iterrows():
            injury_dt = row["injury_date_dt"]
            prior = grp.iloc[:idx]
            count_career = idx
            count_impact = int(prior["is_impact"].sum()) if len(prior) > 0 else 0

            if pd.notna(injury_dt) and len(prior) > 0:
                count_2yr = len(
                    prior[prior["injury_date_dt"] >= injury_dt - pd.Timedelta(days=730)]
                )
            else:
                count_2yr = 0

            if len(prior) > 0 and prior["return_date_dt"].notna().any():
                last_return = prior["return_date_dt"].dropna().iloc[-1]
                days_since = (
                    max(0, (injury_dt - last_return).days)
                    if pd.notna(injury_dt)
                    else NO_PRIOR_INJURY_DAYS
                )
            else:
                days_since = NO_PRIOR_INJURY_DAYS

            prior_types = (
                prior["injury_type"].str.lower().str.cat(sep=" ")
                if len(prior) > 0
                else ""
            )

            rows.append(
                {
                    "player_tm_id": str(tm_id),
                    "player_name": row.get("player_name", ""),
                    "current_club": row.get(home_col, ""),
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
                    "has_acl": int("acl" in prior_types or "cruciate" in prior_types),
                    "has_hamstring": int("hamstring" in prior_types),
                    "has_ankle": int("ankle" in prior_types),
                    "has_meniscus": int(
                        "meniscus" in prior_types or "meniscal" in prior_types
                    ),
                }
            )

    result = pd.DataFrame(rows)
    log.info(f"  Built injury features for {len(result)} rows.")
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
    agg = agg.sort_values(["player_tm_id", "season"])
    agg["prev_appearances"] = agg.groupby("player_tm_id")["total_appearances"].shift(1)
    agg["workload_spike"] = (
        agg["total_appearances"] / agg["prev_appearances"].replace(0, np.nan)
    ).round(2)
    agg["workload_spike"] = agg["workload_spike"].fillna(1.0)

    log.info(f"  Built stats for {len(agg)} player-season rows.")
    return agg


# ── Build player-season master table ─────────────────────────────────────────
def build_player_season_features(players_df, injury_feats, stats_feats, surface_map):
    log.info("Building player-season master table...")

    if not injury_feats.empty:
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

    rows = []

    for _, player in players_df.iterrows():
        tm_id = str(player["player_tm_id"])
        club = str(player.get("club_name", ""))
        home_surface = surface_map.get(club.strip().lower(), 0)
        dob = player.get("dob_parsed")

        for season in SEASON_ORDER:
            start_year = SEASON_START_YEAR[season]
            season_start = pd.Timestamp(year=start_year, month=8, day=1)
            age_at_season = calc_age(dob, season_start)

            is_gk = int(player.get("is_goalkeeper", 0))
            is_def = int(player.get("is_defender", 0))
            is_mid = int(player.get("is_midfielder", 0))
            is_fwd = int(player.get("is_forward", 0))

            row = {
                "player_tm_id": tm_id,
                "player_name": player.get("player_name", ""),
                "club_name": club,
                "season": season,
                "age_at_season_start": age_at_season,
                "height_cm": player.get("height_cm"),
                "is_goalkeeper": is_gk,
                "is_defender": is_def,
                "is_midfielder": is_mid,
                "is_forward": is_fwd,
                "strong_foot_right": player.get("strong_foot_right", 0),
                "strong_foot_left": player.get("strong_foot_left", 0),
                "home_surface_type": home_surface,
            }

            inj_count_prior = 0
            if not inj_agg.empty:
                match = inj_agg[
                    (inj_agg["player_tm_id"] == tm_id) & (inj_agg["season"] == season)
                ]
                if not match.empty:
                    m = match.iloc[0]
                    inj_count_prior = int(m["injury_count_prior"])
                    row.update(
                        {
                            "injury_count_season": int(m["injury_count_season"]),
                            "impact_injuries_season": int(m["impact_injuries_season"]),
                            "injury_count_prior": inj_count_prior,
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
                            "days_since_last_injury": NO_PRIOR_INJURY_DAYS,
                            "has_acl": 0,
                            "has_hamstring": 0,
                            "has_ankle": 0,
                            "has_meniscus": 0,
                            "avg_injury_surface": float(home_surface),
                        }
                    )

            if not stats_feats.empty:
                sm = stats_feats[
                    (stats_feats["player_tm_id"] == tm_id)
                    & (stats_feats["season"] == season)
                ]
                if not sm.empty:
                    total_apps = int(sm.iloc[0]["total_appearances"])
                    row.update(
                        {
                            "total_appearances": total_apps,
                            "total_minutes": int(sm.iloc[0]["total_minutes"]),
                            "avg_minutes_per_game": float(
                                sm.iloc[0]["avg_minutes_per_game"]
                            ),
                            "workload_spike": float(sm.iloc[0]["workload_spike"]),
                            "turf_exposure": total_apps * home_surface,
                        }
                    )
                else:
                    row.update(
                        {
                            "total_appearances": np.nan,
                            "total_minutes": np.nan,
                            "avg_minutes_per_game": np.nan,
                            "workload_spike": 1.0,
                            "turf_exposure": 0,
                        }
                    )
            else:
                row.update(
                    {
                        "total_appearances": np.nan,
                        "total_minutes": np.nan,
                        "avg_minutes_per_game": np.nan,
                        "workload_spike": 1.0,
                        "turf_exposure": 0,
                    }
                )

            age_safe = age_at_season if pd.notna(age_at_season) else 0.0
            row["pos_x_surface"] = (is_fwd + is_def) * home_surface
            row["age_x_injury"] = age_safe * inj_count_prior
            row["age_x_acl"] = age_safe * int(row.get("has_acl", 0))

            rows.append(row)

    master = pd.DataFrame(rows)

    for col in ["total_appearances", "total_minutes", "avg_minutes_per_game"]:
        master[col] = master.groupby("player_tm_id")[col].transform(
            lambda x: x.fillna(x.mean())
        )
        master[col] = master.groupby("is_goalkeeper")[col].transform(
            lambda x: x.fillna(x.median())
        )
        master[col] = master[col].fillna(master[col].median())

    master["age_at_season_start"] = master.groupby("is_goalkeeper")[
        "age_at_season_start"
    ].transform(lambda x: x.fillna(x.median()))
    master["age_at_season_start"] = master["age_at_season_start"].fillna(
        master["age_at_season_start"].median()
    )
    master["age_x_injury"] = (
        master["age_at_season_start"] * master["injury_count_prior"]
    )
    master["age_x_acl"] = master["age_at_season_start"] * master["has_acl"]

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

    # Injury-level dataset
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

    # Age at injury date
    injury_feats_with_bio["age_at_season_start"] = injury_feats_with_bio.apply(
        lambda r: calc_age(r["dob_parsed"], parse_date(r.get("injury_date", ""))),
        axis=1,
    )
    injury_feats_with_bio["age_at_season_start"] = injury_feats_with_bio[
        "age_at_season_start"
    ].fillna(injury_feats_with_bio["age_at_season_start"].median())

    # Surface + stats features on injury dataset
    injury_feats_with_bio["home_surface_type"] = injury_feats_with_bio[
        "current_club"
    ].apply(lambda x: surface_map.get(str(x).strip().lower(), 0))
    injury_feats_with_bio["avg_injury_surface"] = injury_feats_with_bio[
        "injury_surface"
    ].astype(float)
    injury_feats_with_bio["turf_exposure"] = 0
    injury_feats_with_bio["workload_spike"] = 1.0
    injury_feats_with_bio["total_appearances"] = np.nan
    injury_feats_with_bio["total_minutes"] = np.nan
    injury_feats_with_bio["avg_minutes_per_game"] = np.nan
    injury_feats_with_bio["impact_injuries_season"] = injury_feats_with_bio[
        "is_impact_injury"
    ]

    if not stats_feats.empty:
        stats_merge = stats_feats[
            [
                "player_tm_id",
                "season",
                "total_appearances",
                "total_minutes",
                "avg_minutes_per_game",
                "workload_spike",
            ]
        ]
        injury_feats_with_bio = injury_feats_with_bio.merge(
            stats_merge,
            on=["player_tm_id", "season"],
            how="left",
            suffixes=("_drop", ""),
        )
        for col in [
            "total_appearances",
            "total_minutes",
            "avg_minutes_per_game",
            "workload_spike",
        ]:
            drop_col = f"{col}_drop"
            if drop_col in injury_feats_with_bio.columns:
                injury_feats_with_bio[col] = injury_feats_with_bio[col].fillna(
                    injury_feats_with_bio[drop_col]
                )
                injury_feats_with_bio.drop(columns=[drop_col], inplace=True)
        injury_feats_with_bio["turf_exposure"] = (
            injury_feats_with_bio["total_appearances"].fillna(0)
            * injury_feats_with_bio["home_surface_type"]
        )

    for col in ["total_appearances", "total_minutes", "avg_minutes_per_game"]:
        injury_feats_with_bio[col] = injury_feats_with_bio[col].fillna(
            injury_feats_with_bio[col].median()
        )

    injury_feats_with_bio["pos_x_surface"] = (
        injury_feats_with_bio["is_forward"] + injury_feats_with_bio["is_defender"]
    ) * injury_feats_with_bio["home_surface_type"]
    injury_feats_with_bio["age_x_injury"] = (
        injury_feats_with_bio["age_at_season_start"]
        * injury_feats_with_bio["injury_count_prior"]
    )
    injury_feats_with_bio["age_x_acl"] = (
        injury_feats_with_bio["age_at_season_start"] * injury_feats_with_bio["has_acl"]
    )

    injury_out = OUT / "model_dataset.csv"
    injury_feats_with_bio.to_csv(injury_out, index=False, encoding="utf-8-sig")
    log.info(f"\n✅ model_dataset.csv → {injury_out}")
    log.info(
        f"   Rows: {len(injury_feats_with_bio)} | Cols: {len(injury_feats_with_bio.columns)}"
    )

    season_out = OUT / "player_season_features.csv"
    master.to_csv(season_out, index=False, encoding="utf-8-sig")
    log.info(f"✅ player_season_features.csv → {season_out}")
    log.info(f"   Rows: {len(master)} | Players: {master['player_tm_id'].nunique()}")

    log.info("\n   Null counts (model_dataset):")
    nulls = injury_feats_with_bio.isnull().sum()
    for col, n in nulls[nulls > 0].items():
        log.info(f"     {col:<40} nulls={n}")


if __name__ == "__main__":
    run()
