# ⚽ PitchGuard — Football Injury Risk Predictor

> **ML-powered, surface-aware impact injury prediction for professional football clubs**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![PRD Version](https://img.shields.io/badge/PRD-v0.1-lightgrey)](docs/PRD.md)

PitchGuard predicts per-player impact injury risk (ACL, hamstring, ankle ligament, meniscus) for upcoming matches by integrating **playing surface type**, player biomechanics, and workload data — the first multi-league ML system to treat artificial turf as a structured predictive feature.

---

## 📐 Architecture Overview

```
Scrapers (Transfermarkt + FBref)
        │
        ▼
  Raw Data (SQLite / PostgreSQL)
        │
        ▼
  Feature Engineering
  (workload, surface, congestion)
        │
        ▼
  ML Model (XGBoost / LightGBM)
  + SHAP Explainability
        │
        ▼
  Streamlit Dashboard
  (Squad risk overview + Player detail cards)
```

---

## 🗂️ Repository Structure

```
pitchguard/
├── data/
│   ├── raw/                  # Scraped raw data (gitignored)
│   ├── processed/            # Merged, cleaned datasets
│   └── surface_mapping/      # Stadium surface lookup table (~100 clubs)
├── src/
│   ├── scrapers/             # Transfermarkt & FBref scrapers
│   ├── features/             # Feature engineering pipeline
│   ├── model/                # Model training, tuning, evaluation
│   ├── dashboard/            # Streamlit app
│   └── utils/                # Shared helpers
├── notebooks/                # EDA and experimentation
├── tests/                    # Unit & integration tests
├── scripts/                  # Cron jobs, one-off utilities
├── docs/                     # PRD, paper drafts, methodology
└── requirements.txt
```

---

## 🚀 Quickstart

```bash
# 1. Clone & install
git clone https://github.com/YOUR_USERNAME/pitchguard.git
cd pitchguard
pip install -r requirements.txt

# 2. Run scrapers (Phase 1)
python src/scrapers/transfermarkt_scraper.py
python src/scrapers/fbref_scraper.py

# 3. Feature engineering (Phase 2)
python src/features/build_features.py

# 4. Train model (Phase 3)
python src/model/train.py

# 5. Launch dashboard (Phase 4)
streamlit run src/dashboard/app.py
```

---

## 🧠 ML Model

| Aspect | Detail |
|---|---|
| Problem type | Multi-class classification (Low / Medium / High risk) |
| Models | XGBoost, LightGBM, Random Forest |
| Explainability | SHAP values per prediction |
| Class imbalance | SMOTE oversampling |
| Evaluation | F1-score, AUC-ROC, Precision-Recall |
| Validation | Time-split: train 2019–2023, test 2024 |

### Risk Tiers

| Tier | Score | Action |
|---|---|---|
| 🟢 Low | 0–40% | No action needed |
| 🟡 Medium | 40–70% | Flag for physio review |
| 🔴 High | 70–100% | Restrict / monitor playing time |

---

## 📊 Data Sources

| Data | Source |
|---|---|
| Player bio | Transfermarkt, FBref |
| Injury history | Transfermarkt, Physioroom.com |
| Match logs | FBref |
| Stadium surface type | Wikipedia + Club official sites (manual) |

**Leagues covered:** Premier League · La Liga · Bundesliga · Serie A · Ligue 1 · Süper Lig (~100 clubs)

---

## 📄 Research Paper

**Target title:** *"Surface-Aware Machine Learning for Impact Injury Prediction in Professional Football: A Multi-League Study"*

**Core hypothesis:** Artificial turf is a statistically significant predictor of impact injuries when controlling for age, position, workload, and injury history.

**Target journals:** PLOS ONE · JSAMS · BMJ Open Sport & Exercise Medicine · Scientific Reports

---

## ⚠️ Known Limitations

- Training injury surface assumed to equal home stadium surface type
- No GPS/biomechanical sensor data (future work)
- Injury data uses games-missed as a proxy for confirmed injury records

---

## 🤝 Contributing

This is a 2-person independent research project. See [CONTRIBUTING.md](CONTRIBUTING.md) for branch strategy and code style guidelines.

---

*PitchGuard PRD v0.1 · Confidential · For internal use only*
