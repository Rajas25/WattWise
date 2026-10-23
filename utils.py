"""
Utility functions for Building Energy Waste Detective.
======================================================
Contains modules for:
1. Data cleaning, validation, and feature engineering.
2. Chronological train/test splitting (zero leakage).
3. Regression and anomaly detection evaluation metrics.
4. Contextual residual-based energy waste detection.
5. Unsupervised Isolation Forest anomaly detection.
6. Financial and energy waste estimation in INR (₹) and kWh.
"""

from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import pandas as pd
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score, confusion_matrix
from sklearn.ensemble import IsolationForest


# Standard commercial tariff in INR per kWh for Indian institutional/campus power
DEFAULT_TARIFF_INR_PER_KWH = 8.50

# Core required columns for pipeline
REQUIRED_INPUT_COLUMNS = [
    "timestamp",
    "building",
    "zone",
    "occupancy",
    "temperature",
    "humidity",
    "actual_power_kw",
]

# Numerical feature columns used for regression modeling
NUMERIC_FEATURES = [
    "occupancy",
    "temperature",
    "humidity",
    "hour",
    "day_of_week",
    "is_weekend",
    "is_business_hours",
    "cooling_need",
    "hour_sin",
    "hour_cos",
]

# Categorical columns to encode
CATEGORICAL_FEATURES = ["building", "zone"]


def validate_dataset_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """
    Validates that a dataframe contains all required columns for ML prediction
    and anomaly detection.
    
    Returns:
    --------
    (is_valid, missing_columns)
    """
    missing = [col for col in REQUIRED_INPUT_COLUMNS if col not in df.columns]
    return (len(missing) == 0, missing)


def preprocess_energy_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Performs data cleaning, datetime parsing, and physics-informed feature engineering.
    
    Features engineered:
    - is_business_hours: Weekdays 8:00 AM to 6:00 PM
    - cooling_need: Positive difference between temperature and baseline comfort (24°C)
    - hour_sin, hour_cos: Cyclical periodic transformation of 24h clock
    """
    data = df.copy()

    # 1. Datetime conversion
    if not pd.api.types.is_datetime64_any_dtype(data["timestamp"]):
        data["timestamp"] = pd.to_datetime(data["timestamp"])

    # 2. Basic cleaning: drop pure duplicates
    data = data.drop_duplicates(subset=["timestamp", "building", "zone"]).reset_index(drop=True)

    # 3. Ensure time components exist
    if "hour" not in data.columns:
        data["hour"] = data["timestamp"].dt.hour
    if "day_of_week" not in data.columns:
        data["day_of_week"] = data["timestamp"].dt.dayofweek
    if "is_weekend" not in data.columns:
        data["is_weekend"] = data["day_of_week"].apply(lambda d: 1 if d in [5, 6] else 0)

    # 4. Domain & Physics-based features
    # Academic/business core hours: Monday-Friday (day_of_week 0-4), 08:00 to 18:00
    data["is_business_hours"] = (
        (data["day_of_week"] < 5) & (data["hour"] >= 8) & (data["hour"] <= 18)
    ).astype(int)

    # Cooling degree demand (AC threshold typically 24°C in Indian standard guidelines)
    data["cooling_need"] = np.maximum(0.0, data["temperature"] - 24.0)

    # Cyclical hour features (ensures 23:00 and 00:00 are recognized as adjacent)
    data["hour_sin"] = np.sin(2 * np.pi * data["hour"] / 24.0)
    data["hour_cos"] = np.cos(2 * np.pi * data["hour"] / 24.0)

    return data


def chronological_train_test_split(
    df: pd.DataFrame, test_ratio: float = 0.20
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Strict chronological train/test split.
    Prevents future-data leakage by training solely on historical records and
    evaluating on subsequent time periods.
    """
    sorted_df = df.sort_values(by="timestamp").reset_index(drop=True)
    split_idx = int(len(sorted_df) * (1.0 - test_ratio))
    train_df = sorted_df.iloc[:split_idx].copy().reset_index(drop=True)
    test_df = sorted_df.iloc[split_idx:].copy().reset_index(drop=True)
    return train_df, test_df


