"""
PitchGuard — Model Training v2
File: src/model/train.py

Run:
    python src/model/train.py

Outputs:
    data/models/xgboost_model.pkl
    data/models/feature_columns.json
    data/models/shap_summary.png
    data/models/model_meta.json
"""

import json
import os
import pickle
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import xgboost as xgb
import lightgbm as lgb
import optuna
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    classification_report,
)

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ── Paths ─────────────────────────────────────────────────────────────────────
DATA_PATH = "data/processed/model_dataset.csv"
MODELS_DIR = "data/models"
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Feature columns ───────────────────────────────────────────────────────────
# Position flags removed — pos_x_surface carries the interaction
# New features from build_features v9: congestion proxy + new injury features
FEATURE_COLS = [
    "age_at_season_start",
    "height_cm",
    "strong_foot_right",
    "strong_foot_left",
    "home_surface_type",
    "avg_injury_surface",
    "turf_exposure",
    "injury_count_prior",
    "injury_count_2yr",
    "injury_count_impact_prior",
    "days_since_last_injury",
    "days_since_last_impact",
    "career_impact_rate",
    "surface_consistency",
    "prior_games_missed",
    "has_acl",
    "has_hamstring",
    "has_ankle",
    "has_meniscus",
    "total_appearances",
    "total_minutes",
    "avg_minutes_per_game",
    "workload_spike",
    "games_per_week",
    "minutes_per_week",
    "season_minutes_spike",
    "peak_overload",
    "fatigue_index",
    "pos_x_surface",
    "age_x_injury",
    "age_x_acl",
    "age_x_surface",
    "injury_rate",
    "injury_burden",
]

TARGET_COL = "is_impact_injury"
TRAIN_SEASONS = ["19/20", "20/21", "21/22", "22/23"]
VAL_SEASONS = ["23/24"]
TEST_SEASONS = ["24/25", "25/26"]
DAYS_CAP = 730


# ── Feature engineering ───────────────────────────────────────────────────────
def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["days_since_last_injury"] = df["days_since_last_injury"].clip(upper=DAYS_CAP)
    df["days_since_last_impact"] = (
        df["days_since_last_impact"].clip(upper=DAYS_CAP)
        if "days_since_last_impact" in df.columns
        else DAYS_CAP
    )
    df["injury_rate"] = (
        (df["injury_count_prior"] / df["total_appearances"].replace(0, np.nan))
        .fillna(0)
        .round(4)
    )
    # injury_burden already in dataset from build_features v9
    if "injury_burden" not in df.columns:
        df["injury_burden"] = 0.0
    return df


# ── Load + split ──────────────────────────────────────────────────────────────
def load_and_split():
    print(f"[1/7] Loading {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)
    df = engineer_features(df)

    missing = [c for c in FEATURE_COLS if c not in df.columns]
    if missing:
        print(f"  ⚠️  Missing cols (will fill 0): {missing}")
        for c in missing:
            df[c] = 0
    else:
        print(f"  ✅ All {len(FEATURE_COLS)} feature columns present")

    train_df = df[df["season"].isin(TRAIN_SEASONS)]
    val_df = df[df["season"].isin(VAL_SEASONS)]
    test_df = df[df["season"].isin(TEST_SEASONS)]
    print(f"  Train: {len(train_df):,} | Val: {len(val_df):,} | Test: {len(test_df):,}")

    pos_rate = df["is_impact_injury"].mean()
    print(f"  Overall impact injury rate: {pos_rate:.1%}")

    return train_df, val_df, test_df


def prepare_xy(df):
    X = pd.DataFrame()
    for col in FEATURE_COLS:
        X[col] = df[col] if col in df.columns else 0
    X = X[FEATURE_COLS].fillna(X.median(numeric_only=True))
    y = df[TARGET_COL].astype(int)
    return X, y


# ── SMOTE ─────────────────────────────────────────────────────────────────────
def apply_smote(X, y):
    print("[2/7] Applying SMOTE ...")
    scale_pos = int((y == 0).sum()) / max(int(y.sum()), 1)
    print(
        f"  Before — pos: {y.sum():,} | neg: {(y==0).sum():,} | scale_pos={scale_pos:.2f}"
    )
    sm = SMOTE(random_state=42)
    X_res, y_res = sm.fit_resample(X, y)
    print(f"  After  — pos: {y_res.sum():,} | neg: {(y_res==0).sum():,}")
    return X_res, y_res, scale_pos


# ── Optuna XGBoost ────────────────────────────────────────────────────────────
def tune_xgboost(X_train, y_train, X_val, y_val, scale_pos, n_trials=50):
    print(f"[3/7] Tuning XGBoost ({n_trials} trials) ...")

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
            "max_depth": trial.suggest_int("max_depth", 4, 12),
            "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.2, log=True),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "colsample_bylevel": trial.suggest_float("colsample_bylevel", 0.4, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 20),
            "gamma": trial.suggest_float("gamma", 0, 5),
            "reg_alpha": trial.suggest_float("reg_alpha", 0, 3),
            "reg_lambda": trial.suggest_float("reg_lambda", 0, 3),
            "scale_pos_weight": scale_pos,
            "random_state": 42,
            "verbosity": 0,
            "eval_metric": "auc",
            "early_stopping_rounds": 30,
        }
        model = xgb.XGBClassifier(**params)
        model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
        proba = model.predict_proba(X_val)[:, 1]
        return roc_auc_score(y_val, proba)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    print(f"  Best AUC: {study.best_value:.4f}")
    best = study.best_params
    best.update(
        {
            "scale_pos_weight": scale_pos,
            "random_state": 42,
            "verbosity": 0,
            "eval_metric": "auc",
            "early_stopping_rounds": 30,
        }
    )
    model = xgb.XGBClassifier(**best)
    model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)
    return model, study.best_value


