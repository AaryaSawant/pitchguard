"""
PitchGuard — CatBoost-only training (v5)
File: src/model/train_catboost.py

Goal: close the val/test AUC gap seen in v2 (SMOTE + XGB/LGB, gap=0.022) and
v4 (4-model stack, gap=0.031). Same data loading / feature engineering /
chronological split as train.py — only the model + tuning strategy changes.

Changes vs train.py (v2):
  - No SMOTE. Class weighting via scale_pos_weight only (v4 already showed
    this beats SMOTE: val AUC 0.625 vs 0.589).
  - CatBoost only, no stacking (v4's stack beat solo CatBoost by just 0.0013
    val AUC while widening the test gap — not worth the extra variance).
  - Tightened Optuna search space (shallower depth, forced subsampling,
    explicit L2, higher min leaf size) + fewer trials (60 vs 200) to reduce
    search-level overfitting.
  - Hyperparameters selected via rolling-origin CV (3 folds walking forward
    through seasons) instead of one fixed val split, so we're not just
    fitting whatever quirk of 23/24 happens to maximize AUC.
  - strong_foot_right / strong_foot_left dropped — suspected artifact,
    ranked #1/#3 by SHAP in v2 ahead of every injury-history feature, which
    doesn't hold up on inspection.

Run:
    python src/model/train_catboost.py

Outputs:
    data/models/catboost_model_v5.cbm
    data/models/feature_columns_v5.json
    data/models/shap_catboost_v5.png
    data/models/model_meta_v5.json
"""

import json
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import shap
import optuna
from catboost import CatBoostClassifier
from sklearn.metrics import (
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
    classification_report,
)

warnings.filterwarnings("ignore")
optuna.logging.set_verbosity(optuna.logging.WARNING)

# ── Paths — identical to train.py ──────────────────────────────────────────
DATA_PATH = "data/processed/model_dataset.csv"
MODELS_DIR = "data/models"
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Feature columns — same as train.py FEATURE_COLS, minus strong_foot_* ──
FEATURE_COLS = [
    "age_at_season_start",
    "height_cm",
    # "strong_foot_right",   # dropped — see module docstring
    # "strong_foot_left",    # dropped — see module docstring
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


# ── Feature engineering — identical to train.py ────────────────────────────
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
    if "injury_burden" not in df.columns:
        df["injury_burden"] = 0.0
    return df


# ── Load + split — identical to train.py ───────────────────────────────────
def load_and_split():
    print(f"[1/8] Loading {DATA_PATH} ...")
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

    return df, train_df, val_df, test_df


def prepare_xy(df):
    X = pd.DataFrame()
    for col in FEATURE_COLS:
        X[col] = df[col] if col in df.columns else 0
    X = X[FEATURE_COLS].fillna(X.median(numeric_only=True))
    y = df[TARGET_COL].astype(int)
    return X, y


# ── Rolling-origin CV for hyperparameter selection ─────────────────────────
# Fold 1: train 19/20-20/21 -> val 21/22
# Fold 2: train 19/20-21/22 -> val 22/23
# Fold 3: train 19/20-22/23 -> val 23/24
# Averaged AUC across these picks hyperparams that generalize across
# seasons, not just whatever fits 23/24 specifically.
ROLLING_FOLDS = [
    (["19/20", "20/21"], ["21/22"]),
    (["19/20", "20/21", "21/22"], ["22/23"]),
    (["19/20", "20/21", "21/22", "22/23"], ["23/24"]),
]


def rolling_auc(full_df, params):
    aucs = []
    for tr_seasons, va_seasons in ROLLING_FOLDS:
        tr = full_df[full_df["season"].isin(tr_seasons)]
        va = full_df[full_df["season"].isin(va_seasons)]
        if len(tr) == 0 or len(va) == 0 or va[TARGET_COL].nunique() < 2:
            continue
        X_tr, y_tr = prepare_xy(tr)
        X_va, y_va = prepare_xy(va)
        m = CatBoostClassifier(**params, verbose=False)
        m.fit(X_tr, y_tr)
        p = m.predict_proba(X_va)[:, 1]
        aucs.append(roc_auc_score(y_va, p))
    return float(np.mean(aucs)) if aucs else 0.0


# ── Optuna: tightened search space ──────────────────────────────────────────
def tune_catboost(full_df, scale_pos, n_trials=60):
    print(f"[2/8] Tuning CatBoost ({n_trials} trials, rolling-origin CV) ...")

    def objective(trial):
        params = {
            "depth": trial.suggest_int("depth", 3, 5),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.1, log=True),
            "l2_leaf_reg": trial.suggest_float("l2_leaf_reg", 3.0, 15.0),
            "min_data_in_leaf": trial.suggest_int("min_data_in_leaf", 15, 60),
            "subsample": trial.suggest_float("subsample", 0.6, 0.8),
            "colsample_bylevel": trial.suggest_float("colsample_bylevel", 0.6, 0.8),
            "iterations": trial.suggest_int("iterations", 200, 600),
            "bootstrap_type": "Bernoulli",
            "scale_pos_weight": scale_pos,
            "eval_metric": "AUC",
            "random_seed": 42,
        }
        return rolling_auc(full_df, params)

    study = optuna.create_study(direction="maximize")
    study.optimize(objective, n_trials=n_trials, show_progress_bar=True)
    print(f"  Best rolling-CV AUC: {study.best_value:.4f}")

    best = dict(study.best_params)
    best.update(
        {
            "bootstrap_type": "Bernoulli",
            "scale_pos_weight": scale_pos,
            "eval_metric": "AUC",
            "random_seed": 42,
        }
    )
    return best, study.best_value


