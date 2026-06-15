"""
PitchGuard – FastAPI Backend
Endpoints: /api/risk, /api/squad, /api/status
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

from model import predict_risk, get_shap_explanation

app = FastAPI(
    title="PitchGuard API",
    description="Injury-risk prediction & squad analytics for football clubs",
    version="0.1.0",
)

# CORS – allow the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request / Response Schemas ────────────────────────────────────────
class RiskRequest(BaseModel):
    player_id: str
    match_load_minutes: Optional[float] = None
    training_intensity: Optional[float] = None


class RiskResponse(BaseModel):
    player_id: str
    risk_score: float
    risk_label: str  # "low" | "medium" | "high"
    shap_factors: dict


class SquadResponse(BaseModel):
    squad: list[dict]


class StatusResponse(BaseModel):
    status: str
    model_version: str


# ── Endpoints ─────────────────────────────────────────────────────────
@app.get("/api/status", response_model=StatusResponse)
async def status():
    """Health-check & model version."""
    return StatusResponse(status="ok", model_version="0.1.0")


@app.post("/api/risk", response_model=RiskResponse)
async def assess_risk(req: RiskRequest):
    """Return injury-risk score + SHAP explanation for a single player."""
    try:
        score, label = predict_risk(
            req.player_id,
            req.match_load_minutes,
            req.training_intensity,
        )
        factors = get_shap_explanation(req.player_id)
        return RiskResponse(
            player_id=req.player_id,
            risk_score=score,
            risk_label=label,
            shap_factors=factors,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/squad", response_model=SquadResponse)
async def squad_overview():
    """Return risk overview for every player in the current squad."""
    # TODO: iterate over known player IDs and return aggregated risk
    return SquadResponse(squad=[])


# ── Dev entry-point ───────────────────────────────────────────────────
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
