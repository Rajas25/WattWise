"""
WattWise ML Service
====================
Integrates the existing trained models (best_model.joblib) and utils.py functions.
This module loads the model once at startup and reuses it for all predictions.

IMPORTANT DISTINCTION (documented for viva/presentation):
- "Anomaly"    — A statistical deviation detected by the model (could be legitimate).
- "Waste event"— An anomaly where residual >= threshold AND occupancy <= limit.
                 This is *potential* waste, not confirmed waste without physical inspection.
- "Confirmed waste" — Would require a facilities engineer to verify the cause on-site.
"""

import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

# Project root on path
_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_ROOT))

from backend.config import settings

# Lazy-loaded model + metadata (loaded once on first call)
_model = None
_metadata = None


def _load_model():
    global _model, _metadata
    if _model is not None:
        return True
    try:
        import joblib
        if not Path(settings.BEST_MODEL_PATH).exists():
            return False
        _model = joblib.load(settings.BEST_MODEL_PATH)
        with open(settings.METADATA_PATH) as f:
            _metadata = json.load(f)
        print(f"[ML] Model loaded: {_metadata.get('best_model_name','unknown')}")
        return True
    except Exception as e:
        print(f"[ML] WARNING: Could not load model: {e}")
        return False


def get_model_info() -> Optional[Dict]:
    if not _load_model():
        return None
    return {
        "model_name": _metadata.get("best_model_name"),
        "features": _metadata.get("feature_columns"),
        "train_samples": _metadata.get("train_samples"),
        "test_samples": _metadata.get("test_samples"),
        "regression_metrics": _metadata.get("regression_metrics"),
        "waste_detection_metrics": _metadata.get("waste_detection_metrics"),
        "default_thresholds": _metadata.get("default_thresholds"),
    }


def predict_power(features: Dict[str, Any]) -> Optional[Dict]:
    """
    Single-row power prediction.
    features must include: building, zone, occupancy, temperature, humidity,
                           hour, day_of_week, is_weekend
    Returns: {predicted_power_kw, model_name}
    """
    if not _load_model():
        return None
    try:
        from utils import preprocess_energy_data, CATEGORICAL_FEATURES, NUMERIC_FEATURES

        row = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "building": features.get("building", "Academic Block A"),
            "zone": features.get("zone", "Lecture Halls & Classrooms"),
            "occupancy": int(features.get("occupancy", 0)),
            "temperature": float(features.get("temperature", 25.0)),
            "humidity": float(features.get("humidity", 60.0)),
            "actual_power_kw": 0.0,  # placeholder for preprocess
        }
        df = pd.DataFrame([row])
        df = preprocess_energy_data(df)

        feature_cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
        X = df[feature_cols]
        pred = float(_model.predict(X)[0])
        return {
            "predicted_power_kw": round(max(0.0, pred), 2),
            "model_name": _metadata.get("best_model_name", "XGBoost"),
            "note": "Prediction from trained WattWise model",
        }
    except Exception as e:
        print(f"[ML] Prediction error: {e}")
        return None


