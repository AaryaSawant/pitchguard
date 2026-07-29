"""
PitchGuard — Hypothesis test: surface type and impact injury risk
File: src/model/hypothesis_test.py

Purpose: the tree models (v2 XGB/LGB, v4 stack, v5 CatBoost) are for
predictive performance. This script is for the paper's core claim —
"controlling for injury history, workload, and age, is artificial turf
exposure associated with impact injury risk?" — with a coefficient,
odds ratio, 95% CI, and p-value, not a SHAP rank.

Uses statsmodels Logit (not sklearn) because we need standard errors /
p-values / CIs, which sklearn's LogisticRegression doesn't expose.

Model: full training + val + test data pooled (this is inference, not
prediction — we're not holding out data to test generalization, we're
estimating a population effect as precisely as possible). Standard errors
clustered by player (tm_id) since each player contributes multiple
player-seasons — without clustering, repeated observations per player
would understate the true standard errors and overstate significance.

Run:
    python src/model/hypothesis_test.py

Outputs:
    data/models/hypothesis_test_summary.txt   (full statsmodels output)
    data/models/hypothesis_test_results.json  (surface coefs/ORs/CIs/p-values)
    data/models/hypothesis_test_forest.png    (odds ratio forest plot)
"""

import json
import os
import warnings

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")

DATA_PATH = "data/processed/model_dataset.csv"
MODELS_DIR = "data/models"
os.makedirs(MODELS_DIR, exist_ok=True)

TARGET_COL = "is_impact_injury"
DAYS_CAP = 730

# Player ID column used for clustered standard errors — confirmed against
# model_dataset.csv's actual columns.
PLAYER_ID_COL = "player_tm_id"

# ── Variable of interest vs. controls ───────────────────────────────────
# Keep this model deliberately smaller than the tree models — the point of
# a hypothesis-test regression is a clean, explainable coefficient on
# surface exposure, not maximum predictive power. Too many correlated
# controls inflates standard errors and makes the surface coefficient
# unstable (multicollinearity), so we pick one clean representation per
# concept rather than throwing in every engineered variant.
#
# turf_exposure = appearances * home_surface_type, so it's mechanically
# collinear with home_surface_type (turf_exposure is 0 whenever
# home_surface_type is 0). Putting both in one regression makes it
# arbitrary which one "absorbs" the significance. Fit them as two SEPARATE
# models instead, each with the other surface var dropped, so each gets a
# clean, independent estimate. Report both — if they tell the same story
# (same direction, both plausible), that's a robustness check, not
# redundancy.
SURFACE_MODELS = {
    "home_surface_type": "home_surface_type",
    "turf_exposure": "turf_exposure",
}

CONTROL_VARS = [
    "age_at_season_start",
    "height_cm",
    "injury_count_prior",
    "days_since_last_injury",
    "career_impact_rate",
    "total_appearances",
    "workload_spike",
    "has_acl",
    "has_hamstring",
    "has_ankle",
    "has_meniscus",
]


def load_data():
    print(f"[1/5] Loading {DATA_PATH} ...")
    df = pd.read_csv(DATA_PATH)

    df["days_since_last_injury"] = df["days_since_last_injury"].clip(upper=DAYS_CAP)

    all_needed = list(SURFACE_MODELS.values()) + CONTROL_VARS + [TARGET_COL]
    missing = [c for c in all_needed if c not in df.columns]
    if missing:
        raise KeyError(f"Missing columns needed for hypothesis test: {missing}")

    if PLAYER_ID_COL not in df.columns:
        print(
            f"  ⚠️  '{PLAYER_ID_COL}' not found — clustered SEs will be skipped, "
            f"falling back to robust (HC1) SEs. Check the actual player-ID "
            f"column name in model_dataset.csv and update PLAYER_ID_COL."
        )
    else:
        print(f"  ✅ Clustering standard errors by '{PLAYER_ID_COL}'")

    df = df.dropna(subset=all_needed).copy()
    print(f"  Rows after dropping NA in model vars: {len(df):,}")
    print(f"  Impact injury rate: {df[TARGET_COL].mean():.1%}")
    return df


def standardize(df, cols):
    """Z-score continuous vars so coefficients are comparable in magnitude.
    Binary vars (has_acl etc, home_surface_type) are left as-is — z-scoring
    a 0/1 variable doesn't help interpretability and breaks the clean
    'present vs absent' odds ratio reading."""
    df = df.copy()
    for c in cols:
        if df[c].nunique() > 2:  # continuous
            df[c] = (df[c] - df[c].mean()) / df[c].std()
    return df


def fit_logit(df, surface_var):
    model_vars = [surface_var] + CONTROL_VARS
    df_std = standardize(df, model_vars)

    y, X = df_std[TARGET_COL].astype(int), sm.add_constant(df_std[model_vars])
    model = sm.Logit(y, X)

    if PLAYER_ID_COL in df.columns:
        result = model.fit(
            cov_type="cluster",
            cov_kwds={"groups": df[PLAYER_ID_COL]},
            disp=False,
        )
    else:
        result = model.fit(cov_type="HC1", disp=False)

    return result, model_vars


