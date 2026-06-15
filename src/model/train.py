"""
PitchGuard — Model Training
File: src/model/train.py

Run:
    python src/model/train.py

Outputs:
    models/xgboost_model.pkl
    models/feature_columns.json
    models/shap_summary.png   (save figure for paper)
"""

import os
import json
import pickle
import warnings
import pandas as pd
import numpy as np
import xgboost as xgb
import shap
import matplotlib.pyplot as plt

from sklearn.metrics import classification_report, roc_auc_score
from imblearn.over_sampling import SMOTE

warnings.filterwarnings("ignore")

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_PATH = "data/processed/model_dataset.csv"
MODELS_DIR = "models"
os.makedirs(MODELS_DIR, exist_ok=True)

# ── Feature columns ───────────────────────────────────────────────────────────
# Stats columns (avg_minutes_per_game, total_appearances) may be NaN while
# the scraper is still running — they are included but NaNs are imputed below.
FEATURE_COLS = [
    "age_at_season_start",
    "height_cm",
    "is_goalkeeper",
    "is_defender",
    "is_midfielder",
    "is_forward",
    "strong_foot_right",
    "strong_foot_left",
    "home_surface_type",
    "injury_surface",
    "injury_count_prior",
    "injury_count_2yr",
    "injury_count_impact_prior",
    "days_since_last_injury",
    "has_acl",
    "has_hamstring",
    "has_ankle",
    "has_meniscus",
    "total_appearances",
    "avg_minutes_per_game",
]

TARGET_COL = "is_impact_injury"

# ── Season splits (NEVER shuffle — always chronological) ─────────────────────
TRAIN_SEASONS = ["19/20", "20/21", "21/22", "22/23"]
VAL_SEASONS = ["23/24"]
TEST_SEASONS = ["24/25", "25/26"]


def load_data():
    print(f"[1/7] Loading data from {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)
    print(f"      Rows: {len(df):,}  |  Columns: {df.shape[1]}")

    # Warn about missing stat columns so you know when scraper is still running
    missing_pct = df[["total_appearances", "avg_minutes_per_game"]].isna().mean() * 100
    for col, pct in missing_pct.items():
        if pct > 0:
            print(
                f"      ⚠️  {col} is {pct:.1f}% NaN (stats scraper still running — OK to proceed)"
            )

    return df


def split_data(df):
    print("[2/7] Splitting by season ...")

    train_df = df[df["season"].isin(TRAIN_SEASONS)]
    val_df = df[df["season"].isin(VAL_SEASONS)]
    test_df = df[df["season"].isin(TEST_SEASONS)]

    print(
        f"      Train: {len(train_df):,} rows | Val: {len(val_df):,} rows | Test: {len(test_df):,} rows"
    )

    if len(val_df) == 0:
        raise ValueError(
            "Validation set is empty — check that 'season' column uses format '23/24'."
        )

    return train_df, val_df, test_df


def prepare_xy(df):
    """Extract features + target; impute NaN stats with column median."""
    # Only keep columns that exist in the dataframe
    available = [c for c in FEATURE_COLS if c in df.columns]
    missing_cols = set(FEATURE_COLS) - set(available)
    if missing_cols:
        print(f"      ⚠️  These feature columns are not in the CSV yet: {missing_cols}")
        print(
            "         They will be filled with 0 — rerun train.py once build_features.py is rerun with full stats."
        )

    X = df[available].copy()

    # Add any missing feature columns as zeros so the model always sees the same shape
    for col in FEATURE_COLS:
        if col not in X.columns:
            X[col] = 0

    X = X[FEATURE_COLS]  # enforce column order

    # Impute NaN with median (safe for both sparse and full data)
    X = X.fillna(X.median(numeric_only=True))

    y = df[TARGET_COL].astype(int)
    return X, y


def apply_smote(X_train, y_train):
    print("[3/7] Applying SMOTE on training data only ...")
    print(
        f"      Before — positive: {y_train.sum():,} | negative: {(y_train==0).sum():,}"
    )
    sm = SMOTE(random_state=42)
    X_res, y_res = sm.fit_resample(X_train, y_train)
    print(f"      After  — positive: {y_res.sum():,} | negative: {(y_res==0).sum():,}")
    return X_res, y_res


def train_model(X_train_res, y_train_res, X_val, y_val):
    print("[4/7] Training XGBoost ...")

    scale_pos = len(y_train_res[y_train_res == 0]) / max(
        len(y_train_res[y_train_res == 1]), 1
    )

    model = xgb.XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        scale_pos_weight=scale_pos,
        eval_metric="logloss",
        early_stopping_rounds=20,
        verbosity=0,
    )

    model.fit(
        X_train_res,
        y_train_res,
        eval_set=[(X_val, y_val)],
        verbose=50,
    )

    print(f"      Best iteration: {model.best_iteration}")
    return model


