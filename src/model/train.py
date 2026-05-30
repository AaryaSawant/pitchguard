"""
PitchGuard Model Training
--------------------------
Trains XGBoost / LightGBM classifier for injury risk prediction.
Outputs: trained model, SHAP explainer, evaluation metrics.

Usage:
    python src/model/train.py --features data/processed/features.parquet \
                               --model xgboost --output models/
"""

import argparse
import json
import logging
import pickle
from pathlib import Path

import pandas as pd
import shap
from imblearn.over_sampling import SMOTE
from sklearn.metrics import (
    classification_report,
    roc_auc_score,
    f1_score,
)
from sklearn.preprocessing import label_binarize

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Features used for training — mirrors PRD Section 5
FEATURE_COLS = [
    "age",
    "height_cm",
    "weight_kg",
    "position_code",
    "injury_count_2y",
    "days_since_last_injury",
    "has_acl",
    "has_hamstring",
    "has_ankle",
    "has_meniscus",
    "minutes_last_30d",
    "games_last_14d",
    "season_minutes",
    "avg_minutes_per_game",
    "upcoming_surface",
    "home_surface",
    "is_home",
    "league_pl",
    "league_la_liga",
    "league_bundesliga",
    "league_serie_a",
    "league_ligue_1",
    "league_super_lig",
]

TARGET_COL = "risk_label"  # 0=Low, 1=Medium, 2=High
RISK_LABELS = {0: "Low", 1: "Medium", 2: "High"}


def load_data(features_path: str) -> pd.DataFrame:
    path = Path(features_path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    return pd.read_csv(path)


def time_split(df: pd.DataFrame, test_year: int = 2024):
    """
    Temporal train/test split to prevent data leakage.
    Train: up to end of test_year-1. Test: test_year onwards.
    """
    df["reference_date"] = pd.to_datetime(df["reference_date"])
    train = df[df["reference_date"].dt.year < test_year]
    test = df[df["reference_date"].dt.year >= test_year]
    logger.info(f"Train size: {len(train)}, Test size: {len(test)}")
    return train, test


def apply_smote(X: pd.DataFrame, y: pd.Series):
    """Apply SMOTE to handle class imbalance (injuries are rare events)."""
    smote = SMOTE(random_state=42)
    X_res, y_res = smote.fit_resample(X, y)
    logger.info(
        f"After SMOTE — class distribution: {pd.Series(y_res).value_counts().to_dict()}"
    )
    return X_res, y_res


def get_model(model_type: str):
    if model_type == "xgboost":
        from xgboost import XGBClassifier

        return XGBClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            use_label_encoder=False,
            eval_metric="mlogloss",
            random_state=42,
        )
    elif model_type == "lightgbm":
        from lightgbm import LGBMClassifier

        return LGBMClassifier(
            n_estimators=300,
            max_depth=6,
            learning_rate=0.05,
            random_state=42,
            verbose=-1,
        )
    elif model_type == "random_forest":
        from sklearn.ensemble import RandomForestClassifier

        return RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1)
    else:
        raise ValueError(f"Unknown model type: {model_type}")


def evaluate(model, X_test: pd.DataFrame, y_test: pd.Series) -> dict:
    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)

    y_bin = label_binarize(y_test, classes=[0, 1, 2])
    auc = roc_auc_score(y_bin, y_prob, multi_class="ovr", average="macro")

    report = classification_report(
        y_test, y_pred, target_names=list(RISK_LABELS.values()), output_dict=True
    )
    macro_f1 = f1_score(y_test, y_pred, average="macro")

    metrics = {
        "macro_auc_roc": round(auc, 4),
        "macro_f1": round(macro_f1, 4),
        "classification_report": report,
    }
    logger.info(f"Macro AUC-ROC: {auc:.4f} | Macro F1: {macro_f1:.4f}")
    return metrics


def compute_shap(model, X_train: pd.DataFrame, output_dir: Path):
    """Compute and save SHAP explainer for dashboard use."""
    logger.info("Computing SHAP values...")
    explainer = shap.TreeExplainer(model)

    explainer.shap_values(X_train.sample(min(500, len(X_train)), random_state=42))

    with open(output_dir / "shap_explainer.pkl", "wb") as f:
        pickle.dump(explainer, f)
    logger.info(f"SHAP explainer saved to {output_dir / 'shap_explainer.pkl'}")
    return explainer


def main(features_path: str, model_type: str, output_dir: str):
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load data
    df = load_data(features_path)
    missing_cols = [c for c in FEATURE_COLS + [TARGET_COL] if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing columns in dataset: {missing_cols}")

    df = df.dropna(subset=FEATURE_COLS)

    # Time split
    train_df, test_df = time_split(df)

    X_train = train_df[FEATURE_COLS]
    y_train = train_df[TARGET_COL]
    X_test = test_df[FEATURE_COLS]
    y_test = test_df[TARGET_COL]

    # Handle imbalance
    X_train_res, y_train_res = apply_smote(X_train, y_train)

    # Train
    model = get_model(model_type)
    logger.info(f"Training {model_type}...")
    model.fit(X_train_res, y_train_res)

    # Evaluate
    metrics = evaluate(model, X_test, y_test)

    # Save model
    model_file = output_path / f"pitchguard_{model_type}.pkl"
    with open(model_file, "wb") as f:
        pickle.dump(model, f)
    logger.info(f"Model saved to {model_file}")

    # Save metrics
    metrics_file = output_path / "metrics.json"
    with open(metrics_file, "w") as f:
        json.dump(metrics, f, indent=2)
    logger.info(f"Metrics saved to {metrics_file}")

    # SHAP
    compute_shap(model, X_train, output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--features", default="data/processed/features.parquet")
    parser.add_argument(
        "--model", default="xgboost", choices=["xgboost", "lightgbm", "random_forest"]
    )
    parser.add_argument("--output", default="models/")
    args = parser.parse_args()
    main(args.features, args.model, args.output)
