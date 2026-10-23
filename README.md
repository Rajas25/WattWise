# ⚡ WattWise — ML-Based Campus Energy Waste Detection & Analytics


[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue)](https://python.org)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688)](https://fastapi.tiangolo.com)
[![SQLite](https://img.shields.io/badge/Database-SQLite-07405E)](https://sqlite.org)
[![Tests](https://img.shields.io/badge/Tests-52%20passing-brightgreen)](#7-run-tests)

> **Detect Waste. Reduce Costs. Build a Smarter Campus.**

WattWise is a fully local, zero-cost academic ML project that detects, quantifies, and
financially evaluates electricity waste in university campus buildings.

**⚠️ Simulated Data Notice:** All campus telemetry is generated locally by the simulator.
No real energy meters or external services are required or connected.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Technology Stack](#3-technology-stack)
4. [Directory Structure](#4-directory-structure)
5. [Prerequisites](#5-prerequisites)
6. [Quick Start (All-in-One)](#6-quick-start)
7. [Run Tests](#7-run-tests)
8. [Create First Admin Account](#8-create-first-admin-account)
9. [API Documentation](#9-api-documentation)
10. [Authentication & Roles](#10-authentication--roles)
11. [ML Pipeline](#11-ml-pipeline)
12. [Known Limitations](#12-known-limitations)

---

## 1. Project Overview

WattWise detects electricity waste by:
1. **Predicting** expected power from weather, occupancy, and time.
2. **Flagging** cases where actual power exceeds the prediction *and* the building is unoccupied.
3. **Quantifying** financial impact in ₹ INR.
4. **Comparing** a contextual ML detector against Isolation Forest to show why domain-context matters.

**Best model:** XGBoost Regressor — R²=0.9038, MAE=2.106 kW on held-out test data.
**Detection:** F1=0.9647 vs. Isolation Forest F1=0.0168.

---

## 2. Architecture

```
┌─────────────────────────────────────────┐
│   Simulated Campus Telemetry            │
│   (backend/services/simulator.py)       │
└────────────────┬────────────────────────┘
                 │  POST /api/energy/readings
                 ▼
┌─────────────────────────────────────────┐
│   FastAPI Backend  (backend/main.py)    │
│   • /api/auth/*   — JWT authentication  │
│   • /api/energy/* — readings, dashboard │
│   • /api/ml/*     — predictions         │
│   • /api/admin/*  — admin operations    │
│   • /api/users/*  — user management     │
└──────────┬──────────────────┬───────────┘
           │                  │
    ┌──────▼──────┐   ┌───────▼────────┐
    │  SQLite DB  │   │ ML Models      │
    │  wattwise.db│   │ XGBoost + IsoF │
    └─────────────┘   └────────────────┘
           │
    ┌──────▼─────────────────────────────┐
    │  Static HTML/CSS/JS Frontend       │
    │  Served at http://localhost:8000   │
    │  Student & Admin dashboards        │
    └────────────────────────────────────┘
```

---

## 3. Technology Stack

| Layer | Technology |
|---|---|
| ML Pipeline | Python 3.14, Pandas, NumPy, Scikit-learn, XGBoost, Joblib |
| Streamlit Dashboard | Streamlit, Plotly |
| API Backend | FastAPI, Uvicorn |
| Database | SQLite (built-in `sqlite3`) |
| Authentication | JWT (`python-jose`), bcrypt 5.x |
| Frontend | HTML5, Vanilla CSS, JavaScript, Chart.js |
| Tests | Pytest, HTTPX |

---

## 4. Directory Structure

```
DSML_mini/
├── app.py                        ← Streamlit dashboard (standalone)
├── generate_data.py              ← Synthetic dataset generator
├── train_model.py                ← ML training pipeline
├── utils.py                      ← Core ML utilities
├── requirements.txt
├── .env.example                  ← Environment variable template
├── .gitignore
│
├── data/
│   ├── energy_data.csv           ← Synthetic dataset (90 days, 8640 rows)
│   └── wattwise.db               ← SQLite database (auto-created, gitignored)
│
├── models/
│   ├── best_model.joblib         ← Trained XGBoost pipeline (652 KB)
│   ├── isolation_forest.joblib   ← Isolation Forest model
│   ├── model_comparison.csv      ← Benchmark results
│   └── model_metadata.json       ← Metrics, features, thresholds
│
├── backend/                      ← FastAPI application
│   ├── main.py                   ← App entry point
│   ├── config.py                 ← Environment-based settings
│   ├── database.py               ← SQLite schema + init
│   ├── security.py               ← bcrypt + JWT
│   ├── create_admin.py           ← CLI to create first admin
│   ├── models/schemas.py         ← Pydantic request/response schemas
│   ├── routers/
│   │   ├── auth.py               ← /api/auth/* (login, register, /me)
│   │   ├── energy.py             ← /api/energy/* (readings, dashboard, alerts)
│   │   ├── ml.py                 ← /api/ml/* (predict, analyze)
│   │   ├── admin.py              ← /api/admin/* (admin dashboard, meters)
│   │   └── users.py              ← /api/users/* (user management)
│   └── services/
│       ├── ml_service.py         ← ML model integration
│       └── simulator.py          ← Simulated sensor data provider
│
├── frontend/                     ← Static HTML/CSS/JS (served by FastAPI)
│   ├── index.html                ← Landing page
│   ├── auth.html                 ← Login page (real backend auth)
│   ├── student-dashboard.html    ← Student module
│   ├── admin-dashboard.html      ← Admin module
│   ├── css/
│   └── js/
│       ├── api.js                ← Centralized API client
│       ├── dashboard-init.js     ← Auth guard + chart helpers
│       ├── data.js               ← JS simulation fallback
│       ├── student.js            ← Student page logic
│       └── admin.js              ← Admin page logic
│
└── tests/
    ├── test_backend.py           ← 52 backend tests
    ├── test_data.py              ← ML data generation tests
    ├── test_detection.py         ← Waste detection tests
    └── test_model.py             ← Model inference tests
```

---

## 5. Prerequisites

- **Python 3.11+** (tested on 3.14)
- No external accounts, cloud services, or paid APIs required

---

## 6. Quick Start

Run all commands from the project root (`c:\Users\rajas\DSML\DSML_mini`).

### Step 1 — Install dependencies

```powershell
pip install -r requirements.txt
```

### Step 2 — (Optional) Configure environment

```powershell
Copy-Item .env.example .env
# Edit .env to set WATTWISE_SECRET_KEY to a strong random value:
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Step 3 — Generate ML dataset and train models

> Skip if `data/energy_data.csv` and `models/best_model.joblib` already exist.

```powershell
python generate_data.py
python train_model.py
```

### Step 4 — Create your first Admin account

```powershell
python backend/create_admin.py
```
You will be prompted for email, name, and password. No credentials are hardcoded.

### Step 5 — Start the FastAPI backend

```powershell
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

The server starts at **http://localhost:8000** and:
- Initialises the SQLite database automatically on first run.
- Serves the frontend at `/`.
- Provides API docs at `/docs`.

### Step 6 — (Optional) Seed simulated data

In a separate PowerShell window:

```powershell
# One-time historical backfill (30 days)
python -m backend.services.simulator --days 30

# Or run continuously (generates one reading per building every 30 s)
python -m backend.services.simulator --loop --interval 30
```

### Step 7 — Open the application

| URL | Purpose |
|---|---|
| http://localhost:8000 | WattWise landing page |
| http://localhost:8000/auth.html | Login / Register |
| http://localhost:8000/student-dashboard.html | Student dashboard |
| http://localhost:8000/admin-dashboard.html | Admin dashboard |
| http://localhost:8000/docs | Interactive API documentation |

### Step 8 — (Optional) Run the Streamlit dashboard

The original Streamlit app still works independently:

```powershell
streamlit run app.py
```

---

## 7. Run Tests

```powershell
# All tests (ML + backend)
python -m pytest tests/ -v

# Backend only (52 tests)
python -m pytest tests/test_backend.py -v

# ML pipeline only
python -m pytest tests/test_data.py tests/test_detection.py tests/test_model.py -v
```

Tests use a **temporary isolated SQLite database** — your `data/wattwise.db` is never touched.

---

## 8. Create First Admin Account

```powershell
python backend/create_admin.py
```

After the first admin is created, additional admins can be created via:
- `POST /api/users/` endpoint (admin auth required)
- Running `create_admin.py` again

**No default credentials are hardcoded in the source code.**

---

## 9. API Documentation

Interactive Swagger UI is available at **http://localhost:8000/docs** while the server is running.

### Key Endpoints

| Method | Endpoint | Role | Description |
|---|---|---|---|
| `GET` | `/api/health` | Public | System health check |
| `POST` | `/api/auth/token` | Public | Login → JWT token |
| `POST` | `/api/auth/register` | Public | Self-register as student |
| `GET` | `/api/auth/me` | Any | Get own profile |
| `GET` | `/api/energy/buildings` | Any | List campus buildings |
| `GET` | `/api/energy/dashboard` | Any | KPI summary |
| `GET` | `/api/energy/daily-trend` | Any | Daily energy trend |
| `GET` | `/api/energy/hourly-profile` | Any | 24-hour power profile |
| `POST` | `/api/energy/readings` | Any | Submit a meter reading |
| `GET` | `/api/energy/anomalies` | Any | List waste events |
| `GET` | `/api/energy/alerts` | Any | List alerts |
| `GET` | `/api/ml/info` | Any | Loaded model details |
| `POST` | `/api/ml/predict` | Any | Single power prediction |
| `POST` | `/api/ml/analyze` | Any | Batch waste analysis |
| `GET` | `/api/admin/dashboard` | Admin | Full admin summary |
| `GET` | `/api/admin/meters` | Admin | Meter status |
| `GET` | `/api/users/` | Admin | List all users |
| `POST` | `/api/users/` | Admin | Create user with any role |
| `PATCH` | `/api/users/{id}` | Admin | Update user role/status |

---

## 10. Authentication & Roles

### How Authentication Works

1. Client POSTs `{email, password}` to `/api/auth/token`
2. Server validates credentials from SQLite using bcrypt
3. Server returns a **JWT Bearer token** (expires after 60 minutes by default)
4. Client includes `Authorization: Bearer <token>` on all subsequent requests
5. Every protected endpoint validates the token server-side

### Roles

| Role | Permissions |
|---|---|
| `student` | View buildings, energy data, anomalies, alerts, own profile |
| `admin` | All student permissions + user management, admin dashboard, meter status, anomaly acknowledgement |

**Role enforcement is server-side.** A student cannot gain admin access by modifying JavaScript,
localStorage, URL parameters, or request headers.

### Token Security

- Passwords are hashed with bcrypt (cost factor 12) with SHA-256 pre-hashing for passwords > 72 bytes.
- Tokens are signed with HS256 using `WATTWISE_SECRET_KEY` from `.env`.
- No passwords or hashes are ever returned in API responses.
- Rate limiting: max 10 login attempts per minute per IP.

---

## 11. ML Pipeline

### Detection Algorithm

```
residual_kw = actual_power_kw − predicted_power_kw
is_waste = (residual_kw ≥ 10.0 kW) AND (occupancy ≤ 5 persons)
```

**Important distinction:**
- **Anomaly** — statistical deviation detected by the model.
- **Potential waste event** — anomaly with high residual AND low occupancy → flagged by WattWise.
- **Confirmed waste** — requires on-site physical verification by facilities staff.

WattWise reports *potential* waste events, not confirmed waste.

### Model Performance (on held-out test set)

| Model | MAE | RMSE | R² | MAPE |
|---|---|---|---|---|
| Linear Regression | 3.257 kW | 5.644 kW | 0.8922 | 13.97% |
| Random Forest | 2.128 kW | 5.409 kW | 0.9010 | 10.36% |
| **XGBoost** ✅ | **2.106 kW** | **5.330 kW** | **0.9038** | **10.07%** |

| Detector | Precision | Recall | F1 |
|---|---|---|---|
| Contextual ML (WattWise) | 93.2% | 100% | **96.47%** |
| Isolation Forest | 1.28% | 2.44% | 1.68% |

---

## 12. Known Limitations

| Limitation | Notes |
|---|---|
| No real sensor data | All readings are labelled `data_source='simulated'` |
| Streamlit app branding | `app.py` still shows "Building Energy Waste Detective" title |
| No real-time WebSocket | Dashboard requires manual refresh or page reload |
| Single flat electricity tariff | Real billing often uses time-of-day pricing |
| Simulated anomaly injection | ~4% of idle-hour readings have injected waste spikes |
| No HTTPS | Run behind a reverse proxy (nginx) for any real deployment |
| No email notifications | Alert system is dashboard-only |

---

## Development Notes

- The SQLite database is at `data/wattwise.db` by default. Set `WATTWISE_DATABASE_URL` in `.env` to change it.
- The ML model at `models/best_model.joblib` is loaded once at startup. Retrain with `python train_model.py`.
- The simulator and Streamlit app can run simultaneously alongside the FastAPI backend.
- All API responses include `data_source_note: "Simulated campus telemetry"` where relevant.
**Detect energy waste. Analyze consumption. Support smarter campus energy management.**

WattWise is a machine-learning-based project that analyzes campus building energy-consumption data to identify unusual usage patterns and estimate the potential financial impact of energy waste.

The project combines synthetic energy-data generation, preprocessing, regression-based prediction, anomaly detection, financial-loss estimation, and an interactive Streamlit dashboard.

## ✨ Features

- **Synthetic Energy Data Generation:** Generates sample energy-consumption data for experimentation.
- **Feature Engineering:** Prepares and processes data for machine-learning workflows.
- **Energy Consumption Prediction:** Trains three regression models to estimate expected energy consumption.
- **Anomaly Detection:** Uses an Isolation Forest baseline to identify unusual observations.
- **Waste Analysis:** Applies contextual detection logic to help identify potential energy inefficiencies.
- **Financial Impact Estimation:** Estimates potential energy-waste costs in Indian rupees (INR).
- **Interactive Dashboard:** Provides a Streamlit interface with five tabs for exploring project outputs.
- **Frontend Demonstration:** Includes a separate HTML, CSS, and JavaScript interface.
- **Testing:** Includes pytest test files for selected project functionality.

## 🛠️ Technology Stack

- Python
- Streamlit
- Machine learning and regression
- Isolation Forest
- Data preprocessing and feature engineering
- HTML, CSS, and JavaScript
- pytest
- Git and GitHub

## 📂 Project Structure

```text
WattWise/
├── app.py
├── generate_data.py
├── train_model.py
├── utils.py
├── models/
├── tests/
├── frontend/
├── docs/
├── .gitignore
└── README.md
```

The exact contents of each directory depend on the current repository. The `docs/` folder can be used for the project audit and other documentation.

## 🚀 Getting Started

### Prerequisites

- Python 3
- Git
- Visual Studio Code or another code editor

### 1. Clone the repository

```bash
git clone https://github.com/Rajas25/WattWise.git
cd WattWise
```

### 2. Create a virtual environment

**Windows PowerShell:**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

If `requirements.txt` is present:

```bash
python -m pip install -r requirements.txt
```

If it is not present, install the packages required by the project and create a `requirements.txt` containing the verified dependencies.

### 4. Generate sample data

```bash
python generate_data.py
```

Review the script to confirm the configured output path before running it.

### 5. Train the models

```bash
python train_model.py
```

The training script is intended to train the project's regression models and save the resulting artifacts.

### 6. Launch the dashboard

```bash
streamlit run app.py
```

Open the local URL shown in your terminal.

### 7. Run tests

```bash
python -m pytest
```

Run the commands from the project root. The actual dependencies, file paths, and execution requirements should be verified against the current source code.

## 🔄 Workflow

1. Generate synthetic energy-consumption data.
2. Preprocess the data and engineer features.
3. Train regression models to estimate expected usage.
4. Detect unusual observations using anomaly-detection techniques.
5. Assess potential energy waste.
6. Estimate the possible financial impact.
7. Visualize results in the Streamlit dashboard.

## ⚠️ Current Scope and Limitations

- The current prototype uses synthetic data rather than verified live campus electricity readings.
- Live electricity-meter and IoT sensor integration is not implemented.
- The standalone frontend demonstration is not connected to the Python dashboard backend.
- The audited implementation does not include a dedicated database/API backend or implemented authentication and role-based access control.
- Anomaly detection identifies observations for investigation; it does not independently prove that energy was wasted.
- Financial estimates depend on the assumptions, electricity rates, and data used.

## 🔮 Future Enhancements

- Integrate real-world campus energy data.
- Add live electricity-meter or IoT sensor support.
- Improve forecasting and model evaluation.
- Add building-wise energy-consumption comparisons.
- Connect the frontend to a backend API.
- Implement secure authentication and role-based access control.
- Introduce historical reports, alerts, and dashboards.
- Validate the system using real campus data.

## 🎯 Objective

WattWise explores how machine learning and data analytics can help identify potentially inefficient electricity consumption and communicate its possible financial impact, providing a foundation for future campus energy-efficiency solutions.

## 👨‍💻 Repository

GitHub: https://github.com/Rajas25/WattWise

## 📄 License

No open-source license has been specified yet. Add a `LICENSE` file if you choose to publish the project under a particular license.

---

**WattWise — Turning energy data into actionable insights.**
>>>>>>> origin/main
