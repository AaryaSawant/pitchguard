"""
PitchGuard – Model Layer
Load a trained XGBoost / LightGBM model and generate SHAP explanations.
"""

import os
import numpy as np

# ── Lazy-loaded globals ───────────────────────────────────────────────
_model = None
_explainer = None

MODEL_PATH = os.getenv("PITCHGUARD_MODEL_PATH", "artifacts/model.pkl")


def _load_model():
    """Load the serialised model + SHAP explainer once."""
    global _model, _explainer

    if _model is not None:
        return

    # TODO: replace with your actual model artefact
    # import joblib, shap
    # _model = joblib.load(MODEL_PATH)
    # _explainer = shap.TreeExplainer(_model)

    # Placeholder – returns random scores until the real model is plugged in
    _model = "placeholder"
    _explainer = "placeholder"
    print("[model] Loaded placeholder model – swap in your trained artefact.")


def predict_risk(
    player_id: str,
    match_load_minutes: float | None = None,
    training_intensity: float | None = None,
) -> tuple[float, str]:
    """
    Return (risk_score, risk_label) for a player.
    risk_label is one of: "low", "medium", "high".
    """
    _load_model()

    # TODO: build a proper feature vector from player_id + context
    score = float(np.random.default_rng().random())  # placeholder

    if score < 0.3:
        label = "low"
    elif score < 0.7:
        label = "medium"
    else:
        label = "high"

    return score, label


def get_shap_explanation(player_id: str) -> dict:
    """
    Return a dict of {feature_name: shap_value} for the most recent
    prediction so the front-end can render a waterfall / bar chart.
    """
    _load_model()

    # TODO: compute real SHAP values from _explainer
    return {
        "minutes_last_7d": round(np.random.uniform(-0.2, 0.3), 3),
        "sprint_distance_km": round(np.random.uniform(-0.1, 0.2), 3),
        "age": round(np.random.uniform(-0.05, 0.15), 3),
        "previous_injuries": round(np.random.uniform(0.0, 0.25), 3),
        "recovery_days": round(np.random.uniform(-0.15, 0.05), 3),
    }
