"""
PitchGuard — Predictor
File: src/model/predictor.py

Usage:
    from src.model.predictor import predict

    result = predict({
        "age_at_season_start": 27,
        "height_cm": 182,
        "is_goalkeeper": 0, "is_defender": 1, "is_midfielder": 0, "is_forward": 0,
        "strong_foot_right": 1, "strong_foot_left": 0,
        "home_surface_type": 1, "injury_surface": 1,
        "injury_count_prior": 3, "injury_count_2yr": 2, "injury_count_impact_prior": 1,
        "days_since_last_injury": 120,
        "has_acl": 0, "has_hamstring": 1, "has_ankle": 0, "has_meniscus": 0,
        "total_appearances": 28, "avg_minutes_per_game": 71.4,
    })
    print(result)
"""

import pickle
import json
import numpy as np
import pandas as pd
import shap

MODEL_PATH = "models/xgboost_model.pkl"
FEATURES_PATH = "models/feature_columns.json"

# Cache model in memory after first load so the dashboard doesn't reload it per request
_model = None
_feature_cols = None
_explainer = None


def _load():
    global _model, _feature_cols, _explainer
    if _model is None:
        with open(MODEL_PATH, "rb") as f:
            _model = pickle.load(f)
        with open(FEATURES_PATH) as f:
            _feature_cols = json.load(f)
        _explainer = shap.TreeExplainer(_model)


def predict(player_features: dict) -> dict:
    """
    Takes a flat dict of player features and returns:
        {
            "risk_score": 73.4,          # 0–100 float
            "risk_tier": "High",         # Low / Medium / High
            "shap_top3": [
                {"feature": "injury_surface",         "shap_value": 0.31},
                {"feature": "injury_count_impact_prior", "shap_value": 0.18},
                {"feature": "days_since_last_injury", "shap_value": -0.12},
            ]
        }
    """
    _load()

    df = pd.DataFrame([player_features])

    # Fill any missing features with 0 (handles partial data during dev)
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
        {"feature": _feature_cols[i], "shap_value": round(float(shap_vals[i]), 4)}
        for i in top3_idx
    ]

    return {
        "risk_score": risk,
        "risk_tier": tier,
        "shap_top3": top3,
    }
