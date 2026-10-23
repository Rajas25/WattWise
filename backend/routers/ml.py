"""
/api/ml — Prediction, anomaly analysis, and model info endpoints.
Integrates the existing WattWise ML utilities from utils.py.
"""

import sys
import os
from pathlib import Path
from typing import List, Optional

import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

# Make project root importable
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import settings
from backend.models.schemas import PredictionRequest, PredictionResponse
from backend.routers.deps import _db_gen, get_current_user
from backend.services.ml_service import (
    get_model_info,
    predict_power,
    run_analysis_on_db_readings,
)

router = APIRouter(prefix="/api/ml", tags=["ml"])


@router.get("/info")
def model_info(_=Depends(get_current_user)):
    """Returns the loaded model name, features, and benchmark metrics."""
    info = get_model_info()
    if info is None:
        raise HTTPException(
            status_code=503,
            detail="Model artifacts not found. Run `python train_model.py` first.",
        )
    return info


@router.post("/predict", response_model=PredictionResponse)
def predict(
    body: PredictionRequest,
    _=Depends(get_current_user),
):
    """Single-row prediction from the best trained model."""
    result = predict_power(body.model_dump())
    if result is None:
        raise HTTPException(
            status_code=503,
            detail="Model not available. Run `python train_model.py` first.",
        )
    return result


@router.post("/analyze")
def analyze_readings(
    building: Optional[str] = None,
    days: int = 7,
    db=Depends(_db_gen),
    _=Depends(get_current_user),
):
    """
    Runs the ML pipeline on recent stored readings and saves anomalies + alerts.
    Returns a summary of what was detected.
    """
    result = run_analysis_on_db_readings(db, building=building, days=days)
    return result