def summarize(result, label):
    print(f"\n  Model summary ({label}):\n")
    print(result.summary())

    fname = f"hypothesis_test_summary_{label}.txt"
    with open(os.path.join(MODELS_DIR, fname), "w") as f:
        f.write(str(result.summary()))
    print(f"\n  Full summary saved → {MODELS_DIR}/{fname}")


def odds_ratios(result, model_vars, surface_var, label):
    params = result.params
    conf = result.conf_int()
    conf.columns = ["ci_lower", "ci_upper"]
    pvals = result.pvalues

    out = {}
    print(f"\n  {'Variable':<28}{'OR':>8}{'95% CI':>20}{'p-value':>12}")
    print("  " + "-" * 68)
    for var in model_vars:
        or_val = np.exp(params[var])
        ci_low = np.exp(conf.loc[var, "ci_lower"])
        ci_high = np.exp(conf.loc[var, "ci_upper"])
        p = pvals[var]
        flag = "  ← surface" if var == surface_var else ""
        print(
            f"  {var:<28}{or_val:>8.3f}   [{ci_low:.3f}, {ci_high:.3f}]{p:>12.4f}{flag}"
        )
        out[var] = {
            "coef": round(float(params[var]), 4),
            "odds_ratio": round(float(or_val), 4),
            "ci_lower": round(float(ci_low), 4),
            "ci_upper": round(float(ci_high), 4),
            "p_value": round(float(p), 4),
            "is_surface_var": var == surface_var,
        }

    fname = f"hypothesis_test_results_{label}.json"
    with open(os.path.join(MODELS_DIR, fname), "w") as f:
        json.dump(
            {
                "surface_var": surface_var,
                "n_obs": int(result.nobs),
                "pseudo_r2": round(float(result.prsquared), 4),
                "log_likelihood": round(float(result.llf), 2),
                "variables": out,
            },
            f,
            indent=2,
        )
    print(f"\n  Results saved → {MODELS_DIR}/{fname}")
    return out


def forest_plot(results_dict, surface_var, label):
    vars_sorted = sorted(
        results_dict.keys(), key=lambda v: results_dict[v]["odds_ratio"]
    )
    ors = [results_dict[v]["odds_ratio"] for v in vars_sorted]
    lowers = [
        results_dict[v]["odds_ratio"] - results_dict[v]["ci_lower"] for v in vars_sorted
    ]
    uppers = [
        results_dict[v]["ci_upper"] - results_dict[v]["odds_ratio"] for v in vars_sorted
    ]
    colors = [
        "#d62728" if results_dict[v]["is_surface_var"] else "#7f7f7f"
        for v in vars_sorted
    ]

    fig, ax = plt.subplots(figsize=(8, 6))
    y_pos = np.arange(len(vars_sorted))
    ax.errorbar(
        ors,
        y_pos,
        xerr=[lowers, uppers],
        fmt="o",
        color="black",
        ecolor="black",
        elinewidth=1,
        capsize=3,
        zorder=2,
    )
    for i, (o, c) in enumerate(zip(ors, colors)):
        ax.scatter(o, i, color=c, s=60, zorder=3)
    ax.axvline(1.0, linestyle="--", color="gray", linewidth=1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(vars_sorted)
    ax.set_xlabel("Odds Ratio (95% CI)")
    ax.set_title(
        f"Impact injury risk — odds ratios ({label})\n(red = surface variable: {surface_var})"
    )
    plt.tight_layout()
    path = os.path.join(MODELS_DIR, f"hypothesis_test_forest_{label}.png")
    plt.savefig(path, dpi=150)
    plt.close()
    print(f"  Forest plot → {path}")


def main():
    print("=" * 60)
    print("  PitchGuard — Hypothesis Test (Logistic Regression)")
    print("=" * 60)

    df = load_data()
    clustered = PLAYER_ID_COL in df.columns

    headline = {}
    for i, (label, surface_var) in enumerate(SURFACE_MODELS.items(), 1):
        print(
            f"\n[{i}/{len(SURFACE_MODELS)}] Fitting model: surface_var = '{surface_var}' "
            f"(other surface var excluded to avoid collinearity)"
        )
        result, model_vars = fit_logit(df, surface_var)
        summarize(result, label)
        results_dict = odds_ratios(result, model_vars, surface_var, label)
        forest_plot(results_dict, surface_var, label)
        headline[surface_var] = results_dict[surface_var]

    print("\n" + "=" * 60)
    print(
        f"  Standard errors: {'clustered by player' if clustered else 'robust HC1 (NOT clustered)'}"
    )
    print("  Surface hypothesis — headline numbers for the paper:")
    for var, r in headline.items():
        sig = "significant" if r["p_value"] < 0.05 else "not significant"
        print(
            f"    {var}: OR={r['odds_ratio']} [{r['ci_lower']}, {r['ci_upper']}], "
            f"p={r['p_value']} ({sig} at α=0.05)"
        )
    print("=" * 60)
    print("\n✅ Done.")


if __name__ == "__main__":
    main()
