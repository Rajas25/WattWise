"""
Tests for Contextual Energy Waste Detection and Evaluation.
"""

import numpy as np
import pandas as pd
import pytest
from utils import (
    detect_contextual_waste,
    compute_anomaly_metrics,
    train_and_predict_isolation_forest,
)


def test_detect_contextual_waste_logic():
    # Construct synthetic scenarios
    # Row 0: High power, zero occupancy -> SHOULD BE FLAGGED AS ENERGY WASTE
    # Row 1: High power, high occupancy (100 students) -> JUSTIFIED LOAD, NOT WASTE
    # Row 2: Normal power, zero occupancy -> NORMAL, NOT WASTE
    # Row 3: Slight deviation (5 kW) < threshold (10 kW) -> NOT WASTE
    test_data = pd.DataFrame({
        "timestamp": pd.date_range("2026-01-01", periods=4, freq="h"),
        "building": ["Academic Block A"] * 4,
        "zone": ["Classroom"] * 4,
        "occupancy": [0, 80, 0, 0],
        "actual_power_kw": [45.0, 50.0, 12.0, 15.0],
    })
    
    # Model predictions
    predicted_kw = np.array([15.0, 48.0, 12.0, 10.0])
    
    result = detect_contextual_waste(
        test_data,
        predicted_kw=predicted_kw,
        residual_threshold_kw=10.0,
        occupancy_threshold=5,
        tariff_inr=8.50,
    )
    
    assert "is_waste_detected" in result.columns
    assert "residual_kw" in result.columns
    assert "waste_severity" in result.columns
    assert "excess_cost_inr" in result.columns
    
    # Check Row 0: Residual = 30 kW >= 10 kW, occ = 0 <= 5 -> Flagged!
    assert result.loc[0, "is_waste_detected"] == 1
    assert result.loc[0, "residual_kw"] == 30.0
    assert result.loc[0, "waste_severity"] == "High Waste (Severe)"
    assert result.loc[0, "excess_cost_inr"] == round(30.0 * 8.50, 2)
    
    # Check Row 1: Residual = 2 kW < 10 kW, occ = 80 > 5 -> Not flagged!
    assert result.loc[1, "is_waste_detected"] == 0
    
    # Check Row 2: Residual = 0 kW < 10 kW -> Not flagged!
    assert result.loc[2, "is_waste_detected"] == 0
    
    # Check Row 3: Residual = 5 kW < 10 kW -> Not flagged!
    assert result.loc[3, "is_waste_detected"] == 0


def test_compute_anomaly_metrics():
    y_true = np.array([1, 1, 0, 0])
    y_pred = np.array([1, 0, 0, 1])
    # TP=1, FN=1, TN=1, FP=1
    metrics = compute_anomaly_metrics(y_true, y_pred)
    assert metrics["tp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tn"] == 1
    assert metrics["fp"] == 1
    assert metrics["accuracy"] == 0.5


def test_isolation_forest_execution():
    X_train = pd.DataFrame({
        "actual_power_kw": np.random.normal(25, 5, 200),
        "occupancy": np.random.randint(0, 50, 200),
        "temperature": np.random.normal(26, 3, 200),
        "humidity": np.random.normal(60, 10, 200),
        "hour": np.random.randint(0, 24, 200),
    })
    X_test = X_train.iloc[:50].copy()
    
    model, preds, scores = train_and_predict_isolation_forest(X_train, X_test, contamination=0.05)
    assert len(preds) == 50
    assert set(preds).issubset({0, 1})