# ── Threshold optimisation on val — identical to train.py ──────────────────
def best_threshold(model, X_val, y_val):
    proba = model.predict_proba(X_val)[:, 1]
    best_t, best_f1 = 0.5, 0.0
    for t in np.arange(0.10, 0.61, 0.01):
        preds = (proba >= t).astype(int)
        f = f1_score(y_val, preds, zero_division=0)
        if f > best_f1:
            best_f1, best_t = f, float(t)
    return round(best_t, 2), round(best_f1, 4)


# ── Evaluate — identical to train.py ────────────────────────────────────────
def evaluate(model, threshold, X_val, y_val, X_test, y_test, label):
    print(f"\n[6/8] Evaluating {label} at threshold={threshold} ...")
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


# ── SHAP — identical structure to train.py ──────────────────────────────────
def run_shap(model, X_test, model_name):
    print(f"\n[7/8] Computing SHAP ({model_name}) ...")
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_test)
    if isinstance(shap_vals, list):
        shap_vals = shap_vals[1]

    plt.figure(figsize=(10, 10))
    shap.summary_plot(shap_vals, X_test, feature_names=FEATURE_COLS, show=False)
    path = os.path.join(MODELS_DIR, "shap_catboost_v5.png")
    plt.savefig(path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"  SHAP plot → {path}")

    mean_shap = np.abs(shap_vals).mean(axis=0)
    ranked = mean_shap.argsort()[::-1]

    print("\n  Top 15 features by mean |SHAP|:")
    for rank, i in enumerate(ranked[:15], 1):
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


# ── Save ─────────────────────────────────────────────────────────────────────
def save(model, threshold, results, best_params, model_name):
    print(f"\n[8/8] Saving {model_name} ...")
    model.save_model(os.path.join(MODELS_DIR, "catboost_model_v5.cbm"))
    with open(os.path.join(MODELS_DIR, "feature_columns_v5.json"), "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)
    meta = {
        "model": model_name,
        "threshold": threshold,
        "val": results.get("Val", {}),
        "test": results.get("Test", {}),
        "val_test_gap": round(
            results.get("Val", {}).get("auc", 0)
            - results.get("Test", {}).get("auc", 0),
            4,
        ),
        "train_seasons": TRAIN_SEASONS,
        "val_seasons": VAL_SEASONS,
        "test_seasons": TEST_SEASONS,
        "features": FEATURE_COLS,
        "n_features": len(FEATURE_COLS),
        "days_cap": DAYS_CAP,
        "best_params": best_params,
        "dropped_features": ["strong_foot_right", "strong_foot_left"],
        "note": "No SMOTE (class weighting only). CatBoost solo, no stack. "
        "Hyperparams selected via rolling-origin CV, not single fixed val split.",
    }
    with open(os.path.join(MODELS_DIR, "model_meta_v5.json"), "w") as f:
        json.dump(meta, f, indent=2)
    print(f"  Saved → {MODELS_DIR}/")


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  PitchGuard — CatBoost Training v5")
    print("=" * 60)

    full_df, train_df, val_df, test_df = load_and_split()
    X_train, y_train = prepare_xy(train_df)
    X_val, y_val = prepare_xy(val_df)
    X_test, y_test = prepare_xy(test_df)

    scale_pos = int((y_train == 0).sum()) / max(int(y_train.sum()), 1)
    print(
        f"[Train] positive rate: {y_train.mean():.1%} | scale_pos_weight: {scale_pos:.2f}"
    )

    best_params, cv_auc = tune_catboost(full_df, scale_pos, n_trials=60)

    print("\n[3/8] Fitting final model on train ...")
    model = CatBoostClassifier(**best_params, verbose=False)
    model.fit(X_train, y_train)

    print("[4/8] Computing val/test AUC ...")
    val_auc = roc_auc_score(y_val, model.predict_proba(X_val)[:, 1])
    test_auc = roc_auc_score(y_test, model.predict_proba(X_test)[:, 1])
    print(f"  Val AUC:  {val_auc:.4f}")
    print(f"  Test AUC: {test_auc:.4f}")
    print(f"  Val/Test gap: {val_auc - test_auc:.4f}  (v2 gap=0.022, v4 gap=0.031)")

    print("\n[5/8] Threshold sweep on val (F1) ...")
    threshold, val_f1 = best_threshold(model, X_val, y_val)
    print(f"  Optimal threshold: {threshold} → F1={val_f1:.4f}")

    results = evaluate(
        model, threshold, X_val, y_val, X_test, y_test, "CatBoost (solo)"
    )
    run_shap(model, X_test, "CatBoost (solo)")
    save(model, threshold, results, best_params, "CatBoost (solo)")

    print("\n✅ Done.")
    print("=" * 60)


if __name__ == "__main__":
    main()
