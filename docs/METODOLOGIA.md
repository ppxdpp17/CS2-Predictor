# Methodology & System Architecture

This document outlines the design decisions, feature engineering standards, model benchmarks, and production architecture for the CS2 Tier-1 Match Predictor.

---

## 1. Data Collection & Processing

Match and map data are scraped from [HLTV.org](https://www.hltv.org/stats/matches), filtered to Counter-Strike 2 matches involving HLTV Top 30 teams (since October 4, 2023).

* **Cloudflare Bypass**: HTTP requests use a session cookie (`cf_clearance`) to bypass Cloudflare protection (see [`docs/RENOVAR_COOKIE.md`](file:///c:/Users/Pedro/Desktop/pp/Projetos/CS2%20Predictor/docs/RENOVAR_COOKIE.md)).
* **Series Reconstruction**: Individual maps are grouped into complete Bo1/Bo3/Bo5 series based on temporal proximity rather than calendar dates to prevent merging distinct matches.
* **Filtering & Data Integrity**: Invalid matches (such as forfeits or overturned scores due to banned scripts) are excluded.
* **Dynamic Dataset**: The dataset expands automatically via daily pipelines (~3,020 initial baseline matches).

---

## 2. Prevention of Data Leakage

To accurately reflect real-world forecasting conditions:

1. **Strict Chronological Pipeline**: All dynamic features (Elo ratings, recent form, head-to-head records) are computed sequentially by timestamp. For any match on day $D$, only information available prior to $D$ is utilized.
2. **Post-Veto Feature Exclusion**: Map win-rate features are excluded from pre-match production models, as map choices are finalized only during vetoes right before match start.
3. **Temporal Holdout Evaluation**: Model performance is evaluated using an 80/20 temporal split (first 80% chronological matches for training, last 20% for testing) instead of randomized cross-validation.

---

## 3. Model Benchmarks & Feature Ablation

Models were evaluated on the 20% temporal holdout set:

| Model | Accuracy | Log Loss | Brier Score | Notes |
|---|:---:|:---:|:---:|---|
| **Logistic Regression** | **63.2%** | **0.645** | **0.226** | **Primary Production Model** — Optimal balance of accuracy, log loss, and interpretability. |
| **Baseline Elo** | 61.3% | — | — | Reference baseline (predicts higher team Elo wins). |
| **XGBoost Classifier** | 61.3% | 0.645 | — | Hyperparameter tuning (`GridSearchCV` + `TimeSeriesSplit`) converged to `max_depth=2`, showing added complexity does not improve performance. |
| **LR + Player Ratings** | 62.1% | 0.644 | — | Aggregated player ratings proved redundant with team Elo. |
| **LR + Roster Stability** | 63.1% | 0.646 | — | Isolated roster stability feature yielded no measurable gain. |

### Feature Ablation Findings
Aggregating individual player ratings or tracking roster stability provided no performance lift over team dynamic Elo. Team Elo implicitly captures overall player quality over time, making additional roster features redundant.

---

## 4. Probabilistic Calibration

Model probabilities were validated using calibration curves and Brier Score analysis. The Logistic Regression model achieved a **Brier Score of 0.226** (compared to 0.250 for a random 50/50 classifier), confirming that output probabilities are well-calibrated and reliable for confidence estimation.

---

## 5. Production Architecture

* **Full-Data Retraining**: Production models are retrained daily using 100% of historical data to maximize signal.
* **Multi-Model Predictions**: The Streamlit dashboard displays predictions from three models simultaneously (Baseline Elo, Logistic Regression, XGBoost) for direct comparison and live auditing.
* **Per-Map Extrapolation**: When veto results are available (`data-maps` attribute on HLTV), per-map win probabilities are estimated via log-odds averaging of the series-level model probability and the team's historical win rate on that map. This serves as an empirical heuristic rather than a trained map-level ML model.
* **Lineup Resolution**: Team lineups displayed in tooltips use a 3-tier fallback strategy:
  1. Confirmed match lineup (including stand-ins) from the match page.
  2. Official team roster (from team main page).
  3. Empty roster fallback.

---

## 6. MLOps & Continuous Automation

Two GitHub Actions workflows maintain continuous operations:

* **Hourly Workflow**: Captures predictions for upcoming/live games, checks match results, and logs real-world production accuracy in [`data/previsoes_log.csv`](file:///c:/Users/Pedro/Desktop/pp/Projetos/CS2%20Predictor/data/previsoes_log.csv).
* **Daily Workflow**: Scrapes newly completed matches, appends data to the historical dataset, and retrains production models.

---

## 7. Known Limitations

* **Economy & Round Data**: Round-by-round weapon and financial data are not currently tracked.
* **Pre-Veto Map Predictor**: Individual map predictions rely on win-rate heuristics because veto decisions occur immediately prior to match start.
* **Session Cookie Maintenance**: Scraping requires periodic manual renewal of the HLTV `cf_clearance` cookie ([`docs/RENOVAR_COOKIE.md`](file:///c:/Users/Pedro/Desktop/pp/Projetos/CS2%20Predictor/docs/RENOVAR_COOKIE.md)).