"""
/api/admin — Admin-only dashboard and management endpoints.
All endpoints require role='admin', enforced via require_admin dependency.
"""

import sqlite3
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException

from backend.config import settings
from backend.models.schemas import AdminDashboard, BuildingOut
from backend.routers.deps import _db_gen, require_admin

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboard)
def admin_dashboard(
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    total_users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_buildings = db.execute("SELECT COUNT(*) FROM buildings WHERE is_active=1").fetchone()[0]
    total_meters = db.execute("SELECT COUNT(*) FROM meters WHERE is_active=1").fetchone()[0]
    total_readings = db.execute("SELECT COUNT(*) FROM energy_readings").fetchone()[0]
    total_anomalies = db.execute("SELECT COUNT(*) FROM anomalies").fetchone()[0]
    unack = db.execute(
        "SELECT COUNT(*) FROM anomalies WHERE is_acknowledged = 0 AND is_waste = 1"
    ).fetchone()[0]
    unread_alerts = db.execute("SELECT COUNT(*) FROM alerts WHERE is_read = 0").fetchone()[0]

    waste_agg = db.execute(
        "SELECT COALESCE(SUM(excess_kwh),0), COALESCE(SUM(excess_cost_inr),0) FROM anomalies WHERE is_waste=1"
    ).fetchone()

    return AdminDashboard(
        total_users=total_users,
        total_buildings=total_buildings,
        total_meters=total_meters,
        total_readings=total_readings,
        total_anomalies=total_anomalies,
        unacknowledged_anomalies=unack,
        unread_alerts=unread_alerts,
        total_waste_kwh=round(waste_agg[0], 2),
        total_waste_inr=round(waste_agg[1], 2),
        system_note="All figures from local SQLite database — simulated campus telemetry",
    )


@router.get("/meters")
def list_meters(
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    rows = db.execute(
        """
        SELECT m.*, b.name AS building_name, b.zone
        FROM meters m
        JOIN buildings b ON b.id = m.building_id
        ORDER BY m.building_id
        """
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        # Compute staleness (no reading in last 2 hours = stale)
        stale = True
        if d.get("last_reading_at"):
            try:
                last = datetime.fromisoformat(d["last_reading_at"].replace("Z", "+00:00"))
                diff_minutes = (datetime.now(timezone.utc) - last).total_seconds() / 60
                stale = diff_minutes > 120
            except Exception:
                pass
        d["is_stale"] = stale
        result.append(d)
    return result


@router.get("/ingestion/health")
def ingestion_health(
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    total = db.execute("SELECT COUNT(*) FROM energy_readings").fetchone()[0]
    latest = db.execute(
        "SELECT timestamp, data_source FROM energy_readings ORDER BY timestamp DESC LIMIT 1"
    ).fetchone()
    errors = db.execute(
        "SELECT COUNT(*) FROM anomalies WHERE created_at >= strftime('%Y-%m-%dT%H:%M:%SZ', datetime('now','-1 hour'))"
    ).fetchone()[0]
    return {
        "total_readings": total,
        "latest_reading_timestamp": latest["timestamp"] if latest else None,
        "latest_data_source": latest["data_source"] if latest else None,
        "anomalies_last_hour": errors,
        "status": "healthy" if total > 0 else "no_data",
    }


@router.get("/buildings", response_model=List[BuildingOut])
def admin_list_buildings(
    db: sqlite3.Connection = Depends(_db_gen),
    _=Depends(require_admin),
):
    rows = db.execute("SELECT * FROM buildings").fetchall()
    return [dict(r) for r in rows]
