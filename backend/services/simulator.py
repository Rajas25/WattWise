"""
WattWise Simulated Energy Data Provider
=========================================
Generates clearly-labelled simulated readings that are ingested through
the same pipeline as future real hardware readings.

⚠️  ALL readings produced here carry data_source='simulated'.
    The application never presents simulated data as real sensor readings.

Usage:
    python -m backend.services.simulator          # run one batch
    python -m backend.services.simulator --loop   # run continuously
"""

import sys
import math
import random
import sqlite3
import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

# Project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from backend.config import settings
from backend.database import get_connection, init_db


# ── Building profiles (mirrors generate_data.py) ──────────────────────────────
BUILDING_PROFILES = [
    {
        "name": "Academic Block A",
        "zone": "Lecture Halls & Classrooms",
        "meter_id": "MTR-ACA-001",
        "base_kw": 12.0,
        "max_occ": 90,
        "power_per_person": 0.18,
        "hvac_k": 1.4,
        "weekend_active": False,
    },
    {
        "name": "Library & Computing Hub",
        "zone": "Central Study & Server Hub",
        "meter_id": "MTR-LIB-001",
        "base_kw": 25.0,
        "max_occ": 120,
        "power_per_person": 0.22,
        "hvac_k": 1.8,
        "weekend_active": True,
    },
    {
        "name": "Science Complex",
        "zone": "Advanced Chemistry & Bio Labs",
        "meter_id": "MTR-SCI-001",
        "base_kw": 18.0,
        "max_occ": 45,
        "power_per_person": 0.35,
        "hvac_k": 1.6,
        "weekend_active": False,
    },
    {
        "name": "Administrative Block",
        "zone": "Offices & Meeting Rooms",
        "meter_id": "MTR-ADM-001",
        "base_kw": 8.0,
        "max_occ": 50,
        "power_per_person": 0.16,
        "hvac_k": 1.2,
        "weekend_active": False,
    },
]


def _simulate_reading(prof: dict, ts: datetime, rng: random.Random) -> dict:
    """Compute a physics-based simulated power reading for one building/timestamp."""
    hour = ts.hour
    dow = ts.weekday()
    is_weekend = int(dow in (5, 6))

    # Temperature: sinusoidal diurnal cycle with subtropical baseline
    day_progress = (hour - 5) % 24
    daily_cycle = 8.0 * math.sin(math.pi * (day_progress / 12.0))
    seasonal = 3.0 * math.sin(2 * math.pi * (ts.timetuple().tm_yday / 365.0))
    temp = 24.0 + daily_cycle + seasonal + rng.gauss(0, 0.8)
    temp = max(16.0, min(42.0, temp))

    humidity = 85.0 - (temp - 16.0) * 1.8 + rng.gauss(0, 2.5)
    humidity = max(30.0, min(95.0, humidity))

    # Occupancy
    if is_weekend and not prof["weekend_active"]:
        occupancy = rng.choice([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1])
    elif is_weekend and prof["weekend_active"]:
        if 9 <= hour <= 21:
            ratio = 0.3 + 0.35 * math.sin(math.pi * ((hour - 9) / 12.0))
            occupancy = max(0, int(prof["max_occ"] * ratio + rng.gauss(0, 4)))
        else:
            occupancy = rng.choice([0, 0, 0, 0, 0, 0, 0, 2, 4])
    else:
        if 8 <= hour <= 18:
            ratio = 0.65 + 0.3 * math.sin(math.pi * ((hour - 8) / 10.0))
            occupancy = max(0, int(prof["max_occ"] * ratio + rng.gauss(0, 5)))
        elif 18 < hour <= 21:
            ratio = 0.20 + 0.15 * math.sin(math.pi * ((hour - 18) / 3.0))
            occupancy = max(0, int(prof["max_occ"] * ratio + rng.gauss(0, 3)))
        else:
            occupancy = rng.choice([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 2])
    occupancy = max(0, min(occupancy, prof["max_occ"]))

    p_base = prof["base_kw"]
    p_occ = occupancy * prof["power_per_person"]
    cooling_delta = max(0.0, temp - 24.0)
    heat_boost = (humidity - 50.0) * 0.03 if humidity > 50 else 0.0
    occ_ratio = occupancy / prof["max_occ"] if prof["max_occ"] > 0 else 0.0
    p_hvac = (cooling_delta + heat_boost) * prof["hvac_k"] * (0.4 + 0.6 * occ_ratio)
    p_sched = prof["base_kw"] * 0.25 if ((not is_weekend or prof["weekend_active"]) and 8 <= hour <= 18) else 0.0
    noise = rng.gauss(0, 0.9)
    power = max(2.0, p_base + p_occ + p_hvac + p_sched + noise)

    # ── Inject realistic waste anomalies (~4% of idle hours) ─────────────────
    # These are labelled as simulated waste events, not confirmed physical waste.
    anomaly_type = None
    is_idle = occupancy <= 5
    is_night = hour <= 5 or hour >= 22
    is_weekend_idle = is_weekend and not prof["weekend_active"]

    if is_idle and (is_night or is_weekend_idle) and rng.random() < 0.04:
        excess = rng.uniform(12.0, 30.0)
        power = power + excess
        if is_weekend_idle:
            anomaly_type = "Weekend Equipment Left Running (Simulated Waste)"
        else:
            anomaly_type = "Nighttime HVAC Overcooling (Simulated Waste)"
    elif is_idle and is_night and rng.random() < 0.025:
        excess = rng.uniform(14.0, 28.0)
        power = power + excess
        anomaly_type = "Empty Room After Hours (Simulated Waste)"
    power = round(power, 2)

    return {
        "meter_id": prof["meter_id"],
        "building": prof["name"],
        "zone": prof["zone"],
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "actual_power_kw": round(power, 2),
        "occupancy": occupancy,
        "temperature": round(temp, 2),
        "humidity": round(humidity, 2),
        "hour": hour,
        "day_of_week": dow,
        "is_weekend": is_weekend,
        "data_source": "simulated",
    }


