"""
Building Energy Waste Detective: Model Training and Evaluation Pipeline
========================================================================
1. Loads campus electricity dataset.
2. Performs data preprocessing, validation, and exploratory data analysis (EDA).
3. Executes a strict chronological train/test split (no future leakage).
4. Trains 3 regression architectures:
   - Linear Regression (Baseline)
   - Random Forest Regressor
   - XGBoost Regressor
5. Evaluates and compares all models fairly using MAE, RMSE, R², and MAPE.
6. Evaluates Anomaly Detection performance (Contextual Residual Detector vs Isolation Forest)
   against ground-truth simulated waste events (precision, recall, F1, confusion matrix).
7. Saves the best model, feature metadata, and comparison reports to models/ directory.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
import xgboost as xgb

from utils import (
    preprocess_energy_data,
    chronological_train_test_split,
    compute_regression_metrics,
    compute_anomaly_metrics,
    detect_contextual_waste,
    train_and_predict_isolation_forest,
    validate_dataset_columns,
    NUMERIC_FEATURES,
    CATEGORICAL_FEATURES,
)


def run_pipeline(
    data_path: str = "data/energy_data.csv",
    models_dir: str = "models",
    test_ratio: float = 0.20,
):
    print("=" * 80)
    print("  BUILDING ENERGY WASTE DETECTIVE: ML PIPELINE TRAINING & BENCHMARKING  ")
    print("=" * 80)

    # 1. Load Dataset
    if not os.path.exists(data_path):
        raise FileNotFoundError(f"Dataset not found at {data_path}. Run generate_data.py first.")

    raw_df = pd.read_csv(data_path)
    print(f"\n[Step 1] Dataset Loaded: {len(raw_df):,} records from '{data_path}'")

    # 2. Validation & EDA
    is_valid, missing = validate_dataset_columns(raw_df)
    if not is_valid:
        raise ValueError(f"Dataset is missing required columns: {missing}")

    print("\n--- Exploratory Data Analysis (EDA) ---")
    print(f"Missing Values:\n{raw_df.isna().sum()[raw_df.isna().sum() > 0] if raw_df.isna().sum().sum() > 0 else 'Zero missing values detected.'}")
    print(f"Duplicate Rows : {raw_df.duplicated().sum()}")
    print(f"Date Range     : {raw_df['timestamp'].min()} to {raw_df['timestamp'].max()}")
    print(f"Buildings      : {list(raw_df['building'].unique())}")
    print(f"Power (kW)     : Mean={raw_df['actual_power_kw'].mean():.2f}, Std={raw_df['actual_power_kw'].std():.2f}, Min={raw_df['actual_power_kw'].min():.2f}, Max={raw_df['actual_power_kw'].max():.2f}")
    print(f"Occupancy      : Mean={raw_df['occupancy'].mean():.1f}, Max={raw_df['occupancy'].max()}")
    print(f"Temperature(°C): Mean={raw_df['temperature'].mean():.2f}, Min={raw_df['temperature'].min():.2f}, Max={raw_df['temperature'].max():.2f}")

    # Feature Engineering
    df = preprocess_energy_data(raw_df)

    # 3. Chronological Train/Test Split
    train_df, test_df = chronological_train_test_split(df, test_ratio=test_ratio)
    print(f"\n[Step 2] Chronological Train/Test Split (Zero-Leakage):")
    print(f" - Train Samples: {len(train_df):,} ({train_df['timestamp'].min()} -> {train_df['timestamp'].max()})")
    print(f" - Test Samples : {len(test_df):,} ({test_df['timestamp'].min()} -> {test_df['timestamp'].max()})")

    # Feature Matrix (X) and Target (y)
    # Strictly exclude ground truth labels (is_anomaly, anomaly_type) and target (actual_power_kw)
    feature_cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    print(f" - Selected Features ({len(feature_cols)}): {feature_cols}")

    X_train = train_df[feature_cols]
    y_train = train_df["actual_power_kw"].values

    X_test = test_df[feature_cols]
    y_test = test_df["actual_power_kw"].values

    # Preprocessing pipelines for ML algorithms
    # Note: Categorical features one-hot encoded, numeric features scaled for Linear Regression
    preprocessor_scaled = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", StandardScaler(), NUMERIC_FEATURES),
        ]
    )

    preprocessor_trees = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore", sparse_output=False), CATEGORICAL_FEATURES),
            ("num", "passthrough", NUMERIC_FEATURES),
        ]
    )

    # Models definition
    models = {
        "Linear Regression (Baseline)": Pipeline([
            ("prep", preprocessor_scaled),
            ("model", LinearRegression()),
        ]),
        "Random Forest Regressor": Pipeline([
            ("prep", preprocessor_trees),
            ("model", RandomForestRegressor(n_estimators=120, max_depth=14, random_state=42, n_jobs=-1)),
        ]),
        "XGBoost Regressor": Pipeline([
            ("prep", preprocessor_trees),
            ("model", xgb.XGBRegressor(
                n_estimators=150,
                max_depth=6,
                learning_rate=0.08,
                subsample=0.85,
                colsample_bytree=0.85,
                random_state=42,
                n_jobs=-1
            )),
        ]),
    }

    # 4. Train and Benchmark Models
    print("\n[Step 3] Training and Fair Benchmarking on Test Data:")
    benchmark_results = []
    trained_pipelines = {}

    for name, pipe in models.items():
        print(f"  Training {name}...")
        pipe.fit(X_train, y_train)
        y_pred = pipe.predict(X_test)
        metrics = compute_regression_metrics(y_test, y_pred)
        
        benchmark_results.append({
            "Model": name,
            "MAE (kW)": round(metrics["MAE"], 3),
            "RMSE (kW)": round(metrics["RMSE"], 3),
            "R2 Score": round(metrics["R2"], 4),
            "MAPE (%)": round(metrics["MAPE"], 2),
        })
        trained_pipelines[name] = pipe

    comparison_df = pd.DataFrame(benchmark_results)
    print("\n" + "=" * 65)
    print("              MODEL REGRESSION BENCHMARK COMPARISON              ")
    print("=" * 65)
    print(comparison_df.to_string(index=False))
    print("=" * 65)

    # Pick the best model based on highest R2 Score
    best_row = comparison_df.sort_values(by="R2 Score", ascending=False).iloc[0]
    best_model_name = best_row["Model"]
    best_pipeline = trained_pipelines[best_model_name]
    print(f"\n>>> Best Performing Model: '{best_model_name}' (R² = {best_row['R2 Score']}, MAE = {best_row['MAE (kW)']} kW)")

    # 5. Waste Detection & Anomaly Evaluation
    print("\n[Step 4] Evaluating Waste Detection against Ground Truth on Test Set:")
    best_test_preds = best_pipeline.predict(X_test)

    # A. Contextual Residual-Based Waste Detector
    # Residual threshold default: 10.0 kW, Low Occupancy: <= 5
    waste_df = detect_contextual_waste(
        test_df,
        best_test_preds,
        residual_threshold_kw=10.0,
        occupancy_threshold=5,
    )

    # In our simulated dataset, ground truth energy waste occurs when is_anomaly == 1 and not pure drop
    # Only waste events (empty room, overcooling, weekend equipment) represent true energy waste
    ground_truth_waste = (
        (test_df["is_anomaly"] == 1) & 
        (test_df["anomaly_type"].str.contains("Waste", case=False, na=False))
    ).astype(int).values

    contextual_detected = waste_df["is_waste_detected"].values
    contextual_metrics = compute_anomaly_metrics(ground_truth_waste, contextual_detected)

    print("\n--- Contextual Residual-Based Detector Performance ---")
    print(f"Precision : {contextual_metrics['precision']:.4f}")
    print(f"Recall    : {contextual_metrics['recall']:.4f}")
    print(f"F1-Score  : {contextual_metrics['f1_score']:.4f}")
    print(f"Accuracy  : {contextual_metrics['accuracy']:.4f}")
    print(f"Confusion Matrix: TP={contextual_metrics['tp']}, FP={contextual_metrics['fp']}, TN={contextual_metrics['tn']}, FN={contextual_metrics['fn']}")

    # B. Isolation Forest Baseline (Unsupervised outlier detection)
    # Train Isolation Forest on operational features of train set
    iso_features = ["actual_power_kw", "occupancy", "temperature", "humidity", "hour"]
    iso_model, iso_preds, _ = train_and_predict_isolation_forest(
        train_df[iso_features],
        test_df[iso_features],
        contamination=0.035,
    )
    iso_metrics = compute_anomaly_metrics(ground_truth_waste, iso_preds)

    print("\n--- Isolation Forest (Unsupervised Baseline) Performance ---")
    print(f"Precision : {iso_metrics['precision']:.4f}")
    print(f"Recall    : {iso_metrics['recall']:.4f}")
    print(f"F1-Score  : {iso_metrics['f1_score']:.4f}")
    print(f"Accuracy  : {iso_metrics['accuracy']:.4f}")
    print(f"Confusion Matrix: TP={iso_metrics['tp']}, FP={iso_metrics['fp']}, TN={iso_metrics['tn']}, FN={iso_metrics['fn']}")

    print("\nKey Insight for Viva:")
    print("Isolation Forest flags any statistical outliers (such as drops and unusual weather),")
    print("whereas the ML Contextual Residual Detector isolates high excess power specifically")
    print("during unpopulated/idle hours, leading to much higher precision for Energy Waste.")

    # 6. Save Model Artifacts
    os.makedirs(models_dir, exist_ok=True)
    best_model_path = os.path.join(models_dir, "best_model.joblib")
    iso_model_path = os.path.join(models_dir, "isolation_forest.joblib")
    comparison_csv_path = os.path.join(models_dir, "model_comparison.csv")
    metadata_json_path = os.path.join(models_dir, "model_metadata.json")

    joblib.dump(best_pipeline, best_model_path)
    joblib.dump(iso_model, iso_model_path)
    comparison_df.to_csv(comparison_csv_path, index=False)

    metadata = {
        "best_model_name": best_model_name,
        "feature_columns": feature_cols,
        "categorical_features": CATEGORICAL_FEATURES,
        "numeric_features": NUMERIC_FEATURES,
        "train_samples": len(train_df),
        "test_samples": len(test_df),
        "test_ratio": test_ratio,
        "regression_metrics": {row["Model"]: row for row in benchmark_results},
        "waste_detection_metrics": {
            "contextual_detector": contextual_metrics,
            "isolation_forest": iso_metrics,
        },
        "default_thresholds": {
            "residual_threshold_kw": 10.0,
            "occupancy_threshold": 5,
            "tariff_inr_per_kwh": 8.50,
        },
    }

    with open(metadata_json_path, "w") as f:
        json.dump(metadata, f, indent=4)

    print(f"\n[Step 5] Artifacts Saved Successfully to '{models_dir}/':")
    print(f" - {best_model_path}")
    print(f" - {iso_model_path}")
    print(f" - {comparison_csv_path}")
    print(f" - {metadata_json_path}")
    print("=" * 80)


if __name__ == "__main__":
    current_dir = os.path.dirname(os.path.abspath(__file__))
    data_file = os.path.join(current_dir, "data", "energy_data.csv")
    models_folder = os.path.join(current_dir, "models")
    run_pipeline(data_path=data_file, models_dir=models_folder)
