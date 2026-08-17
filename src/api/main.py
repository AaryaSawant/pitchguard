"""
PitchGuard — FastAPI Backend
File: src/api/main.py

Wires src/db/queries.py (Supabase) + src/model/predictor.py (CatBoost v5)
into the endpoints the frontend needs, shaped to match PitchGuard.tsx's
Player interface as closely as real data allows.

Run:
    uvicorn src.api.main:app --reload --port 8000

Endpoints:
    GET /clubs
    GET /squad/{club_name}
    GET /player/{tm_player_id}

────────────────────────────────────────────────────────────────────────────
WHAT'S REAL vs APPROXIMATED (read before wiring the frontend)
────────────────────────────────────────────────────────────────────────────
REAL (from DB + v5 model):
    id, name, position, age, daysSinceInjury, injuryCount2yr, riskScore,
    tier, shapFactors, injuryHistory

APPROXIMATED (no fixtures/travel data exists in the Supabase schema —
flagged clearly rather than silently faked):
    nextMatch   — no fixtures table exists yet. Surface is real (pulled
                  from stadiums table); opponent/venue/date are not.
    distance    — no travel/geo data anywhere in the schema. Placeholder.
    subScores   — none of the models (v5 CatBoost, logistic regression)
                  predict per-injury-type risk; only one overall impact-
                  injury probability. Heuristic derived from injury-
                  history flags, NOT a model output.
    minutesLast30 / gamesLast14 — no match-by-match date data available,
                  only season totals. Approximated from season averages.

────────────────────────────────────────────────────────────────────────────
COLUMN NAME REFERENCE — verified against real Postgres errors, not guessed:
    players          -> tm_player_id
    injuries         -> player_tm_id
    player_stats     -> player_tm_id
    player_features  -> tm_player_id  (matches players, NOT injuries/stats)
This file uses `tm_player_id` as its own internal variable name everywhere
(row["tm_player_id"], features_lookup keys, response field) since that's
what the `players` table — the row this code is built around — actually
uses. The injuries lookup below is the ONE place that has to translate to
the different column name (`player_tm_id`) that the injuries table uses.
────────────────────────────────────────────────────────────────────────────
"""

from typing import Optional
from datetime import datetime, date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.db.queries import (
    get_all_clubs,
    get_squad,
    get_squad_injuries,
    get_player_by_id,
    get_player_injuries,
    get_stadium_surface,
    get_player_features,
    get_squad_features,
)
from src.model.predictor import predict

app = FastAPI(title="PitchGuard API")

# Allow the Vite dev server (local) and the deployed Vercel frontend
# (production) to call this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "https://pitchguard-one.vercel.app",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

RISK_LOW_MAX = 40
RISK_MED_MAX = 70


# ── Feature extraction ──────────────────────────────────────────────────────
def _row_to_features(
    row: dict,
    features_row: Optional[dict] = None,
    player_injuries: Optional[list] = None,
) -> dict:
    """
    Merges a players-table bio row with its matching player_features row
    (the real engineered model inputs) before handing off to predict().

    Three features aren't in player_season_features.csv and never made it
    into the player_features table: injury_rate, injury_burden, and
    injury_count_impact_prior. Computed live here the same way train.py's
    engineer_features() does, instead of silently falling back to 0.

    player_injuries: this player's injury rows, if already fetched by the
    caller (e.g. squad()'s batched injuries_lookup) — avoids an extra query
    per player. If None, fetches directly (used by the single-player
    /player endpoint, where there's no batch to reuse).
    """
    merged = dict(row)
    if features_row:
        merged.update(
            {
                k: v
                for k, v in features_row.items()
                if k not in ("tm_player_id", "season")
            }
        )

    # injury_rate = injury_count_prior / total_appearances (matches train.py)
    injury_count_prior = merged.get("injury_count_prior") or 0
    total_appearances = merged.get("total_appearances") or 0
    merged["injury_rate"] = (
        round(injury_count_prior / total_appearances, 4) if total_appearances else 0
    )

    # injury_burden = prior_games_missed / total_appearances (matches train.py / build_features.py v9)
    prior_games_missed = merged.get("prior_games_missed") or 0
    merged["injury_burden"] = (
        round(prior_games_missed / total_appearances, 4) if total_appearances else 0
    )

    # injury_count_impact_prior: count of this player's prior injuries
    # flagged as impact injuries. Not in player_features — computed from
    # the injuries table (or reused if the caller already fetched it).
    if player_injuries is None:
        tm_id = row.get("tm_player_id")
        player_injuries = get_player_injuries(tm_id) if tm_id else []
    merged["injury_count_impact_prior"] = sum(
        1 for inj in player_injuries if inj.get("is_impact_injury")
    )

    return merged


