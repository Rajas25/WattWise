# Building Energy Waste Detective: ML-Based Energy Anomaly Detection

[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Streamlit](https://img.shields.io/badge/Dashboard-Streamlit-red.svg)](https://streamlit.io/)
[![Scikit-Learn](https://img.shields.io/badge/ML-Scikit--Learn-orange.svg)](https://scikit-learn.org/)
[![XGBoost](https://img.shields.io/badge/Ensemble-XGBoost-green.svg)](https://xgboost.ai/)

An academic Machine Learning mini-project designed to detect, quantify, and financially evaluate electricity waste across university campus buildings using supervised regression baselines and physics-informed contextual anomaly detection.

---

## 📌 1. Problem Statement & Motivation

Educational institutions and commercial buildings consume significant electricity, a large portion of which is inadvertently wasted due to:
- Lighting, projectors, and computers left powered on overnight or on weekends.
- HVAC (Air Conditioning) systems running at full cooling capacity in completely unoccupied lecture halls and classrooms.
- Equipment left running continuously in laboratories during semester breaks or holidays.

Traditional energy management systems rely on simple, static threshold rules (e.g., alert if power > 50 kW). These static rules fail because power draw fluctuates naturally with weather (ambient temperature/humidity) and occupancy. A high power draw is **justified** when an auditorium holds 100 students on a 36°C afternoon, but is **blatant waste** when observed in an empty classroom at 2:00 AM on Sunday.

### Core Project Objective
To develop an end-to-end Machine Learning pipeline that:
1. **Predicts Expected Power Consumption**: Models expected campus load as a function of weather, occupancy, time of day, and building type.
2. **Detects Actionable Energy Waste**: Isolates situations where actual power consumption significantly exceeds predicted expected power **and** space occupancy is zero or negligible.
3. **Quantifies Real Financial Impact**: Computes excess kilowatt-hours (kWh) and estimates financial loss in Indian Rupees (₹ INR).
4. **Compares Detection Methodologies**: Benchmarks the contextual ML residual detector against an unsupervised **Isolation Forest** baseline to highlight why generic outlier detectors are inadequate for energy waste auditing.

---

## 🏗️ 2. System Architecture & Methodology

```
┌────────────────────────────────┐
│   Campus Telemetry / Dataset   │
│   (Weather, Occupancy, Time)   │
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│     Feature Engineering        │
│ (Cooling Need, Business Hours, │
│  Sin/Cos Cyclical Hour, One-Hot│
└───────────────┬────────────────┘
                │
                ▼
┌────────────────────────────────┐
│  Chronological Train/Test Split│
│     (Strict Zero-Leakage)      │
└───────────────┬────────────────┘
                │
        ┌───────┴────────────────────────┐
        ▼                                ▼
┌─────────────────────────┐   ┌────────────────────────┐
│  Supervised Regression  │   │   Unsupervised Baseline│
│ (Linear, RF, XGBoost)   │   │   (Isolation Forest)   │
└───────────┬─────────────┘   └───────────┬────────────┘
            │ Predicted Baseline (kW)     │
            ▼                             │
┌─────────────────────────┐               │
│ Residual Error (e = y - ŷ)              │
└───────────┬─────────────┘               │
            │                             │
            ▼                             │
┌───────────────────────────────────┐     │
│ Contextual Waste Gatekeeper       │     │
│ (Residual >= Threshold AND        │     │
│  Occupancy <= Limit)              │     │
└───────────┬───────────────────────┘     │
            │                             │
            ▼                             ▼
┌──────────────────────────────────────────────┐
│  Financial Loss (INR ₹) & Waste Analytics    │
│  Interactive Streamlit Multi-Tab Dashboard   │
└──────────────────────────────────────────────┘
```

---

## 📊 3. Dataset Description & Simulation

The project includes `generate_data.py`, which generates 90 days of hourly telemetry (8,640 records) across 4 campus facilities:
1. **Academic Block A**: Lecture Halls & Classrooms.
2. **Library & Computing Hub**: Central Study & Server Rooms (continuous baseload).
3. **Science Complex**: Chemistry & Bio Labs (specialized equipment).
4. **Administrative Block**: Faculty & Office Cabins.

### Dataset Schema
| Column Name | Data Type | Physical Meaning / Units |
| :--- | :--- | :--- |
| `timestamp` | Datetime | Telemetry measurement time (hourly frequency) |
| `building` | String | Campus facility name |
| `zone` | String | Functional zone inside facility |
| `occupancy` | Integer | Headcount present in the zone (0 to 120 people) |
| `temperature` | Float | Ambient outdoor temperature (16.0°C to 42.0°C) |
| `humidity` | Float | Relative humidity (30.0% to 95.0%) |
| `hour` | Integer | Hour of day (0 to 23) |
| `day_of_week` | Integer | Day of week (0 = Monday, 6 = Sunday) |
| `is_weekend` | Integer | Flag: 1 if Saturday or Sunday, else 0 |
| `actual_power_kw` | Float | **Target Variable**: Measured power draw (kW) |
| `is_anomaly` | Integer | *Ground-truth label for evaluation only (not used in features)* |
| `anomaly_type` | String | Ground-truth waste category (e.g., Empty Room, Night HVAC) |

> ⚠️ **Academic Simulation Notice**: The dataset is synthetically simulated using thermodynamics, occupancy distributions, and equipment load curves. Ground-truth anomaly labels are strictly isolated for evaluation and are **never** passed into feature matrices.

---

## ⚙️ 4. Feature Engineering

To capture physical energy dynamics without data leakage:
1. **Cooling Degree Demand (`cooling_need`)**:
   $$\text{cooling\_need} = \max(0.0, \text{temperature} - 24.0)$$
   HVAC chillers activate primarily when ambient temperature exceeds human comfort baselines (24°C).
2. **Academic Business Hours (`is_business_hours`)**:
   Binary flag set to `1` during Monday–Friday between 08:00 and 18:00.
3. **Cyclical Clock Encoding (`hour_sin`, `hour_cos`)**:
   Transforms 24-hour cycles into continuous trigonometric waves so the algorithm recognizes hour 23 (11:00 PM) and hour 0 (12:00 AM) as adjacent.
   $$\text{hour\_sin} = \sin\left(\frac{2\pi \cdot \text{hour}}{24}\right), \quad \text{hour\_cos} = \cos\left(\frac{2\pi \cdot \text{hour}}{24}\right)$$
4. **One-Hot Encoding**: Categorical variables (`building`, `zone`) encoded via Scikit-Learn `ColumnTransformer`.

---

## 🤖 5. Machine Learning Models & Results

### Train/Test Split (Zero-Leakage)
- **Train Period**: First 80% chronologically (6,912 records: Jan 1 to Mar 13, 2026).
- **Test Period**: Final 20% chronologically (1,728 records: Mar 14 to Mar 31, 2026).
- *Strict chronological splitting ensures the model does not predict the past using future information.*

### Regression Benchmark Comparison
All three models were evaluated on the identical, unseen chronological test set:

| Model | MAE (kW) | RMSE (kW) | $R^2$ Score | MAPE (%) |
| :--- | :---: | :---: | :---: | :---: |
| **Linear Regression (Baseline)** | 3.257 kW | 5.644 kW | 0.8922 | 13.97% |
| **Random Forest Regressor** | 2.126 kW | 5.405 kW | 0.9011 | 10.35% |
| **XGBoost Regressor (Champion)** | **2.099 kW** | **5.317 kW** | **0.9043** | **10.09%** |

**XGBoost Regressor** achieved the highest $R^2$ score (0.9043) and lowest MAE (2.099 kW), and was saved as the primary production artifact.

---

## 🔍 6. Energy Waste Detection Logic

### A. Contextual Residual-Based Detection
1. Compute the model's regression residual:
   $$\text{Residual} = \text{Actual Power (kW)} - \text{Predicted Baseline (kW)}$$
2. Flag as **True Energy Waste** if:
   $$\text{Residual} \ge \tau_{\text{residual}} \quad (\text{default: } 10.0\text{ kW}) \quad \text{AND} \quad \text{Occupancy} \le \tau_{\text{occupancy}} \quad (\text{default: } 5\text{ people})$$
3. Compute financial loss in Indian Rupees:
   $$\text{Wasted Energy (kWh)} = \text{Residual (kW)} \times 1\text{ hour}$$
   $$\text{Financial Loss (₹)} = \text{Wasted Energy (kWh)} \times \text{Tariff Rate (₹8.50/kWh)}$$

### B. Contextual Detector vs. Isolation Forest Benchmark
Evaluating both methods against the ground-truth test-set waste incidents:

| Anomaly Detection Method | Precision | Recall | F1-Score | Accuracy |
| :--- | :---: | :---: | :---: | :---: |
| **Contextual ML Residual Detector** | **0.9318** | **1.0000** | **0.9647** | **0.9983** |
| **Isolation Forest (Unsupervised)** | 0.0128 | 0.0244 | 0.0168 | 0.9323 |

#### Confusion Matrix for Contextual Detector:
- **True Positives (TP)**: 41 (Waste correctly detected)
- **False Positives (FP)**: 3
- **True Negatives (TN)**: 1,684 (Normal operation correctly identified)
- **False Negatives (FN)**: 0 (No waste incidents missed)

---

## 💻 7. Installation and Execution

### 1. Prerequisites
Ensure Python 3.10+ is installed on your machine.

### 2. Navigate to Project Directory
```powershell
cd C:\Users\Netizens\.gemini\antigravity-ide\scratch\energy_waste_detective
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Step-by-Step Execution

#### Step A: Generate Synthetic Campus Dataset
```bash
python generate_data.py
```
*Outputs: `data/energy_data.csv` (8,640 rows).*

#### Step B: Train & Benchmark ML Models
```bash
python train_model.py
```
*Outputs: Trains Linear Regression, Random Forest, and XGBoost; benchmarks against Isolation Forest; saves artifacts to `models/`.*

#### Step C: Run Unit & Pipeline Tests
```bash
python -m pytest -v
```
*Executes all 9 automated test cases covering data generator, physics feature engineering, chronological splitting, regression metrics, and anomaly detection rules.*

#### Step D: Launch the Interactive Streamlit Dashboard
```bash
python -m streamlit run app.py
```
*Opens the web dashboard in your browser at `http://localhost:8501`.*

---

## 📁 8. Project Directory Structure

```
energy_waste_detective/
├── app.py                      # Interactive Streamlit dashboard application
├── generate_data.py            # Physics-based synthetic dataset generator
├── train_model.py              # ML model training, benchmarking, and evaluation
├── utils.py                    # Preprocessing, metrics, detection logic & costs
├── requirements.txt            # Dependency manifest
├── README.md                   # Complete documentation & viva defense guide
├── data/
│   └── energy_data.csv         # Generated 90-day hourly campus dataset
├── models/
│   ├── best_model.joblib       # Serialized champion XGBoost model pipeline
│   ├── isolation_forest.joblib # Trained Isolation Forest baseline artifact
│   ├── model_comparison.csv    # Benchmark table comparing regression models
│   └── model_metadata.json     # Feature list, test metrics, and default thresholds
└── tests/
    ├── __init__.py
    ├── test_data.py            # Unit tests for data generation and schema
    ├── test_model.py           # Unit tests for ML features and inference
    └── test_detection.py       # Unit tests for contextual waste logic
```

---

## 🎓 9. Viva Questions & Project Defense Guide

### Q1: Why did you use Regression + Residuals instead of direct Binary Classification?
> **Answer**: Real campus metering systems rarely have labeled "waste" datasets. Training a classifier on historical data is impractical because operational waste is unlabelled. By training a **regression model** on contextual variables (weather, schedule, occupancy), the model learns the **expected baseline physics** of the building. The difference between what the building actually consumes and what physics/occupancy predicts it should consume reveals operational waste.

### Q2: Why did Isolation Forest perform poorly compared to the Contextual Detector?
> **Answer**: Isolation Forest is an unsupervised density estimator. It isolates points that are rare in multidimensional space. For instance, a sudden power drop (breaker trip), an unusually cool morning, or a high-occupancy event are all statistically rare, so Isolation Forest flags them as anomalies. However, statistical rarity is **not** synonymous with electricity waste. Our Contextual Detector requires both an **excess positive residual** AND **zero/low occupancy**, yielding 93.2% precision compared to Isolation Forest's 1.3%.

### Q3: How did you prevent Data Leakage?
> **Answer**:
> 1. We used a strict **chronological train/test split** (training on Jan 1 – Mar 13, testing on Mar 14 – Mar 31) rather than a random shuffle split, preventing future time steps from leaking into the past.
> 2. Ground-truth evaluation labels (`is_anomaly`, `anomaly_type`) and the target variable (`actual_power_kw`) were strictly excluded from the feature matrix $X$.
> 3. Encoders and standardizers were fitted exclusively inside an Scikit-Learn `Pipeline` during training and never fitted on test data.

### Q4: How is financial waste calculated?
> **Answer**: Telemetry is measured at hourly intervals. If a room consumes 40 kW when the model expects 10 kW, the excess is 30 kW. Over 1 hour, that equals $30\text{ kW} \times 1\text{ h} = 30\text{ kWh}$. Multiplying by the institutional commercial tariff (default ₹8.50 per kWh) gives an estimated financial loss of ₹255.00 for that single hour.

### Q5: What are the main limitations of this system?
> **Answer**:
> 1. Telemetry is hourly; 15-minute sub-metering would capture short transient waste (e.g., lights left on during lunch breaks).
> 2. Occupancy in the dataset is simulated; in real deployments, it requires integration with IoT PIR sensors, Wi-Fi connected device counts, or turnstile logs.
> 3. Whole-building meters cannot differentiate whether excess power came from lighting or HVAC; circuit-level sub-metering would provide granular root-cause attribution.

---

## 📜 License
This project is open-source and available under the [MIT License](LICENSE).
