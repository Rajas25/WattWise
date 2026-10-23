"""
/api/energy — Energy readings, buildings, meters, dashboard, alerts
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend.config import settings
from backend.models.schemas import (
    AlertOut, AnomalyOut, BuildingOut, BuildingStats,
    DailyPoint, HourlyPoint, KpiSummary, ReadingIn, ReadingOut,
)
from backend.routers.deps import _db_gen, get_current_user, require_admin

router = APIRouter(prefix="/api/energy", tags=["energy"])


# ── Buildings ─────────────────────────────────────────────────────────────────
@router.get("/buildings", response_model=List[BuildingOut])
def list_buildings(
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    rows = db.execute("SELECT * FROM buildings WHERE is_active = 1").fetchall()
    return [dict(r) for r in rows]


# ── Dashboard KPI summary ─────────────────────────────────────────────────────
@router.get("/dashboard", response_model=KpiSummary)
def dashboard_summary(
    building: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    since = _days_ago_iso(days)
    params: list = [since]
    where = "WHERE er.timestamp >= ?"
    if building and building != "All Buildings":
        where += " AND er.building = ?"
        params.append(building)

    stats = db.execute(
        f"""
        SELECT
            COUNT(*)                    AS total_readings,
            COALESCE(SUM(actual_power_kw), 0) AS total_kwh,
            COALESCE(AVG(actual_power_kw), 0) AS avg_power_kw
        FROM energy_readings er
        {where}
        """,
        params,
    ).fetchone()

    waste = db.execute(
        f"""
        SELECT
            COUNT(*)                     AS waste_incidents,
            COALESCE(SUM(excess_kwh), 0) AS excess_kwh,
            COALESCE(SUM(excess_cost_inr), 0) AS excess_cost_inr
        FROM anomalies a
        WHERE a.is_waste = 1 AND a.timestamp >= ?
        {"AND a.building = ?" if (building and building != 'All Buildings') else ""}
        """,
        [since] + ([building] if building and building != "All Buildings" else []),
    ).fetchone()

    alerts_count = db.execute(
        "SELECT COUNT(*) as c FROM alerts WHERE is_read = 0"
    ).fetchone()["c"]

    meters_count = db.execute(
        "SELECT COUNT(*) as c FROM meters WHERE is_active = 1"
    ).fetchone()["c"]

    return KpiSummary(
        total_readings=stats["total_readings"],
        total_kwh=round(stats["total_kwh"], 2),
        avg_power_kw=round(stats["avg_power_kw"], 2),
        waste_incidents=waste["waste_incidents"],
        excess_kwh=round(waste["excess_kwh"], 2),
        excess_cost_inr=round(waste["excess_cost_inr"], 2),
        unread_alerts=alerts_count,
        active_meters=meters_count,
        data_source_note="Simulated campus telemetry (WattWise Demo)",
    )


# ── Building-level stats ──────────────────────────────────────────────────────
@router.get("/buildings/stats", response_model=List[BuildingStats])
def building_stats(
    days: int = Query(30, ge=1, le=365),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    since = _days_ago_iso(days)
    rows = db.execute(
        """
        SELECT
            er.building,
            COALESCE(SUM(er.actual_power_kw), 0) AS total_kwh,
            COALESCE(COUNT(a.id), 0)              AS waste_incidents,
            COALESCE(SUM(a.excess_cost_inr), 0)  AS excess_cost_inr,
            (SELECT actual_power_kw
               FROM energy_readings sub
              WHERE sub.building = er.building
              ORDER BY sub.timestamp DESC LIMIT 1) AS latest_power_kw
        FROM energy_readings er
        LEFT JOIN anomalies a ON a.building = er.building
            AND a.is_waste = 1 AND a.timestamp >= ?
        WHERE er.timestamp >= ?
        GROUP BY er.building
        ORDER BY total_kwh DESC
        """,
        (since, since),
    ).fetchall()
    return [dict(r) for r in rows]


# ── Hourly profile ────────────────────────────────────────────────────────────
@router.get("/hourly-profile", response_model=List[HourlyPoint])
def hourly_profile(
    building: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    since = _days_ago_iso(days)
    params: list = [since]
    where = "WHERE timestamp >= ?"
    if building and building != "All Buildings":
        where += " AND building = ?"
        params.append(building)

    rows = db.execute(
        f"""
        SELECT hour,
               AVG(actual_power_kw) AS avg_actual_kw
        FROM energy_readings
        {where}
        GROUP BY hour
        ORDER BY hour
        """,
        params,
    ).fetchall()
    return [{"hour": r["hour"], "avg_actual_kw": round(r["avg_actual_kw"], 2), "avg_predicted_kw": None} for r in rows]


# ── Daily trend ───────────────────────────────────────────────────────────────
@router.get("/daily-trend", response_model=List[DailyPoint])
def daily_trend(
    building: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    since = _days_ago_iso(days)
    params: list = [since]
    where = "WHERE er.timestamp >= ?"
    if building and building != "All Buildings":
        where += " AND er.building = ?"
        params.append(building)

    rows = db.execute(
        f"""
        SELECT
            substr(er.timestamp, 1, 10) AS date,
            AVG(er.actual_power_kw)     AS avg_actual_kw,
            COUNT(a.id)                 AS waste_count
        FROM energy_readings er
        LEFT JOIN anomalies a ON a.building = er.building
            AND substr(a.timestamp,1,10) = substr(er.timestamp,1,10) AND a.is_waste = 1
        {where}
        GROUP BY date
        ORDER BY date
        """,
        params,
    ).fetchall()
    return [
        {
            "date": r["date"],
            "avg_actual_kw": round(r["avg_actual_kw"], 2),
            "avg_predicted_kw": None,
            "waste_count": r["waste_count"],
        }
        for r in rows
    ]


# ── Submit readings (authenticated ingestion) ─────────────────────────────────
@router.post("/readings", response_model=ReadingOut, status_code=201)
def submit_reading(
    body: ReadingIn,
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    ts = body.timestamp
    hour = _parse_hour(ts)
    dow = _parse_dow(ts)
    is_weekend = int(dow in (5, 6))

    try:
        cur = db.execute(
            """
            INSERT INTO energy_readings
                (meter_id, building, zone, timestamp, actual_power_kw, occupancy,
                 temperature, humidity, hour, day_of_week, is_weekend, data_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                body.meter_id, body.building, body.zone, ts,
                body.actual_power_kw, body.occupancy,
                body.temperature, body.humidity,
                hour, dow, is_weekend, body.data_source,
            ),
        )
        # Update meter last_reading_at
        db.execute(
            "UPDATE meters SET last_reading_at = ? WHERE meter_id = ?",
            (ts, body.meter_id),
        )
        row = db.execute(
            "SELECT * FROM energy_readings WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return dict(row)
    except sqlite3.IntegrityError:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate reading: meter_id={body.meter_id}, timestamp={ts}",
        )


