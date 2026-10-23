"""
WattWise SQLite Database Layer
=================================
Uses Python's built-in sqlite3.
Tables are created automatically on first startup (CREATE TABLE IF NOT EXISTS).
Existing data is NEVER deleted on startup.
"""

import sqlite3
import os
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from backend.config import settings


def get_connection() -> sqlite3.Connection:
    """Return a thread-local SQLite connection with Row factory."""
    conn = sqlite3.connect(settings.DATABASE_URL, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")   # Better concurrent reads
    conn.execute("PRAGMA foreign_keys=ON")    # Enforce FK constraints
    return conn


@contextmanager
def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Context manager that yields a connection and commits/rolls back."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Schema Definition
# ─────────────────────────────────────────────────────────────────────────────
SCHEMA_SQL = """
-- Users (students and admins)
CREATE TABLE IF NOT EXISTS users (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    email             TEXT    UNIQUE NOT NULL,
    hashed_password   TEXT    NOT NULL,
    full_name         TEXT    NOT NULL,
    role              TEXT    NOT NULL DEFAULT 'student'
                              CHECK(role IN ('student','admin')),
    is_active         INTEGER NOT NULL DEFAULT 1,
    created_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    updated_at        TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- Campus buildings
CREATE TABLE IF NOT EXISTS buildings (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT    UNIQUE NOT NULL,
    zone          TEXT    NOT NULL,
    base_kw       REAL    NOT NULL DEFAULT 10.0,
    max_occupancy INTEGER NOT NULL DEFAULT 100,
    is_active     INTEGER NOT NULL DEFAULT 1,
    created_at    TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_buildings_name ON buildings(name);

-- Energy meters / sensors
CREATE TABLE IF NOT EXISTS meters (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meter_id        TEXT    UNIQUE NOT NULL,
    building_id     INTEGER NOT NULL REFERENCES buildings(id),
    description     TEXT,
    is_active       INTEGER NOT NULL DEFAULT 1,
    last_reading_at TEXT,
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_meters_building ON meters(building_id);

-- Energy readings (one row per meter per hour)
CREATE TABLE IF NOT EXISTS energy_readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    meter_id        TEXT    NOT NULL,
    building        TEXT    NOT NULL,
    zone            TEXT    NOT NULL,
    timestamp       TEXT    NOT NULL,
    actual_power_kw REAL    NOT NULL CHECK(actual_power_kw >= 0),
    occupancy       INTEGER NOT NULL DEFAULT 0 CHECK(occupancy >= 0),
    temperature     REAL,
    humidity        REAL,
    hour            INTEGER,
    day_of_week     INTEGER,
    is_weekend      INTEGER DEFAULT 0,
    data_source     TEXT    NOT NULL DEFAULT 'simulated',
    created_at      TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now')),
    UNIQUE(meter_id, timestamp)
);
CREATE INDEX IF NOT EXISTS idx_readings_meter     ON energy_readings(meter_id);
CREATE INDEX IF NOT EXISTS idx_readings_building  ON energy_readings(building);
CREATE INDEX IF NOT EXISTS idx_readings_timestamp ON energy_readings(timestamp);

-- Anomalies / detected waste events
CREATE TABLE IF NOT EXISTS anomalies (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    reading_id          INTEGER REFERENCES energy_readings(id),
    building            TEXT    NOT NULL,
    zone                TEXT    NOT NULL,
    timestamp           TEXT    NOT NULL,
    actual_power_kw     REAL    NOT NULL,
    predicted_power_kw  REAL    NOT NULL,
    residual_kw         REAL    NOT NULL,
    occupancy           INTEGER NOT NULL,
    is_waste            INTEGER NOT NULL DEFAULT 0,
    waste_severity      TEXT,
    excess_kwh          REAL    NOT NULL DEFAULT 0.0,
    excess_cost_inr     REAL    NOT NULL DEFAULT 0.0,
    anomaly_type        TEXT,
    is_acknowledged     INTEGER NOT NULL DEFAULT 0,
    acknowledged_by     TEXT,
    acknowledged_at     TEXT,
    created_at          TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_anomalies_building   ON anomalies(building);
CREATE INDEX IF NOT EXISTS idx_anomalies_timestamp  ON anomalies(timestamp);
CREATE INDEX IF NOT EXISTS idx_anomalies_is_waste   ON anomalies(is_waste);

-- Alerts
CREATE TABLE IF NOT EXISTS alerts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    anomaly_id  INTEGER REFERENCES anomalies(id),
    building    TEXT    NOT NULL,
    severity    TEXT    NOT NULL CHECK(severity IN ('Low','Medium','High')),
    message     TEXT    NOT NULL,
    is_read     INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_alerts_is_read ON alerts(is_read);
"""


def init_db(database_url: str = None) -> None:
    """
    Safely initialises all tables using CREATE TABLE IF NOT EXISTS.
    Existing data is preserved. Also seeds default campus buildings.
    """
    url = database_url or settings.DATABASE_URL

    # Ensure directory exists
    Path(url).parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(url, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
        _seed_buildings(conn)
        conn.commit()
        print(f"[DB] Database ready at: {url}")
    finally:
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Seed: default campus buildings (idempotent — INSERT OR IGNORE)
# ─────────────────────────────────────────────────────────────────────────────
_DEFAULT_BUILDINGS = [
    ("Academic Block A",       "Lecture Halls & Classrooms",      12.0, 90),
    ("Library & Computing Hub","Central Study & Server Hub",       25.0, 120),
    ("Science Complex",        "Advanced Chemistry & Bio Labs",    18.0, 45),
    ("Administrative Block",   "Offices & Meeting Rooms",          8.0, 50),
]


def _seed_buildings(conn: sqlite3.Connection) -> None:
    for name, zone, base_kw, max_occ in _DEFAULT_BUILDINGS:
        conn.execute(
            """
            INSERT OR IGNORE INTO buildings (name, zone, base_kw, max_occupancy)
            VALUES (?, ?, ?, ?)
            """,
            (name, zone, base_kw, max_occ),
        )

    # Seed meters (one per building) — use Row factory via explicit row_factory
    conn.row_factory = sqlite3.Row
    cursor = conn.execute("SELECT id, name FROM buildings")
    rows = cursor.fetchall()
    conn.row_factory = None  # restore
    for row in rows:
        bname = row["name"]
        bid = row["id"]
        meter_id = f"MTR-{bname[:3].upper().replace(' ','')}-001"
        conn.execute(
            """
            INSERT OR IGNORE INTO meters (meter_id, building_id, description)
            VALUES (?, ?, ?)
            """,
            (meter_id, bid, f"Primary meter for {bname}"),
        )