def compute_regression_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes standard regression evaluation metrics:
    - MAE: Mean Absolute Error (kW)
    - RMSE: Root Mean Squared Error (kW)
    - R²: Coefficient of Determination (explained variance)
    - MAPE: Mean Absolute Percentage Error (%)
    """
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    r2 = r2_score(y_true, y_pred)
    
    # Avoid zero division in MAPE
    non_zero = y_true > 0.1
    if np.sum(non_zero) > 0:
        mape = float(np.mean(np.abs((y_true[non_zero] - y_pred[non_zero]) / y_true[non_zero])) * 100.0)
    else:
        mape = 0.0

    return {
        "MAE": float(mae),
        "RMSE": float(rmse),
        "R2": float(r2),
        "MAPE": float(mape),
    }


def compute_anomaly_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> Dict[str, Any]:
    """
    Computes classification metrics for binary anomaly detection:
    Precision, Recall, F1-Score, Accuracy, and Confusion Matrix.
    """
    prec = precision_score(y_true, y_pred, zero_division=0)
    rec = recall_score(y_true, y_pred, zero_division=0)
    f1 = f1_score(y_true, y_pred, zero_division=0)
    acc = accuracy_score(y_true, y_pred)
    cm = confusion_matrix(y_true, y_pred)

    tn, fp, fn, tp = (cm[0, 0], cm[0, 1], cm[1, 0], cm[1, 1]) if cm.shape == (2, 2) else (0, 0, 0, 0)

    return {
        "precision": float(prec),
        "recall": float(rec),
        "f1_score": float(f1),
        "accuracy": float(acc),
        "confusion_matrix": cm.tolist(),
        "tp": int(tp),
        "fp": int(fp),
        "tn": int(tn),
        "fn": int(fn),
    }


def detect_contextual_waste(
    df: pd.DataFrame,
    predicted_kw: np.ndarray,
    residual_threshold_kw: float = 10.0,
    occupancy_threshold: int = 5,
    tariff_inr: float = DEFAULT_TARIFF_INR_PER_KWH,
) -> pd.DataFrame:
    """
    ML-Driven Contextual Energy Waste Detector:
    1. Computes the regression residual: (actual_power_kw - predicted_power_kw).
    2. Flags an anomaly as True Energy Waste IF AND ONLY IF:
       - Actual consumption significantly exceeds the model's expected baseline
         (residual >= residual_threshold_kw)
       - AND the zone is currently unoccupied or very low occupancy
         (occupancy <= occupancy_threshold).
    3. Calculates wasted energy in kWh and estimated financial cost in INR (₹).
    4. Categorizes severity:
       - Normal: residual < threshold or occupied
       - Low: threshold <= residual < 1.5 * threshold
       - Medium: 1.5 * threshold <= residual < 2.5 * threshold
       - High: residual >= 2.5 * threshold
    """
    res_df = df.copy()
    res_df["predicted_power_kw"] = np.round(predicted_kw, 2)
    res_df["residual_kw"] = np.round(res_df["actual_power_kw"] - res_df["predicted_power_kw"], 2)

    # Condition for genuine energy waste:
    # High power consumption when space is empty or barely used
    is_waste = (
        (res_df["residual_kw"] >= residual_threshold_kw)
        & (res_df["occupancy"] <= occupancy_threshold)
    )

    res_df["is_waste_detected"] = is_waste.astype(int)

    # Calculate severity
    def assign_severity(row):
        if not row["is_waste_detected"]:
            return "Normal"
        r = row["residual_kw"]
        if r < 1.5 * residual_threshold_kw:
            return "Low Waste"
        elif r < 2.5 * residual_threshold_kw:
            return "Medium Waste"
        else:
            return "High Waste (Severe)"

    res_df["waste_severity"] = res_df.apply(assign_severity, axis=1)

    # Excess energy calculation (Hourly telemetry means 1 hour interval -> kWh = kW * 1h)
    res_df["excess_kwh"] = np.where(res_df["is_waste_detected"] == 1, res_df["residual_kw"], 0.0)
    res_df["excess_cost_inr"] = np.round(res_df["excess_kwh"] * tariff_inr, 2)

    return res_df


def train_and_predict_isolation_forest(
    X_train: pd.DataFrame,
    X_test: pd.DataFrame,
    contamination: float = 0.03,
    random_state: int = 42,
) -> Tuple[IsolationForest, np.ndarray, np.ndarray]:
    """
    Trains an Isolation Forest unsupervised model as an outlier baseline.
    
    Returns:
    --------
    (model, binary_predictions, anomaly_scores)
    binary_predictions: 1 for anomaly, 0 for normal.
    """
    iso = IsolationForest(
        contamination=contamination,
        random_state=random_state,
        n_estimators=100,
    )
    iso.fit(X_train)

    # Isolation forest outputs -1 for anomaly, 1 for inlier
    raw_preds = iso.predict(X_test)
    binary_preds = np.where(raw_preds == -1, 1, 0)
    scores = iso.decision_function(X_test)

    return iso, binary_preds, scores