def _calc_age(dob_str: Optional[str]) -> int:
    """Calculate current age from a DOB string (e.g. '1995-09-15'). The
    players table's own `age` column is a stale scraped value that doesn't
    update — this computes it live instead."""
    if not dob_str:
        return 0
    try:
        dob = date.fromisoformat(str(dob_str)[:10])
        today = date.today()
        return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    except (ValueError, TypeError):
        return 0


def _position_from_flags(row: dict) -> str:
    pos = str(row.get("detailed_position") or row.get("position", "")).lower()
    if "goalkeeper" in pos or pos == "gk":
        return "GK"
    if any(x in pos for x in ["back", "defender", "centre-back", "wing-back"]):
        return "DEF"
    if any(x in pos for x in ["mid", "midfielder", "winger"]):
        return "MID"
    if any(x in pos for x in ["forward", "striker", "attacker", "centre-forward"]):
        return "FWD"
    return "N/A"


def _injury_year(injury_date: Optional[str]) -> int:
    if not injury_date:
        return datetime.now().year
    try:
        return datetime.fromisoformat(injury_date.replace("Z", "")).year
    except (ValueError, AttributeError):
        return datetime.now().year


def _build_injury_history(
    tm_player_id: str, injuries_lookup: Optional[dict] = None
) -> list[dict]:
    """injuries_lookup lets /squad pass in a pre-fetched batch (avoids N+1
    queries); /player fetches directly for a single player."""
    if injuries_lookup is not None:
        rows = injuries_lookup.get(tm_player_id, [])
    else:
        rows = get_player_injuries(tm_player_id)
    return [
        {
            "year": _injury_year(r.get("injury_date")),
            "type": r.get("injury_type", "Unknown"),
            "gamesMissed": r.get("games_missed", 0) or 0,
        }
        for r in rows
    ]


def _build_sub_scores(row: dict, risk_score: float) -> dict:
    """
    HEURISTIC, not a model output — see module docstring. Scales the overall
    risk score up for injury types the player has a history of, down for
    ones they don't.
    """

    def scaled(flag_key: str) -> int:
        has_history = bool(row.get(flag_key))
        base = risk_score * (1.3 if has_history else 0.5)
        return int(max(0, min(100, round(base))))

    return {
        "acl": scaled("has_acl"),
        "hamstring": scaled("has_hamstring"),
        "ankle": scaled("has_ankle"),
        "meniscus": scaled("has_meniscus"),
    }


def _build_next_match_placeholder(club_name: str) -> dict:
    """PLACEHOLDER — no fixtures table exists. Surface is real (pulled from
    stadiums table); opponent/venue/date are not."""
    surface_type = get_stadium_surface(club_name)
    surface_label = "Artificial Turf" if surface_type == 1 else "Natural Grass"
    return {
        "opponent": "TBD — fixtures not yet integrated",
        "venue": "TBD",
        "surface": surface_label,
        "homeAway": "Home",
        "date": "TBD",
    }