# ── Optuna LightGBM ───────────────────────────────────────────────────────────
def tune_lgbm(X_train, y_train, X_val, y_val, scale_pos, n_trials=50):
    print(f"[4/7] Tuning LightGBM ({n_trials} trials) ...")

    def objective(trial):
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 200, 1000),
            "max_depth": trial.suggest_int("max_depth", 4, 12),
            "learning_rate": trial.suggest_float("learning_rate", 0.005, 0.2, log=True),
            "num_leaves": trial.suggest_int("num_leaves", 20, 200),
            "subsample": trial.suggest_float("subsample", 0.5, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.4, 1.0),
            "min_child_samples": trial.suggest_int("min_child_samples", 5, 100),
            "reg_alpha": trial.suggest_float("reg_alpha", 0, 3),
            "reg_lambda": trial.suggest_float("reg_lambda", 0, 3),
            "scale_pos_weight": scale_pos,
            "random_state": 42,
            "verbosity": -1,
        }
        model = lgb.LGBMClassifier(**params)
        model.fit(
            X_train,
            y_train,
            eval_set=[(X_val, y_val)],
            callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(-1)],
        )
        proba = model.predict_proba(X_val)[:, 1]
        return roc_auc_score(y_val, proba)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)

    print(f"  Best AUC: {study.best_value:.4f}")
    best = study.best_params
    best.update({"scale_pos_weight": scale_pos, "random_state": 42, "verbosity": -1})
    model = lgb.LGBMClassifier(**best)
    model.fit(
        X_train,
        y_train,
        eval_set=[(X_val, y_val)],
        callbacks=[lgb.early_stopping(30, verbose=False), lgb.log_evaluation(-1)],
    )
    return model, study.best_value


# ── Threshold optimisation on val ─────────────────────────────────────────────
def best_threshold(model, X_val, y_val):
    proba = model.predict_proba(X_val)[:, 1]
    best_t, best_f1 = 0.5, 0.0
    for t in np.arange(0.10, 0.61, 0.01):
        preds = (proba >= t).astype(int)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_f1:
            best_f1, best_t = f, float(t)
    return round(best_t, 2), round(best_f1, 4)


# ── Evaluate ──────────────────────────────────────────────────────────────────
def evaluate(model, threshold, X_val, y_val, X_test, y_test, label):
    print(f"\n[5/7] Evaluating {label} at threshold={threshold} ...")
    results = {}
    for name, X, y in [("Val", X_val, y_val), ("Test", X_test, y_test)]:
        proba = model.predict_proba(X)[:, 1]
        preds = (proba >= threshold).astype(int)
        auc = roc_auc_score(y, proba)
        f1 = f1_score(y, preds, zero_division=0)
        rec = recall_score(y, preds, zero_division=0)
        prec = precision_score(y, preds, zero_division=0)
        print(f"\n  ── {name} ──")
        print(
            classification_report(y, preds, target_names=["No Injury", "Impact Injury"])
        )
        print(f"  AUC-ROC: {auc:.4f}")
        results[name] = {
            "auc": round(auc, 4),
            "f1": round(f1, 4),
            "recall": round(rec, 4),
            "precision": round(prec, 4),
        }
    return results