def generate_historical_batch(
    conn: sqlite3.Connection,
    days_back: int = 7,
    seed: int = 42,
) -> int:
    """
    Generates `days_back` days of hourly readings for all buildings
    and inserts them into energy_readings (skips duplicates).
    Returns the number of new rows inserted.
    """
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    start = now - timedelta(days=days_back)

    inserted = 0
    ts = start
    while ts <= now:
        for prof in BUILDING_PROFILES:
            reading = _simulate_reading(prof, ts, rng)
            try:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO energy_readings
                        (meter_id, building, zone, timestamp, actual_power_kw, occupancy,
                         temperature, humidity, hour, day_of_week, is_weekend, data_source)
                    VALUES (:meter_id, :building, :zone, :timestamp, :actual_power_kw, :occupancy,
                            :temperature, :humidity, :hour, :day_of_week, :is_weekend, :data_source)
                    """,
                    reading,
                )
                if conn.execute("SELECT changes()").fetchone()[0] > 0:
                    inserted += 1
            except sqlite3.IntegrityError:
                pass
        ts += timedelta(hours=1)

    # Update meter last_reading_at
    for prof in BUILDING_PROFILES:
        conn.execute(
            "UPDATE meters SET last_reading_at = ? WHERE meter_id = ?",
            (now.strftime("%Y-%m-%dT%H:%M:%SZ"), prof["meter_id"]),
        )

    conn.commit()
    return inserted


def generate_current_readings(conn: sqlite3.Connection, seed: Optional[int] = None) -> int:
    """Generates one reading per building for 'now' and inserts it."""
    rng = random.Random(seed)
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    inserted = 0
    for prof in BUILDING_PROFILES:
        reading = _simulate_reading(prof, now, rng)
        try:
            conn.execute(
                """
                INSERT OR IGNORE INTO energy_readings
                    (meter_id, building, zone, timestamp, actual_power_kw, occupancy,
                     temperature, humidity, hour, day_of_week, is_weekend, data_source)
                VALUES (:meter_id, :building, :zone, :timestamp, :actual_power_kw, :occupancy,
                        :temperature, :humidity, :hour, :day_of_week, :is_weekend, :data_source)
                """,
                reading,
            )
            if conn.execute("SELECT changes()").fetchone()[0] > 0:
                inserted += 1
                conn.execute(
                    "UPDATE meters SET last_reading_at = ? WHERE meter_id = ?",
                    (reading["timestamp"], prof["meter_id"]),
                )
        except sqlite3.IntegrityError:
            pass
    conn.commit()
    return inserted


# ── CLI entry point ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time

    parser = argparse.ArgumentParser(description="WattWise Simulated Energy Data Provider")
    parser.add_argument("--loop", action="store_true", help="Run continuously every N seconds")
    parser.add_argument("--interval", type=int, default=settings.SIMULATOR_INTERVAL_SECONDS)
    parser.add_argument("--days", type=int, default=30, help="Historical days to backfill on first run")
    args = parser.parse_args()

    print("=" * 60)
    print("⚡ WattWise Simulated Energy Data Provider")
    print("⚠️  DATA SOURCE: SIMULATED (not real hardware)")
    print("=" * 60)

    init_db()
    conn = get_connection()

    # Backfill historical readings
    existing = conn.execute("SELECT COUNT(*) FROM energy_readings").fetchone()[0]
    if existing == 0:
        print(f"[Simulator] Backfilling {args.days} days of historical data...")
        n = generate_historical_batch(conn, days_back=args.days)
        print(f"[Simulator] Inserted {n} historical readings.")
    else:
        print(f"[Simulator] DB already has {existing} readings. Skipping historical backfill.")

    if args.loop:
        print(f"[Simulator] Running live simulation every {args.interval}s. Press Ctrl+C to stop.")
        while True:
            n = generate_current_readings(conn)
            print(f"[Simulator] {datetime.now(timezone.utc).isoformat()} — inserted {n} new readings")
            time.sleep(args.interval)
    else:
        n = generate_current_readings(conn)
        print(f"[Simulator] Generated {n} current readings.")
        conn.close()
