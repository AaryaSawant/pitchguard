"""
PitchGuard Dashboard
--------------------
Streamlit app for club medical staff to monitor squad injury risk.

Run:
    streamlit run src/dashboard/app.py
"""

import pickle
from pathlib import Path

import pandas as pd
import streamlit as st

# ──────────────────────────────────────────────
# Config
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="PitchGuard",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

RISK_COLORS = {"Low": "#2ecc71", "Medium": "#f39c12", "High": "#e74c3c"}
RISK_LABELS = {0: "Low", 1: "Medium", 2: "High"}

MODEL_PATH = Path("models/pitchguard_xgboost.pkl")
SHAP_PATH = Path("models/shap_explainer.pkl")
FEATURES_PATH = Path("data/processed/features.parquet")

FEATURE_COLS = [
    "age", "height_cm", "weight_kg", "position_code",
    "injury_count_2y", "days_since_last_injury",
    "has_acl", "has_hamstring", "has_ankle", "has_meniscus",
    "minutes_last_30d", "games_last_14d", "season_minutes", "avg_minutes_per_game",
    "upcoming_surface", "home_surface", "is_home",
    "league_pl", "league_la_liga", "league_bundesliga",
    "league_serie_a", "league_ligue_1", "league_super_lig",
]


# ──────────────────────────────────────────────
# Data / model loading (cached)
# ──────────────────────────────────────────────
@st.cache_resource
def load_model():
    if not MODEL_PATH.exists():
        return None
    with open(MODEL_PATH, "rb") as f:
        return pickle.load(f)


@st.cache_resource
def load_shap_explainer():
    if not SHAP_PATH.exists():
        return None
    with open(SHAP_PATH, "rb") as f:
        return pickle.load(f)


@st.cache_data
def load_features():
    if not FEATURES_PATH.exists():
        return pd.DataFrame()
    return pd.read_parquet(FEATURES_PATH)


# ──────────────────────────────────────────────
# Sidebar navigation
# ──────────────────────────────────────────────
def sidebar():
    st.sidebar.image("docs/pitchguard_logo.png", use_column_width=True) if Path("docs/pitchguard_logo.png").exists() else st.sidebar.title("⚽ PitchGuard")
    st.sidebar.markdown("**Football Injury Risk Predictor**")
    st.sidebar.divider()

    df = load_features()
    if df.empty:
        st.sidebar.warning("No data loaded yet. Run the scrapers first.")
        return None, None

    leagues = sorted(df["league"].unique()) if "league" in df.columns else []
    selected_league = st.sidebar.selectbox("League", leagues)

    clubs = sorted(df[df["league"] == selected_league]["club"].unique()) if selected_league else []
    selected_club = st.sidebar.selectbox("Club", clubs)

    return selected_league, selected_club


# ──────────────────────────────────────────────
# Squad Overview
# ──────────────────────────────────────────────
def squad_overview(df: pd.DataFrame, model):
    st.header("🏟️ Squad Risk Overview")

    if df.empty or model is None:
        st.info("Load data and train a model to see squad risk scores.")
        return

    X = df[FEATURE_COLS].fillna(0)
    probs = model.predict_proba(X)
    df = df.copy()
    df["risk_score"] = (probs[:, 1] * 40 + probs[:, 2] * 100).clip(0, 100).round(1)
    df["risk_label"] = pd.cut(
        df["risk_score"],
        bins=[-1, 40, 70, 101],
        labels=["Low", "Medium", "High"],
    )

    # Sort options
    sort_by = st.selectbox("Sort by", ["risk_score", "position_code", "minutes_last_30d"])
    df = df.sort_values(sort_by, ascending=False)

    # Display table with coloured badges
    for _, row in df.iterrows():
        col1, col2, col3, col4, col5 = st.columns([3, 1, 1, 1, 1])
        risk = row.get("risk_label", "Low")
        color = RISK_COLORS.get(str(risk), "#aaa")

        with col1:
            st.markdown(f"**{row.get('player_name', 'Unknown')}**")
        with col2:
            st.markdown(f":{color.lstrip('#')}[{row.get('position_code', '')}]")
        with col3:
            st.metric("Risk", f"{row['risk_score']}%")
        with col4:
            badge = f":{color.lstrip('#')}[**{risk}**]"
            st.markdown(badge)
        with col5:
            if st.button("Detail →", key=f"btn_{row.get('player_id', '')}"):
                st.session_state["selected_player"] = row.to_dict()


# ──────────────────────────────────────────────
# Player Detail Card
# ──────────────────────────────────────────────
def player_detail(player: dict, model, explainer):
    st.header(f"🧑 {player.get('player_name', 'Player')} — Detail Card")

    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Risk Score")
        X = pd.DataFrame([player])[FEATURE_COLS].fillna(0)
        prob = model.predict_proba(X)[0]
        score = round((prob[1] * 40 + prob[2] * 100), 1)
        risk = "Low" if score < 40 else "Medium" if score < 70 else "High"
        color = RISK_COLORS[risk]
        st.markdown(f"<h1 style='color:{color}'>{score}% — {risk}</h1>", unsafe_allow_html=True)

        st.subheader("Injury Type Sub-scores")
        for inj_type in ["acl", "hamstring", "ankle", "meniscus"]:
            flag = player.get(f"has_{inj_type}", 0)
            st.progress(int(flag * score), text=f"{inj_type.upper()} risk")

    with col_right:
        st.subheader("Next Match Context")
        surface = "🟡 Artificial Turf" if player.get("upcoming_surface") == 1 else "🟢 Natural Grass"
        venue = "Home" if player.get("is_home") else "Away"
        st.metric("Surface", surface)
        st.metric("Venue", venue)
        st.metric("Minutes last 30d", player.get("minutes_last_30d", "N/A"))
        st.metric("Games last 14d", player.get("games_last_14d", "N/A"))

    if explainer:
        st.subheader("🔍 SHAP Explanation — Top Contributing Factors")
        shap_values = explainer.shap_values(X)
        # Show top 3 features for High risk class
        shap_for_high = shap_values[2][0] if isinstance(shap_values, list) else shap_values[0]
        feature_importance = pd.Series(dict(zip(FEATURE_COLS, shap_for_high)))
        top3 = feature_importance.abs().nlargest(3).index.tolist()
        st.markdown("**Top 3 drivers of High risk:**")
        for feat in top3:
            val = feature_importance[feat]
            direction = "↑ increases" if val > 0 else "↓ decreases"
            st.markdown(f"- `{feat}`: {direction} risk (SHAP={val:+.3f})")


# ──────────────────────────────────────────────
# Main app
# ──────────────────────────────────────────────
def main():
    model = load_model()
    explainer = load_shap_explainer()
    df = load_features()

    selected_league, selected_club = sidebar()

    if not selected_club:
        st.title("⚽ PitchGuard — Football Injury Risk Predictor")
        st.markdown(
            "Select a **league** and **club** from the sidebar to view squad injury risk scores."
        )
        return

    club_df = df[(df["league"] == selected_league) & (df["club"] == selected_club)].copy()

    if "selected_player" in st.session_state and st.session_state["selected_player"]:
        player_detail(st.session_state["selected_player"], model, explainer)
        if st.button("← Back to squad"):
            st.session_state["selected_player"] = None
    else:
        squad_overview(club_df, model)


if __name__ == "__main__":
    main()