# ── SHAP ──────────────────────────────────────────────────────────────────────
def run_shap(model, X_test, model_name):
    print(f"\n[6/7] Computing SHAP ({model_name}) ...")
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_test)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]

    plt.figure(figsize=(10, 10))
    shap.summary_plot(shap_vals, X_test, feature_names=FEATURE_COLS, show=False)
    path = os.path.join(MODELS_DIR, "shap_summary.png")
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  SHAP plot → {path}")

    mean_shap = np.abs(shap_vals).mean(axis=0)
    ranked = mean_shap.argsort()[::-1]

    print("\n  Top 10 features by mean |SHAP|:")
    for rank, i in enumerate(ranked[:10], 1):
        print(f"    {rank:2}. {FEATURE_COLS[i]:<38} {mean_shap[i]:.4f}")

    print("\n  Surface features (key for paper):")
    for feat in [
        "home_surface_type",
        "avg_injury_surface",
        "turf_exposure",
        "surface_consistency",
        "pos_x_surface",
        "age_x_surface",
    ]:
        if feat in FEATURE_COLS:
            idx = FEATURE_COLS.index(feat)
            rank = ranked.tolist().index(idx) + 1
            print(f"    {feat:<38} rank #{rank:2}  |SHAP|={mean_shap[idx]:.4f}")

    return shap_vals


# ── Save ──────────────────────────────────────────────────────────────────────
def save(model, threshold, results, model_name):
    print(f"\n[7/7] Saving {model_name} ...")
    with open(os.path.join(MODELS_DIR, "xgboost_model.pkl"), "wb") as f:
        pickle.dump(model, f)
    with open(os.path.join(MODELS_DIR, "feature_columns.json"), "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)
    meta = {
        "model": model_name,
        "threshold": threshold,
        "val": results.get("Val", {}),
        "test": results.get("Test", {}),
        "train_seasons": TRAIN_SEASONS,
        "val_seasons": VAL_SEASONS,
        "test_seasons": TEST_SEASONS,
        "features": FEATURE_COLS,
        "n_features": len(FEATURE_COLS),
        "days_cap": DAYS_CAP,
        "note": "Threshold optimised on val by F1. High recall tradeoff for medical risk system.",
    }
    with open(os.path.join(MODELS_DIR, "model_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved → {MODELS_DIR}/")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PitchGuard — Model Training v2")
    print("=" * 60)

    train_df, val_df, test_df = load_and_split()
    X_train, y_train = prepare_xy(train_df)
    X_val, y_val = prepare_xy(val_df)
    X_test, y_test = prepare_xy(test_df)

    X_train_res, y_train_res, scale_pos = apply_smote(X_train, y_train)

    xgb_model, xgb_auc = tune_xgboost(
        X_train_res, y_train_res, X_val, y_val, scale_pos, n_trials=50
    )
    lgb_model, lgb_auc = tune_lgbm(
        X_train_res, y_train_res, X_val, y_val, scale_pos, n_trials=50
    )

    if xgb_auc >= lgb_auc:
        best_model, best_name = xgb_model, "XGBoost"
        print(f"\n  Winner: XGBoost (AUC={xgb_auc:.4f} vs LGBM={lgb_auc:.4f})")
    else:
        best_model, best_name = lgb_model, "LightGBM"
        print(f"\n  Winner: LightGBM (AUC={lgb_auc:.4f} vs XGB={xgb_auc:.4f})")

    threshold, val_f1 = best_threshold(best_model, X_val, y_val)
    print(f"  Optimal threshold (val F1): {threshold} → F1={val_f1:.4f}")

    results = evaluate(best_model, threshold, X_val, y_val, X_test, y_test, best_name)
    run_shap(best_model, X_test, best_name)
    save(best_model, threshold, results, best_name)

    print("\n✅ Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
