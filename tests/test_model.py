"""
Tests for ML preprocessing, chronological splitting, and model inference.
"""

import os
import joblib
import numpy as np
import pandas as pd
import pytest
from utils import (
    preprocess_energy_data,
    chronological_train_test_split,
    compute_regression_metrics,
    CATEGORICAL_FEATURES,
    NUMERIC_FEATURES,
)


def test_preprocess_energy_data():
    sample_df = pd.DataFrame({
        "timestamp": ["2026-01-05 09:00:00", "2026-01-10 22:00:00"],  # Monday 9am, Saturday 10pm
        "building": ["Academic Block A", "Academic Block A"],
        "zone": ["Classrooms", "Classrooms"],
        "occupancy": [50, 0],
        "temperature": [28.0, 20.0],
        "humidity": [50.0, 70.0],
        "actual_power_kw": [35.0, 10.0],
    })
    
    processed = preprocess_energy_data(sample_df)
    
    assert "is_business_hours" in processed.columns
    assert "cooling_need" in processed.columns
    assert "hour_sin" in processed.columns
    assert "hour_cos" in processed.columns
    
    # Monday 9am is business hours (1)
    assert processed.loc[0, "is_business_hours"] == 1
    # Saturday 10pm is not business hours (0)
    assert processed.loc[1, "is_business_hours"] == 0
    
    # Cooling need: max(0, 28 - 24) = 4.0; max(0, 20 - 24) = 0.0
    assert processed.loc[0, "cooling_need"] == 4.0
    assert processed.loc[1, "cooling_need"] == 0.0


def test_chronological_split():
    dates = pd.date_range("2026-01-01", periods=100, freq="h")
    df = pd.DataFrame({
        "timestamp": dates,
        "value": np.arange(100),
    })
    
    train_df, test_df = chronological_train_test_split(df, test_ratio=0.20)
    
    assert len(train_df) == 80
    assert len(test_df) == 20
    # Ensure zero future data leakage
    assert train_df["timestamp"].max() < test_df["timestamp"].min()


def test_regression_metrics():
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([11.0, 19.0, 30.0, 42.0])
    
    metrics = compute_regression_metrics(y_true, y_pred)
    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "R2" in metrics
    assert metrics["MAE"] == 1.0
    assert metrics["R2"] > 0.95


def test_saved_model_inference():
    model_path = os.path.join(os.path.dirname(__file__), "..", "models", "best_model.joblib")
    if not os.path.exists(model_path):
        pytest.skip("Model artifact not yet generated.")
        
    model = joblib.load(model_path)
    sample_input = pd.DataFrame([{
        "building": "Academic Block A",
        "zone": "Lecture Halls & Classrooms",
        "occupancy": 30,
        "temperature": 27.5,
        "humidity": 55.0,
        "hour": 14,
        "day_of_week": 2,
        "is_weekend": 0,
        "is_business_hours": 1,
        "cooling_need": 3.5,
        "hour_sin": np.sin(2 * np.pi * 14 / 24.0),
        "hour_cos": np.cos(2 * np.pi * 14 / 24.0),
    }])
    
    pred = model.predict(sample_input)
    assert len(pred) == 1
    assert pred[0] > 0.0
