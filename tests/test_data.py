"""
Tests for dataset generation and validation.
"""

import os
import pandas as pd
import pytest
from generate_data import generate_campus_energy_dataset
from utils import validate_dataset_columns, REQUIRED_INPUT_COLUMNS


def test_generate_campus_energy_dataset():
    # Generate smaller 7-day dataset for rapid testing
    df = generate_campus_energy_dataset(days=7, random_state=42)
    
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 7 * 24 * 4  # 7 days * 24 hours * 4 buildings = 672
    
    # Check required columns
    for col in REQUIRED_INPUT_COLUMNS:
        assert col in df.columns, f"Missing required column: {col}"
    
    # Check evaluation labels exist
    assert "is_anomaly" in df.columns
    assert "anomaly_type" in df.columns
    
    # Check physical constraints
    assert (df["actual_power_kw"] > 0).all(), "Power must always be positive"
    assert (df["occupancy"] >= 0).all(), "Occupancy cannot be negative"
    assert (df["temperature"] >= 10.0).all() and (df["temperature"] <= 50.0).all()
    assert (df["humidity"] >= 20.0).all() and (df["humidity"] <= 100.0).all()
    
    # Check nulls
    assert df.isna().sum().sum() == 0, "Generated dataset should contain zero NaNs"


def test_validate_dataset_columns():
    valid_data = pd.DataFrame({
        "timestamp": ["2026-01-01 00:00:00"],
        "building": ["Block A"],
        "zone": ["Classroom"],
        "occupancy": [10],
        "temperature": [25.0],
        "humidity": [60.0],
        "actual_power_kw": [15.5],
    })
    is_valid, missing = validate_dataset_columns(valid_data)
    assert is_valid is True
    assert len(missing) == 0

    invalid_data = valid_data.drop(columns=["actual_power_kw"])
    is_valid_inv, missing_inv = validate_dataset_columns(invalid_data)
    assert is_valid_inv is False
    assert "actual_power_kw" in missing_inv
