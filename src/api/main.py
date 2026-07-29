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
    nextMatch   — no fixtures table exists yet. Kept as a placeholder using
                  the club's mapped home surface (real) but a generic
                  opponent/venue/date. Build a fixtures table + endpoint
                  later to make this real.
    distance    — no travel/geo data anywhere in the schema. Placeholder.
    subScores   — none of the models (v5 CatBoost, logistic regression)
                  predict per-injury-type risk; only one overall impact-
                  injury probability. This is a heuristic derived from
                  injury-history flags, NOT a model output. If per-injury-
                  type risk matters for the paper/product, that's a
                  separate modelling task (train 4 binary classifiers,
                  one per injury type) — not attempted here.
    minutesLast30 / gamesLast14 — no match-by-match date data available,
                  only season totals. Approximated from season averages.
────────────────────────────────────────────────────────────────────────────
"""

from typing import Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from src.db.queries import (
    get_all_clubs,
    get_squad,
    get_squad_injuries,
    get_player_by_id,
    get_player_injuries,
    get_stadium_surface,
)
from src.model.predictor import predict

app = FastAPI(title="PitchGuard API")

# Allow the Vite dev server to call this API. Adjust origins for production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

RISK_LOW_MAX = 40
RISK_MED_MAX = 70


# ── Feature extraction ──────────────────────────────────────────────────────
def _row_to_features(row: dict) -> dict:
    """Pull only the model's feature columns out of a raw players-table row.
    predict() itself also fills missing cols with 0, so this is a light
    pass-through — kept as a separate step in case DB column names ever
    diverge from the model's expected feature names."""
    return dict(row)


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
    ones they don't. Replace with real per-injury-type models if this needs
    to be a genuine prediction rather than a display heuristic.
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
    stadiums table); opponent/venue/date are not. See module docstring."""
    surface_type = get_stadium_surface(club_name)
    surface_label = (
        "Artificial Turf" if surface_type == "artificial" else "Natural Grass"
    )
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
        "age": row.get("age_at_season_start", 0),
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

    # Batch-fetch injuries once for the whole squad instead of N+1 queries
    squad_injuries = get_squad_injuries(club_name)
    injuries_lookup: dict = {}
    for inj in squad_injuries:
        injuries_lookup.setdefault(inj["tm_player_id"], []).append(inj)

    results = []
    for idx, row in enumerate(players, start=1):
        features = _row_to_features(row)
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

    features = _row_to_features(row)
    risk_result = predict(features)
    return _player_to_response(
        row, idx=0, risk_result=risk_result, injuries_lookup=None
    )