# ── Get recent readings ───────────────────────────────────────────────────────
@router.get("/readings", response_model=List[ReadingOut])
def get_readings(
    building: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    days: int = Query(7, ge=1, le=365),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    since = _days_ago_iso(days)
    params: list = [since]
    where = "WHERE timestamp >= ?"
    if building and building != "All Buildings":
        where += " AND building = ?"
        params.append(building)
    params.append(limit)

    rows = db.execute(
        f"SELECT * FROM energy_readings {where} ORDER BY timestamp DESC LIMIT ?",
        params,
    ).fetchall()
    return [dict(r) for r in rows]


# ── Anomalies / waste events ──────────────────────────────────────────────────
@router.get("/anomalies", response_model=List[AnomalyOut])
def get_anomalies(
    building: Optional[str] = Query(None),
    is_waste: Optional[bool] = Query(None),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(200, ge=1, le=1000),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    since = _days_ago_iso(days)
    params: list = [since]
    where = "WHERE timestamp >= ?"
    if building and building != "All Buildings":
        where += " AND building = ?"
        params.append(building)
    if is_waste is not None:
        where += " AND is_waste = ?"
        params.append(int(is_waste))
    params.append(limit)

    rows = db.execute(
        f"""
        SELECT * FROM anomalies
        {where}
        ORDER BY timestamp DESC LIMIT ?
        """,
        params,
    ).fetchall()
    return [_anomaly_row_to_out(r) for r in rows]


# ── Alerts ────────────────────────────────────────────────────────────────────
@router.get("/alerts", response_model=List[AlertOut])
def get_alerts(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=500),
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    where = "WHERE is_read = 0" if unread_only else ""
    rows = db.execute(
        f"SELECT * FROM alerts {where} ORDER BY created_at DESC LIMIT ?",
        (limit,),
    ).fetchall()
    return [dict(r) for r in rows]


@router.post("/alerts/{alert_id}/read", status_code=200)
def mark_alert_read(
    alert_id: int,
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(get_current_user),
):
    db.execute("UPDATE alerts SET is_read = 1 WHERE id = ?", (alert_id,))
    return {"message": "Alert marked as read"}


@router.post("/anomalies/{anomaly_id}/acknowledge", status_code=200)
def acknowledge_anomaly(
    anomaly_id: int,
    db: sqlite3.Connection = Depends(_db_gen),
    current_user=Depends(require_admin),
):
    ts = datetime.now(timezone.utc).isoformat()
    db.execute(
        """
        UPDATE anomalies
        SET is_acknowledged = 1, acknowledged_by = ?, acknowledged_at = ?
        WHERE id = ?
        """,
        (current_user["email"], ts, anomaly_id),
    )
    return {"message": "Anomaly acknowledged"}


# ── Helpers ───────────────────────────────────────────────────────────────────
def _days_ago_iso(days: int) -> str:
    from datetime import timedelta
    now = datetime.now(timezone.utc)
    delta = now - timedelta(days=days)
    return delta.isoformat()


def _parse_hour(ts: str) -> Optional[int]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).hour
    except Exception:
        return None


def _parse_dow(ts: str) -> Optional[int]:
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00")).weekday()
    except Exception:
        return None


def _anomaly_row_to_out(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "building": row["building"],
        "zone": row["zone"],
        "timestamp": row["timestamp"],
        "actual_power_kw": row["actual_power_kw"],
        "predicted_power_kw": row["predicted_power_kw"],
        "residual_kw": row["residual_kw"],
        "occupancy": row["occupancy"],
        "is_waste": bool(row["is_waste"]),
        "waste_severity": row["waste_severity"],
        "excess_kwh": row["excess_kwh"],
        "excess_cost_inr": row["excess_cost_inr"],
        "anomaly_type": row["anomaly_type"],
        "is_acknowledged": bool(row["is_acknowledged"]),
    }
