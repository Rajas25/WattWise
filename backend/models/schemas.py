"""
Pydantic schemas (request / response models) for the WattWise API.
"""

from __future__ import annotations
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, field_validator


# ── Auth ──────────────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


# ── Users ─────────────────────────────────────────────────────────────────────
class UserCreate(BaseModel):
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)
    full_name: str = Field(..., min_length=2)
    role: str = Field(default="student")

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        if v not in ("student", "admin"):
            raise ValueError("role must be 'student' or 'admin'")
        return v


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    is_active: bool
    created_at: str


class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v not in ("student", "admin"):
            raise ValueError("role must be 'student' or 'admin'")
        return v


# ── Buildings ─────────────────────────────────────────────────────────────────
class BuildingOut(BaseModel):
    id: int
    name: str
    zone: str
    base_kw: float
    max_occupancy: int
    is_active: bool


# ── Energy Readings ───────────────────────────────────────────────────────────
class ReadingIn(BaseModel):
    meter_id: str = Field(..., min_length=1)
    building: str = Field(..., min_length=1)
    zone: str = Field(..., min_length=1)
    timestamp: str = Field(..., description="ISO-8601 UTC timestamp")
    actual_power_kw: float = Field(..., ge=0, le=2000)
    occupancy: int = Field(default=0, ge=0, le=1000)
    temperature: Optional[float] = Field(default=None, ge=-10, le=60)
    humidity: Optional[float] = Field(default=None, ge=0, le=100)
    data_source: str = Field(default="simulated")


class ReadingOut(BaseModel):
    id: int
    meter_id: str
    building: str
    zone: str
    timestamp: str
    actual_power_kw: float
    occupancy: int
    temperature: Optional[float]
    humidity: Optional[float]
    data_source: str
    created_at: str


# ── Anomalies / Waste ─────────────────────────────────────────────────────────
class AnomalyOut(BaseModel):
    id: int
    building: str
    zone: str
    timestamp: str
    actual_power_kw: float
    predicted_power_kw: float
    residual_kw: float
    occupancy: int
    is_waste: bool
    waste_severity: Optional[str]
    excess_kwh: float
    excess_cost_inr: float
    anomaly_type: Optional[str]
    is_acknowledged: bool


# ── Alerts ─────────────────────────────────────────────────────────────────────
class AlertOut(BaseModel):
    id: int
    building: str
    severity: str
    message: str
    is_read: bool
    created_at: str


# ── Dashboard ─────────────────────────────────────────────────────────────────
class KpiSummary(BaseModel):
    total_readings: int
    total_kwh: float
    avg_power_kw: float
    waste_incidents: int
    excess_kwh: float
    excess_cost_inr: float
    unread_alerts: int
    active_meters: int
    data_source_note: str = "Simulated campus telemetry"


class BuildingStats(BaseModel):
    building: str
    total_kwh: float
    waste_incidents: int
    excess_cost_inr: float
    latest_power_kw: Optional[float]


class HourlyPoint(BaseModel):
    hour: int
    avg_actual_kw: float
    avg_predicted_kw: Optional[float]


class DailyPoint(BaseModel):
    date: str
    avg_actual_kw: float
    avg_predicted_kw: Optional[float]
    waste_count: int


# ── ML ─────────────────────────────────────────────────────────────────────────
class PredictionRequest(BaseModel):
    building: str
    zone: str
    occupancy: int = Field(ge=0)
    temperature: float = Field(ge=-10, le=60)
    humidity: float = Field(ge=0, le=100)
    hour: int = Field(ge=0, le=23)
    day_of_week: int = Field(ge=0, le=6)
    is_weekend: int = Field(default=0, ge=0, le=1)


class PredictionResponse(BaseModel):
    model_config = {"protected_namespaces": ()}
    predicted_power_kw: float
    model_name: str
    note: str = "Prediction from trained XGBoost model"


# ── Admin ─────────────────────────────────────────────────────────────────────
class AdminDashboard(BaseModel):
    total_users: int
    total_buildings: int
    total_meters: int
    total_readings: int
    total_anomalies: int
    unacknowledged_anomalies: int
    unread_alerts: int
    total_waste_kwh: float
    total_waste_inr: float
    system_note: str
