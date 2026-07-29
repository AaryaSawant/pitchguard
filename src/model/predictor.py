"""
PitchGuard — Predictor
File: src/model/predictor.py

Loads the v5 CatBoost model and exposes a single predict() function.

Usage:
    from src.model.predictor import predict
    result = predict({"age_at_season_start": 27, "home_surface_type": 1, ...})
"""

import json
import numpy as np
import pandas as pd
import shap
from catboost import CatBoostClassifier

MODEL_PATH = "data/models/catboost_model_v5.cbm"
FEATURES_PATH = "data/models/feature_columns_v5.json"

_model = None
_feature_cols = None
_explainer = None

FEATURE_LABELS = {
    "home_surface_type": "Surface Type",
    "turf_exposure": "Turf Exposure",
    "avg_injury_surface": "Surface Injury Pattern",
    "surface_consistency": "Surface Consistency",
    "pos_x_surface": "Position × Surface",
    "age_x_surface": "Age × Surface",
    "days_since_last_impact": "Recent Impact Injury",
    "days_since_last_injury": "Recency of Injury",
    "career_impact_rate": "Injury History",
    "injury_count_impact_prior": "Prior Impact Injuries",
    "injury_count_prior": "Prior Injuries",
    "injury_count_2yr": "Injuries (2yr)",
    "peak_overload": "Workload Overload",
    "workload_spike": "Workload Spike",
    "fatigue_index": "Fatigue Index",
    "age_at_season_start": "Age",
    "height_cm": "Height",
    "has_acl": "ACL History",
    "has_hamstring": "Hamstring History",
    "has_ankle": "Ankle History",
    "has_meniscus": "Meniscus History",
    "total_appearances": "Appearances",
    "avg_minutes_per_game": "Minutes per Game",
}


def _load():
    global _model, _feature_cols, _explainer
    if _model is None:
        _model = CatBoostClassifier()
        _model.load_model(MODEL_PATH)
        with open(FEATURES_PATH) as f:
            _feature_cols = json.load(f)
        _explainer = shap.TreeExplainer(_model)


def predict(player_features: dict) -> dict:
    """
    Takes a flat dict of player features and returns:
        {
            "risk_score": 73.4,
            "risk_tier": "High",
            "shap_top3": [
                {"feature": "turf_exposure", "label": "Turf Exposure", "shap_value": 0.31},
                ...
            ]
        }
    Risk tiers: Low < 40, Medium 40-69, High >= 70
    """
    _load()

    df = pd.DataFrame([player_features])
    for col in _feature_cols:
        if col not in df.columns:
            df[col] = 0
    df = df[_feature_cols].fillna(0)

    proba = _model.predict_proba(df)[0][1]
    risk = round(float(proba) * 100, 1)
    tier = "High" if risk >= 70 else "Medium" if risk >= 40 else "Low"

    shap_vals = _explainer.shap_values(df)[0]
    top3_idx = np.abs(shap_vals).argsort()[-3:][::-1]
    top3 = [
        {
            "feature": _feature_cols[i],
            "label": FEATURE_LABELS.get(_feature_cols[i], _feature_cols[i]),
            "shap_value": round(float(shap_vals[i]), 4),
        }
        for i in top3_idx
    ]

    return {"risk_score": risk, "risk_tier": tier, "shap_top3": top3}