def _player_to_response(
    row: dict, idx: int, risk_result: dict, injuries_lookup: Optional[dict] = None
) -> dict:
    tm_id = row["tm_player_id"]
    risk_score = risk_result["risk_score"]
    tier = risk_result["risk_tier"]

    # Approximated from season totals — no match-by-match dates in schema.
    avg_minutes = row.get("avg_minutes_per_game", 0) or 0
    games_per_week = row.get("games_per_week", 0) or 0
    minutes_last_30 = round(avg_minutes * games_per_week * 4.3)
    games_last_14 = round(games_per_week * 2)

    return {
        "id": idx,
        "tm_player_id": tm_id,  # keep the real ID around for detail lookups
        "name": row.get("player_name", "Unknown"),
        "position": _position_from_flags(row),
        "age": _calc_age(row.get("dob")),
        "minutesLast30": minutes_last_30,
        "gamesLast14": games_last_14,
        "daysSinceInjury": row.get("days_since_last_injury", 999),
        "injuryCount2yr": row.get("injury_count_2yr", 0),
        "riskScore": risk_score,
        "tier": tier,
        "subScores": _build_sub_scores(row, risk_score),
        "shapFactors": [
            {"label": f["label"], "value": round(abs(f["shap_value"]), 3)}
            for f in risk_result["shap_top3"]
        ],
        "nextMatch": _build_next_match_placeholder(row.get("club_name", "")),
        "injuryHistory": _build_injury_history(tm_id, injuries_lookup),
        "distance": None,  # PLACEHOLDER — no travel/geo data in schema
    }


def log_missing_features(
    tm_player_id: Optional[str], player_name: Optional[str]
) -> None:
    """Loud warning when a player has no row in player_features — their
    risk score will be computed on defaults, not real data."""
    print(
        f"⚠️  No engineered features found for {player_name} ({tm_player_id}) — "
        f"risk score will be inaccurate."
    )


# ── Endpoints ────────────────────────────────────────────────────────────────
@app.get("/clubs")
def list_clubs():
    return {"clubs": get_all_clubs()}


@app.get("/squad/{club_name}")
def squad(club_name: str):
    players = get_squad(club_name)
    if not players:
        raise HTTPException(
            status_code=404, detail=f"No players found for club '{club_name}'"
        )

    # Batch-fetch injuries once for the whole squad instead of N+1 queries.
    # injuries table uses player_tm_id (different from players table's
    # tm_player_id) — that's the real column name, not a typo.
    squad_injuries = get_squad_injuries(club_name)
    injuries_lookup: dict = {}
    for inj in squad_injuries:
        key = inj.get("player_tm_id")
        if key:
            injuries_lookup.setdefault(key, []).append(inj)

    # Batch-fetch real engineered features for the whole squad (CRITICAL —
    # without this every prediction runs on an almost-empty feature vector)
    player_ids = [p["tm_player_id"] for p in players if p.get("tm_player_id")]
    features_lookup = get_squad_features(player_ids)

    results = []
    for idx, row in enumerate(players, start=1):
        tm_id = row.get("tm_player_id")
        features_row = features_lookup.get(tm_id)
        if features_row is None:
            log_missing_features(tm_id, row.get("player_name"))
        player_injuries = injuries_lookup.get(tm_id, [])
        features = _row_to_features(row, features_row, player_injuries)
        risk_result = predict(features)
        results.append(_player_to_response(row, idx, risk_result, injuries_lookup))

    return {"club": club_name, "players": results}


@app.get("/player/{tm_player_id}")
def player_detail(tm_player_id: str):
    row = get_player_by_id(tm_player_id)
    if not row:
        raise HTTPException(
            status_code=404, detail=f"No player found with id '{tm_player_id}'"
        )

    features_row = get_player_features(tm_player_id)
    if features_row is None:
        log_missing_features(tm_player_id, row.get("player_name"))
    features = _row_to_features(row, features_row)
    risk_result = predict(features)
    return _player_to_response(
        row, idx=0, risk_result=risk_result, injuries_lookup=None
    )
