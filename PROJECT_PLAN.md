# Federated AI-Based Patient Footfall Forecasting and Intelligent Workforce Planning System
**PSG Institute of Medical Sciences & Research (PSG IMSR) — Department of Pulmonology**

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [System Architecture](#2-system-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Module Breakdown](#4-module-breakdown)
5. [Data Sources & Features](#5-data-sources--features)
6. [Federated Learning Design](#6-federated-learning-design)
7. [Forecasting Engine](#7-forecasting-engine)
8. [Workforce Planning Engine](#8-workforce-planning-engine)
9. [API Design](#9-api-design)
10. [Frontend Dashboard](#10-frontend-dashboard)
11. [Development Phases](#11-development-phases)
12. [Directory Structure](#12-directory-structure)

---

## 1. Project Overview

| Field | Detail |
|---|---|
| **Organization** | PSG Institute of Medical Sciences & Research, Coimbatore |
| **Department** | Pulmonology |
| **Problem** | No intelligent system to forecast patient inflow or optimize doctor scheduling |
| **Patient Volume** | 60–80 (low demand) to 170–180 (high demand) per day |
| **Doctors** | ~25 in the Pulmonology department |
| **Historical Data** | 2 years of OP/IP records |
| **Core Constraint** | Patient data must never leave hospital servers (Federated Learning) |

### Goals

- Predict daily and weekly OP/IP patient inflow 1–4 weeks in advance
- Integrate environmental, temporal, institutional, and holiday-based features
- Preserve data privacy through Federated Learning
- Optimize doctor leave planning through predictive workload redistribution
- Generate actionable planning insights for department administrators

---

## 2. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ADMIN DASHBOARD                          │
│              (React + TypeScript + Tailwind CSS)                │
└────────────────────────────┬────────────────────────────────────┘
                             │ REST API
┌────────────────────────────▼────────────────────────────────────┐
│                        FASTAPI BACKEND                          │
│  ┌─────────────────┐  ┌──────────────────┐  ┌───────────────┐  │
│  │ Forecast Engine │  │ Workforce Planner│  │  Auth / RBAC  │  │
│  └────────┬────────┘  └────────┬─────────┘  └───────────────┘  │
│           │                   │                                 │
│  ┌────────▼────────────────────▼─────────┐                      │
│  │         Federated Learning Layer      │                      │
│  │    (Flower Aggregation Server)        │                      │
│  └────────────────────────────────────┬──┘                      │
└───────────────────────────────────────┼─────────────────────────┘
                                        │ Parameters only (no raw data)
┌───────────────────────────────────────▼─────────────────────────┐
│                    HOSPITAL LOCAL NODE                          │
│  ┌────────────────┐  ┌─────────────────┐  ┌──────────────────┐  │
│  │  PostgreSQL DB │  │  Local FL Client│  │  Redis Cache     │  │
│  │  (OP/IP data)  │  │  (trains locally│  │  (forecasts)     │  │
│  └────────────────┘  └─────────────────┘  └──────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    EXTERNAL DATA SOURCES                        │
│   AQI (CPCB/OpenAQ)   │   Weather (Open-Meteo)   │   Holidays   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 3. Tech Stack

### Backend
| Component | Technology | Reason |
|---|---|---|
| API Framework | **FastAPI** (Python 3.11+) | Async, auto-docs, fast |
| Federated Learning | **Flower (flwr 1.x)** | Lightweight, production-ready FL |
| Forecasting (primary) | **Prophet + XGBoost** ensemble | Handles seasonality, holidays, trends; works well with ~730 rows |
| Forecasting (future/research) | **LSTM or TFT via PyTorch** | Only viable with 4+ years of data; risk of overfitting on 2-year dataset |
| Task Queue | **Celery + Redis** | Async model training & forecast jobs |
| Database | **PostgreSQL 15** | Structured OP/IP records |
| Cache | **Redis 7** | Forecast result caching |
| ORM | **SQLAlchemy 2.0** | Database abstraction |
| Data Processing | **Pandas + NumPy** | Feature engineering |
| Validation | **Pydantic v2** | Request/response schemas |

### Frontend
| Component | Technology | Reason |
|---|---|---|
| Framework | **React 18 + TypeScript** | Type safety, ecosystem |
| Styling | **Tailwind CSS** | Rapid UI development |
| Charts | **Recharts** | Composable, React-native charts |
| State Management | **Zustand** | Lightweight, simple |
| Data Fetching | **TanStack Query** | Caching, background refetch |
| UI Components | **shadcn/ui** | Accessible, customizable |
| Date Handling | **date-fns** | Lightweight date utilities |

### DevOps & Infrastructure
| Component | Technology |
|---|---|
| Containerization | Docker + Docker Compose |
| Environment Config | python-dotenv / .env files |
| API Testing | Pytest + httpx |
| Linting | Ruff (Python), ESLint (TypeScript) |
| Package Manager | uv (Python), pnpm (Node) |

---

## 4. Module Breakdown

```
System
├── Module 1: Data Ingestion & Feature Engineering
├── Module 2: Federated Learning Pipeline
├── Module 3: Forecasting Engine
├── Module 4: Workforce Planning Engine
│   ├── 4a: Leave Impact Simulation
│   ├── 4b: Pre-Leave Workload Optimization
│   └── 4c: Smart Leave Recommendation
├── Module 5: REST API Layer
└── Module 6: Admin Dashboard
```

### Module Responsibilities

| Module | Input | Output |
|---|---|---|
| Data Ingestion | OP/IP records, AQI, weather, holidays | Cleaned feature matrix |
| FL Pipeline | Local patient data | Aggregated global model weights |
| Forecasting Engine | Feature matrix + model | Daily/weekly OP/IP volume forecast |
| Leave Impact Sim | Doctor leave request + forecast | Feasibility score, redistributed load |
| Pre-Leave Optimizer | Doctor schedule + forecast | Workload adjustment plan |
| Leave Recommender | 4-week forecast | Optimal leave windows |
| Admin Dashboard | API responses | Interactive visualizations |

---

## 5. Data Strategy

> **No real data available yet.** All development and training will use synthetic data
> generated to match the statistical properties described in the problem statement.
> When real hospital data becomes available, it can be swapped in with no code changes.

---

### 5.1 Synthetic Data Generator

A dedicated script (`data/generate_synthetic.py`) will produce 2 years of realistic daily records.

**Rules baked into the generator:**

| Rule | Detail |
|---|---|
| Base OP range | 60–80 (low) to 170–180 (high) per day |
| Monday/Tuesday boost | +20–30% above weekly average |
| Weekend boost | +10–15% (IT professionals available) |
| Public holiday drop | −40–50% |
| School reopening spike | +15–20% for 2 weeks in June and January |
| High AQI (>150) boost | +25–35% (respiratory cases rise) |
| Rainfall drop | −10–20% on heavy rain days |
| Winter peak (Dec–Jan) | +20% seasonal respiratory trend |
| IP count | ~15–20% of daily OP count |
| Follow-ups | ~25–30% of previous week's OP count |
| Doctor availability | 23–25 doctors on normal days; 20–22 on holidays |
| Random noise | ±5–8% Gaussian noise on all counts |

**Output files:**
```
data/synthetic/
├── daily_records.csv       # 730 rows — one per day (Jan 2024 – Dec 2025)
├── doctors.csv             # 25 doctors with specialization + join date
├── leave_requests.csv      # Historical leave records for training
└── aqi_weather.csv         # Synthetic AQI + weather aligned to Coimbatore norms
```

**Schema — `daily_records.csv`:**
```
date, op_count, ip_count, total_footfall, aqi, temperature, humidity,
rainfall, is_holiday, is_weekend, is_monday, is_tuesday, is_school_reopening,
doctors_available, scheduled_followups, active_ip_patients
```

---

### 5.2 Environmental Features
| Feature | Source (now) | Source (when real data available) |
|---|---|---|
| AQI | Synthetic (Coimbatore norms: 80–200 range) | CPCB / OpenAQ API |
| Temperature (°C) | Synthetic (Coimbatore: 22–38°C range) | Open-Meteo API |
| Humidity (%) | Synthetic (Coimbatore: 50–90% range) | Open-Meteo API |
| Rainfall (mm) | Synthetic (monsoon pattern Jun–Sep) | Open-Meteo API |

### 5.3 Temporal & Social Features
| Feature | Encoding |
|---|---|
| Day of week | One-hot (Mon–Sun) |
| Is weekend | Binary |
| Is public holiday | Binary (India + Tamil Nadu calendar) |
| School reopening period | Binary |
| Week of year | Cyclical sin/cos |
| Month | Cyclical sin/cos |

### 5.4 Institutional Features
- Number of scheduled follow-ups (next 7 days)
- Active IP patients
- Doctor headcount available

### 5.5 Target Variables
- `op_count` — daily outpatient volume
- `ip_count` — daily inpatient volume
- `total_footfall` — combined daily count

---

## 6. Federated Learning Design

### Architecture: Centralized Federated Learning (Star Topology)

```
Hospital Node 1 (Pulmonology) ──┐
Hospital Node 2 (future dept)  ──┼──► FL Aggregation Server (FedAvg)
Hospital Node N (future)        ──┘         │
                                      Global Model
                                      (no raw data leaves nodes)
```

### FL Workflow per Round

```
1. Server initializes global model weights
2. Server sends weights → each local node
3. Each node trains on local data (N epochs)
4. Each node sends updated weights → server
5. Server aggregates weights (FedAvg algorithm)
6. Repeat until convergence
7. Distribute final global model
```

### Privacy Guarantees
- Raw patient data never transmitted
- Only model parameter deltas shared
- Future: Differential Privacy noise injection
- Future: Secure Aggregation (SMPC)

### Flower (flwr) Components
| Component | Role |
|---|---|
| `fl.server.start_server()` | Aggregation server |
| `fl.client.start_client()` | Hospital-side local trainer |
| `FedAvg` strategy | Weight aggregation algorithm |
| `NumPyClient` | Model weight serialization |

---

## 7. Forecasting Engine

### Model Selection Rationale

With 2 years (~730 rows) of historical data, model choice matters:

| Model | Suitability | Reason |
|---|---|---|
| **Prophet** | Best | Built for seasonality + holidays; interpretable; works on small datasets |
| **XGBoost** | Best | Handles tabular features (AQI, day-of-week, lags); no minimum data requirement |
| **Prophet + XGBoost Ensemble** | Primary choice | Combines seasonal pattern recognition with feature-driven prediction |
| LSTM | Not recommended now | Needs 4+ years of data to generalize; will overfit on 730 rows |
| Transformer / TFT | Not recommended now | Very data-hungry; overkill for this dataset size |

> LSTM or TFT can be introduced in a future version if data grows to 4+ years.

### Model: Hybrid Ensemble (Primary)

```
Input Features
     │
     ├──► Prophet Model (trend + seasonality + holidays)
     │         handles: weekly peaks, respiratory season, Indian holidays
     │
     └──► XGBoost Model (environmental + institutional features)
               handles: AQI, temperature, rainfall, lag features
               │
               ▼
        Ensemble (weighted average)
          Prophet weight: 0.5  |  XGBoost weight: 0.5
          (tunable based on validation performance)
               │
               ▼
        Daily OP/IP Forecast (7, 14, 28 days)
```

### Prophet Configuration
- Custom Indian public holidays calendar
- Weekly seasonality (Monday/Tuesday peaks)
- Annual seasonality (respiratory season peaks)
- AQI as an additional regressor

### XGBoost Features
- All engineered features from Section 5
- Lag features: `footfall_lag_7`, `footfall_lag_14`
- Rolling averages: 7-day, 14-day rolling mean

### Output Schema
```json
{
  "date": "2026-05-20",
  "op_forecast": 142,
  "ip_forecast": 28,
  "total_forecast": 170,
  "confidence_interval": { "lower": 155, "upper": 185 },
  "demand_level": "HIGH",
  "risk_flags": ["monday_peak", "high_aqi"]
}
```

---

## 8. Workforce Planning Engine

### 8a. Leave Impact Simulation

**Input:** Doctor ID, leave start date, leave end date
**Process:**
1. Fetch forecast for requested leave period
2. Calculate baseline load per doctor (total_forecast / available_doctors)
3. Redistribute departing doctor's load across remaining 24
4. Check if redistributed load exceeds safe threshold (configurable, e.g. 8 patients/hr)
5. Compute feasibility score (0–100)

**Feasibility Score Formula:**
```
score = 100 × (1 - (redistributed_load - baseline_load) / max_safe_load)
score ≥ 70  → APPROVED (green)
40 ≤ score < 70  → REVIEW REQUIRED (yellow)
score < 40  → NOT RECOMMENDED (red)
```

### 8b. Pre-Leave Workload Optimization Plan

When a doctor plans future leave, the system generates:
- List of follow-up patients to advance before leave date
- Recommended consultation slot increases in preceding days
- IP round redistribution suggestions
- OP slot adjustments to clear backlog

### 8c. Smart Leave Recommendation

**Output:** 4-week calendar showing:
- Green windows — low footfall, safe for leave
- Yellow windows — moderate load, possible with handover
- Red windows — peak days, leave not advisable

---

## 9. API Design

### Base URL: `/api/v1`

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/forecasts/daily?from=&to=` | Get daily forecasts for date range |
| `GET` | `/forecasts/weekly?weeks=4` | Get weekly aggregated forecasts |
| `POST` | `/leave/simulate` | Simulate leave impact |
| `GET` | `/leave/recommend/{doctor_id}` | Get smart leave windows |
| `POST` | `/leave/optimize-plan` | Generate pre-leave workload plan |
| `GET` | `/doctors` | List all doctors + availability |
| `GET` | `/doctors/{id}/workload` | Doctor workload history + forecast |
| `POST` | `/fl/train` | Trigger federated training round |
| `GET` | `/fl/status` | FL training status + model version |
| `GET` | `/alerts/active` | Active peak/low demand alerts |
| `GET` | `/dashboard/summary` | Admin dashboard summary stats |

---

## 10. Frontend Dashboard

### Design Language (inspired by reference UI)

- **Layout:** Two-column split — action/input panel (left) + AI insights panel (right, blue card)
- **Color palette:** White cards on light grey background; royal blue (`#2563EB`) for AI insight panels and CTAs
- **Typography:** Bold section headers, subdued helper text below
- **Cards:** Rounded corners (`rounded-2xl`), subtle shadows, internal section dividers
- **Tags/Badges:** Small pill badges — color-coded (green = safe, amber = warning, red = alert, blue = fixed)
- **Data grids:** 2×2 stat grids inside cards for quick metrics
- **Horizontal bars:** For AI influence/feature importance breakdowns
- **Toggles + Steppers:** For configuration inputs (not just dropdowns)
- **Dual CTA pattern:** One dark primary button + one ghost/outline secondary button per page

---

### Pages / Views

#### 1. Overview
**Left:** Today's summary card (date, day type, demand level badge), 7-day forecast bar chart, active peak/low alerts list
**Right (blue):** AI context card — AQI status, weather volatility, seasonal respiratory risk, weekly demand signal; Expected load stat at bottom

#### 2. Forecast
**Left:** 28-day calendar heatmap (color-coded by demand level: green/amber/red), OP vs IP toggle
**Right (blue):** Forecast confidence panel — predicted range, model confidence %, top influencing factors as horizontal bars; FL privacy note at bottom

#### 3. Leave Planner *(primary reference from uploaded screenshot)*
**Left:**
- Leave Configuration card: calendar multi-select, leave type dropdown, full/half day toggle, "Simulate Impact" button
- Workload Strategy card: checkboxes (advance follow-ups, redistribute OP slots, increase pre-leave slots), max patients per doctor stepper with recommended limit warning
- Dual CTA: "Generate AI Forecast & Apply" (dark) + "Check Best Leave Window" (outline)

**Right:**
- AI Forecast Insights (blue card): environmental context 2×2 grid, demand pattern signals list, institutional load 2×2 grid, AI influence breakdown horizontal bars, FL privacy note
- Pending Conflicts card: alert count badge, conflict list with FIXED/FLEXIBLE tags, patient details + dates, "View Detailed Schedule" link
- Expected load footer stat

#### 4. Smart Leave
**Left:** 4-week calendar grid — cells color-coded (green = safe, amber = moderate, red = peak), legend, selected range highlight
**Right (blue):** Recommendation panel — top 3 suggested windows with reasoning (low AQI, low follow-ups, etc.), risk summary for user-selected dates

#### 5. Workload
**Left:** Doctor-wise load distribution horizontal bar chart (all 25 doctors), filter by date range
**Right:** Redistribution simulation card — shows load shift when a doctor is absent, highlight doctors near capacity threshold in amber/red

#### 6. FL Status
**Left:** Training round timeline (round number, date, participating nodes, status)
**Right (blue):** Model health card — current model version, last trained date, accuracy metrics (MAPE, RMSE), node status indicators

---

### Reusable UI Components

| Component | Description |
|---|---|
| `InsightCard` | Blue right-panel card with section dividers — used across all pages |
| `StatGrid` | 2×2 grid of metric tiles inside a card |
| `InfluenceBar` | Labelled horizontal progress bar for feature importance |
| `DemandBadge` | Pill badge — HIGH (red) / MODERATE (amber) / LOW (green) |
| `ConflictItem` | Conflict row with FIXED/FLEXIBLE tag, patient name, date |
| `CalendarPicker` | Multi-date select calendar with demand-level cell coloring |
| `StepperInput` | Number stepper with min/max warning label |
| `DualCTA` | Dark primary + ghost secondary button pair |
| `ForecastChart` | Bar/line chart with confidence interval bands |
| `CalendarHeatmap` | 28-day grid with demand color fill |
| `AlertBanner` | Top-of-page dismissible peak/low demand alert |

---

## 11. Development Phases (8-Week Plan)

### Scope Decision: Build vs Defer

| Feature | Decision | Reason |
|---|---|---|
| Prophet + XGBoost forecasting | **Build** | Core of the project |
| Federated Learning (single node) | **Build (simplified)** | Key requirement; single-node FL is sufficient for demo |
| Leave impact simulation + feasibility score | **Build** | High-value, well-defined output |
| Smart leave recommendation (4-week calendar) | **Build** | Directly uses forecast output, low extra effort |
| Pre-leave workload optimizer | **Defer** | Complex scheduling logic, low time ROI |
| Redis caching | **Defer** | Use in-memory cache for now |
| Auth / RBAC | **Defer** | Not needed for demo/prototype |
| Docker Compose | **Build (Week 8)** | Needed for final demo |
| Multi-node FL | **Defer** | Single node proves the concept |

---

### Week 1 — Foundation + Synthetic Data
- [ ] Project scaffolding (monorepo: `/backend`, `/frontend`, `/data`, `/notebooks`)
- [ ] **Synthetic data generator** (`data/generate_synthetic.py`) — 730 days of OP/IP + AQI + weather + holidays
- [ ] Validate synthetic data: plot distributions, confirm seasonal patterns look realistic
- [ ] PostgreSQL schema: `daily_records`, `doctors`, `forecasts`, `leave_requests`
- [ ] Seed database with synthetic data
- [ ] FastAPI app skeleton + health check endpoint

### Week 2 — Feature Engineering & EDA
- [ ] Feature engineering pipeline (lag features, cyclical encoding, holiday flags)
- [ ] EDA notebook (patterns, seasonality, correlations)
- [ ] Holiday calendar for India (Tamil Nadu public holidays)
- [ ] Data validation + cleaning pipeline

### Week 3 — Forecasting Engine
- [ ] Prophet model: train, tune, evaluate (MAPE, RMSE)
- [ ] XGBoost model: train, tune, evaluate
- [ ] Ensemble: weighted average layer
- [ ] Model comparison notebook
- [ ] Save/load model artifacts

### Week 4 — Forecast API + Federated Learning
- [ ] Forecast API endpoints (`/forecasts/daily`, `/forecasts/weekly`)
- [ ] Flower server setup (aggregation server)
- [ ] Flower client setup (local hospital node)
- [ ] FedAvg training round (single node, proof of concept)
- [ ] FL status API (`/fl/status`, `/fl/train`)

### Week 5 — Workforce Planning Engine
- [ ] Leave impact simulation (load redistribution logic)
- [ ] Feasibility scoring algorithm (0–100 scale)
- [ ] Smart leave recommendation (4-week window analysis)
- [ ] Workforce planning API endpoints (`/leave/simulate`, `/leave/recommend`)

### Week 6 — Dashboard (Core Pages)
- [ ] React + TypeScript + Tailwind app scaffolding
- [ ] Overview page: 7-day forecast chart + demand badges + alerts
- [ ] Forecast page: 28-day calendar heatmap + OP/IP split chart
- [ ] Leave Planner page: doctor selector + date picker + feasibility gauge

### Week 7 — Dashboard (Remaining Pages) + Integration
- [ ] Smart Leave page: 4-week color-coded calendar
- [ ] Workload page: doctor-wise load distribution chart
- [ ] FL Status page: training round tracker + model version
- [ ] End-to-end integration testing (frontend ↔ API ↔ models)
- [ ] Bug fixes + polish

### Week 8 — Testing, Docker & Demo
- [ ] Unit tests for forecasting + workforce planning modules
- [ ] Docker Compose setup (backend + frontend + PostgreSQL)
- [ ] Swap-in guide: document how to replace synthetic data with real hospital data
- [ ] Final demo walkthrough
- [ ] Project documentation update

---

## 12. Directory Structure

```
imsr-pulmonology/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/
│   │   │       ├── forecasts.py
│   │   │       ├── leave.py
│   │   │       ├── doctors.py
│   │   │       ├── fl.py
│   │   │       └── dashboard.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── database.py
│   │   ├── models/
│   │   │   ├── db/              # SQLAlchemy ORM models
│   │   │   └── schemas/         # Pydantic schemas
│   │   ├── services/
│   │   │   ├── forecasting/
│   │   │   │   ├── prophet_model.py
│   │   │   │   ├── xgboost_model.py
│   │   │   │   ├── ensemble.py
│   │   │   │   └── lstm_model.py      # future: only if data grows to 4+ years
│   │   │   ├── federated/
│   │   │   │   ├── server.py
│   │   │   │   └── client.py
│   │   │   ├── workforce/
│   │   │   │   ├── leave_simulator.py
│   │   │   │   ├── workload_optimizer.py
│   │   │   │   └── leave_recommender.py
│   │   │   └── ingestion/
│   │   │       ├── aqi_fetcher.py
│   │   │       ├── weather_fetcher.py
│   │   │       └── holiday_calendar.py
│   │   └── main.py
│   ├── tests/
│   ├── pyproject.toml
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── charts/
│   │   │   ├── leave/
│   │   │   └── ui/
│   │   ├── pages/
│   │   │   ├── Overview.tsx
│   │   │   ├── Forecast.tsx
│   │   │   ├── LeavePlanner.tsx
│   │   │   ├── SmartLeave.tsx
│   │   │   ├── Workload.tsx
│   │   │   └── FLStatus.tsx
│   │   ├── store/
│   │   ├── hooks/
│   │   └── lib/
│   ├── package.json
│   └── Dockerfile
│
├── data/
│   ├── raw/                     # Historical OP/IP records
│   ├── processed/               # Feature-engineered datasets
│   └── synthetic/               # Mock data for development
│
├── notebooks/
│   ├── eda.ipynb                        # Exploratory data analysis
│   ├── feature_engineering.ipynb
│   ├── model_evaluation.ipynb           # Prophet vs XGBoost vs Ensemble comparison
│   └── lstm_experiment.ipynb            # Future: LSTM experiment when data > 4 years
│
├── docker-compose.yml
├── .env.example
└── PROJECT_PLAN.md
```

---

*Last updated: May 2026 | Version 1.4 — No real data available; synthetic data generator added as Week 1 priority; real data swap-in documented for Week 8*