def evaluate(model, X_val, y_val, X_test, y_test):
    print("[5/7] Evaluating ...")

    for split_name, X, y in [("Validation", X_val, y_val), ("Test", X_test, y_test)]:
        if len(y) == 0:
            print(f"      {split_name} set empty — skipping")
            continue
        preds = model.predict(X)
        proba = model.predict_proba(X)[:, 1]
        print(f"\n      ── {split_name} ──")
        print(
            classification_report(y, preds, target_names=["No Injury", "Impact Injury"])
        )
        try:
            auc = roc_auc_score(y, proba)
            print(f"      AUC-ROC: {auc:.4f}")
        except ValueError:
            print("      AUC-ROC: N/A (only one class in split)")


def run_shap(model, X_test):
    print("[6/7] Computing SHAP values ...")
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_test)

    # Global summary plot — save for paper Figure 1
    plt.figure()
    shap.summary_plot(shap_values, X_test, feature_names=FEATURE_COLS, show=False)
    fig_path = os.path.join(MODELS_DIR, "shap_summary.png")
    plt.savefig(fig_path, bbox_inches="tight", dpi=150)
    plt.close()
    print(f"      SHAP summary plot saved → {fig_path}")

    # Print top 5 features by mean |SHAP|
    mean_shap = np.abs(shap_values).mean(axis=0)
    top_idx = mean_shap.argsort()[::-1][:5]
    print("\n      Top 5 features by mean |SHAP|:")
    for rank, i in enumerate(top_idx, 1):
        print(f"        {rank}. {FEATURE_COLS[i]:<35} {mean_shap[i]:.4f}")

    return shap_values


def save_model(model):
    print("[7/7] Saving model and feature columns ...")
    model_path = os.path.join(MODELS_DIR, "xgboost_model.pkl")
    cols_path = os.path.join(MODELS_DIR, "feature_columns.json")

    with open(model_path, "wb") as f:
        pickle.dump(model, f)
    with open(cols_path, "w") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    print(f"      Model saved    → {model_path}")
    print(f"      Features saved → {cols_path}")


def main():
    print("=" * 55)
    print("  PitchGuard — Model Training")
    print("=" * 55)

    df = load_data()
    train_df, val_df, test_df = split_data(df)

    X_train, y_train = prepare_xy(train_df)
    X_val, y_val = prepare_xy(val_df)
    X_test, y_test = prepare_xy(test_df)

    X_train_res, y_train_res = apply_smote(X_train, y_train)

    model = train_model(X_train_res, y_train_res, X_val, y_val)
    evaluate(model, X_val, y_val, X_test, y_test)

    # SHAP on test set (or val if test is empty)
    shap_X = X_test if len(y_test) > 0 else X_val
    run_shap(model, shap_X)

    save_model(model)

    print(
        "\n✅ Done. Rerun this script after stats scraper finishes for full-data results."
    )
    print("=" * 55)


if __name__ == "__main__":
    main()