def run_analysis_on_db_readings(
    db: sqlite3.Connection,
    building: Optional[str] = None,
    days: int = 7,
) -> Dict[str, Any]:
    """
    Loads recent readings from SQLite, runs the ML regression baseline,
    applies contextual waste detection, saves results to anomalies and alerts tables.
    Returns a summary dict.
    """
    if not _load_model():
        return {"error": "Model not loaded. Run python train_model.py first.", "analyzed": 0}

    try:
        from utils import (
            preprocess_energy_data,
            detect_contextual_waste,
            CATEGORICAL_FEATURES,
            NUMERIC_FEATURES,
        )
    except ImportError as e:
        return {"error": f"Cannot import utils.py: {e}", "analyzed": 0}

    # Load readings
    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    params = [since]
    where = "WHERE timestamp >= ?"
    if building and building != "All Buildings":
        where += " AND building = ?"
        params.append(building)

    rows = db.execute(
        f"SELECT * FROM energy_readings {where} ORDER BY timestamp",
        params,
    ).fetchall()

    if not rows:
        return {"analyzed": 0, "waste_events": 0, "message": "No readings found for the given period."}

    # Build DataFrame
    df = pd.DataFrame([dict(r) for r in rows])
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])

    # Preprocess
    df_proc = preprocess_energy_data(df)

    feature_cols = CATEGORICAL_FEATURES + NUMERIC_FEATURES
    # Only keep rows where all features present
    missing = [c for c in feature_cols if c not in df_proc.columns]
    if missing:
        return {"error": f"Missing features after preprocessing: {missing}", "analyzed": 0}

    X = df_proc[feature_cols]
    predicted_kw = _model.predict(X)

    # Waste detection
    waste_df = detect_contextual_waste(
        df_proc,
        predicted_kw=predicted_kw,
        residual_threshold_kw=settings.RESIDUAL_THRESHOLD_KW,
        occupancy_threshold=settings.OCCUPANCY_THRESHOLD,
        tariff_inr=settings.TARIFF_INR_PER_KWH,
    )

    # Save anomalies (waste events only — clear for viva: these are potential waste, not confirmed)
    saved = 0
    alerts_created = 0
    ts_now = datetime.now(timezone.utc).isoformat()

    for _, row in waste_df[waste_df["residual_kw"] > 0].iterrows():
        is_waste = int(row.get("is_waste_detected", 0))
        ts_str = row["timestamp"].isoformat() if hasattr(row["timestamp"], "isoformat") else str(row["timestamp"])
        reading_id = df.iloc[row.name]["id"] if "id" in df.columns else None

        try:
            cur = db.execute(
                """
                INSERT OR IGNORE INTO anomalies
                    (reading_id, building, zone, timestamp, actual_power_kw,
                     predicted_power_kw, residual_kw, occupancy, is_waste,
                     waste_severity, excess_kwh, excess_cost_inr, anomaly_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    reading_id,
                    str(row.get("building", "")),
                    str(row.get("zone", "")),
                    ts_str,
                    float(row.get("actual_power_kw", 0)),
                    float(row.get("predicted_power_kw", 0)),
                    float(row.get("residual_kw", 0)),
                    int(row.get("occupancy", 0)),
                    is_waste,
                    str(row.get("waste_severity", "Normal")),
                    float(row.get("excess_kwh", 0)),
                    float(row.get("excess_cost_inr", 0)),
                    "ML Contextual Detection",
                ),
            )
            if cur.lastrowid and is_waste:
                saved += 1
                severity_map = {
                    "High Waste (Severe)": "High",
                    "Medium Waste": "Medium",
                    "Low Waste": "Low",
                }
                sev = severity_map.get(str(row.get("waste_severity", "")), "Low")
                msg = (
                    f"Potential waste in {row.get('building')} — "
                    f"+{row.get('residual_kw', 0):.1f} kW above baseline, "
                    f"occupancy={row.get('occupancy', 0)}, "
                    f"est. ₹{row.get('excess_cost_inr', 0):.2f}"
                )
                db.execute(
                    "INSERT INTO alerts (anomaly_id, building, severity, message) VALUES (?, ?, ?, ?)",
                    (cur.lastrowid, str(row.get("building", "")), sev, msg),
                )
                alerts_created += 1
        except Exception as ex:
            pass  # Duplicate or constraint violation — skip silently

    db.commit()

    total_waste_cost = float(waste_df["excess_cost_inr"].sum())
    return {
        "analyzed": len(waste_df),
        "waste_events": int(waste_df["is_waste_detected"].sum()),
        "new_anomalies_saved": saved,
        "new_alerts_created": alerts_created,
        "total_excess_kwh": round(float(waste_df["excess_kwh"].sum()), 2),
        "total_excess_cost_inr": round(total_waste_cost, 2),
        "model": _metadata.get("best_model_name"),
        "note": (
            "These are *potential* waste events detected by the ML model. "
            "Physical confirmation requires on-site inspection."
        ),
    }
