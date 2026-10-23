"""
Building Energy Waste Detective: Realistic Campus Electricity Dataset Generator
================================================================================
Simulates 90 days of hourly electricity consumption across 4 representative
campus buildings and functional zones.

NOTE: This dataset is synthetic and simulated for academic machine learning research,
benchmarking, and viva presentation. It models realistic thermal, occupancy, and
operational physical dynamics, while deliberately injecting labeled anomalies for
ground-truth evaluation without leaking target or anomaly labels into model features.
"""

import os
import numpy as np
import pandas as pd


def generate_campus_energy_dataset(
    start_date: str = "2026-01-01 00:00:00",
    days: int = 90,
    random_state: int = 42,
) -> pd.DataFrame:
    """
    Generates a realistic synthetic dataset simulating campus electricity usage.
    
    Parameters:
    -----------
    start_date : str
        Start timestamp in YYYY-MM-DD HH:MM:SS format.
    days : int
        Number of days of hourly telemetry to simulate.
    random_state : int
        Random seed for reproducibility.
        
    Returns:
    --------
    pd.DataFrame
        Synthetic dataset with operational features, actual_power_kw, and
        evaluation-only ground-truth labels.
    """
    np.random.seed(random_state)
    
    # 1. Generate hourly timestamps
    timestamps = pd.date_range(start=start_date, periods=days * 24, freq="h")
    
    # Campus building profiles with typical baseloads and equipment characteristics
    building_profiles = [
        {
            "building": "Academic Block A",
            "zone": "Lecture Halls & Classrooms",
            "base_kw": 12.0,
            "max_occupancy": 90,
            "power_per_person": 0.18,
            "hvac_sensitivity": 1.4,
            "weekend_active": False,
        },
        {
            "building": "Library & Computing Hub",
            "zone": "Central Study & Server Hub",
            "base_kw": 25.0,  # higher baseload due to continuous server and networking gear
            "max_occupancy": 120,
            "power_per_person": 0.22,
            "hvac_sensitivity": 1.8,
            "weekend_active": True,  # open on weekends
        },
        {
            "building": "Science Complex",
            "zone": "Advanced Chemistry & Bio Labs",
            "base_kw": 18.0,  # fume hoods, refrigeration, sensitive lab equipment
            "max_occupancy": 45,
            "power_per_person": 0.35,  # higher per-person equipment usage
            "hvac_sensitivity": 1.6,
            "weekend_active": False,
        },
        {
            "building": "Administrative Block",
            "zone": "Offices & Meeting Rooms",
            "base_kw": 8.0,
            "max_occupancy": 50,
            "power_per_person": 0.16,
            "hvac_sensitivity": 1.2,
            "weekend_active": False,
        },
    ]

    all_records = []

    for prof in building_profiles:
        b_name = prof["building"]
        zone_name = prof["zone"]
        base_kw = prof["base_kw"]
        max_occ = prof["max_occupancy"]
        p_person = prof["power_per_person"]
        hvac_k = prof["hvac_sensitivity"]
        weekend_ok = prof["weekend_active"]

        for ts in timestamps:
            hour = ts.hour
            day_of_week = ts.dayofweek  # 0=Monday, 6=Sunday
            is_weekend = 1 if day_of_week in [5, 6] else 0

            # Realistic Diurnal Temperature Modeling (Indian/subtropical campus climate)
            # Daily sinusoidal cycle: coldest at ~5:00 AM, warmest at ~14:00 PM
            day_progress = (hour - 5) % 24
            daily_temp_cycle = 8.0 * np.sin(np.pi * (day_progress / 12.0))
            seasonal_trend = 3.0 * np.sin(2 * np.pi * (ts.dayofyear / 365.0))
            ambient_temp = 24.0 + daily_temp_cycle + seasonal_trend + np.random.normal(0, 0.8)
            ambient_temp = np.clip(ambient_temp, 16.0, 42.0)

            # Humidity inversely correlated with temperature
            humidity = 85.0 - (ambient_temp - 16.0) * 1.8 + np.random.normal(0, 2.5)
            humidity = np.clip(humidity, 30.0, 95.0)

            # Realistic Occupancy Modeling
            if is_weekend and not weekend_ok:
                # Idle weekend
                occupancy = int(np.random.choice([0, 1], p=[0.92, 0.08]))
            elif is_weekend and weekend_ok:
                # Library weekend
                if 9 <= hour <= 21:
                    occ_ratio = 0.3 + 0.35 * np.sin(np.pi * ((hour - 9) / 12.0))
                    occupancy = int(max_occ * occ_ratio + np.random.normal(0, 4))
                else:
                    occupancy = int(np.random.choice([0, 2, 4], p=[0.7, 0.2, 0.1]))
            else:
                # Weekdays
                if 8 <= hour <= 18:  # Core academic/office hours
                    occ_ratio = 0.65 + 0.3 * np.sin(np.pi * ((hour - 8) / 10.0))
                    occupancy = int(max_occ * occ_ratio + np.random.normal(0, 5))
                elif 18 < hour <= 21:  # Evening study/overtime
                    occ_ratio = 0.20 + 0.15 * np.sin(np.pi * ((hour - 18) / 3.0))
                    occupancy = int(max_occ * occ_ratio + np.random.normal(0, 3))
                else:  # Night
                    occupancy = int(np.random.choice([0, 1, 2], p=[0.85, 0.10, 0.05]))
            
            occupancy = max(0, min(occupancy, max_occ))

            # Physics-based Power Consumption Modeling
            # 1. Base standby power
            p_base = base_kw
            
            # 2. Occupancy load (computers, lights, small appliances)
            p_occ = occupancy * p_person
            
            # 3. HVAC cooling load (AC kicks in when temp > 24°C, modulated by humidity index)
            cooling_delta = max(0.0, ambient_temp - 24.0)
            heat_index_boost = (humidity - 50.0) * 0.03 if humidity > 50 else 0.0
            p_hvac = (cooling_delta + heat_index_boost) * hvac_k * (0.4 + 0.6 * (occupancy / max_occ if max_occ > 0 else 0))
            
            # 4. Schedule-based lighting and equipment
            p_sched = 0.0
            if (not is_weekend or weekend_ok) and 8 <= hour <= 18:
                p_sched = base_kw * 0.25

            # Total normal power with natural sensor noise
            sensor_noise = np.random.normal(0, 0.9)
            normal_power = max(2.0, p_base + p_occ + p_hvac + p_sched + sensor_noise)

            all_records.append({
                "timestamp": ts,
                "building": b_name,
                "zone": zone_name,
                "occupancy": occupancy,
                "temperature": round(ambient_temp, 2),
                "humidity": round(humidity, 2),
                "hour": hour,
                "day_of_week": day_of_week,
                "is_weekend": is_weekend,
                "actual_power_kw": round(normal_power, 2),
                "is_anomaly": 0,
                "anomaly_type": "Normal",
            })

    df = pd.DataFrame(all_records)

    # 2. Deliberately Introduce Realistic Anomalies (~4.8% of total records)
    # Ensuring variety:
    # A) "Empty Room High Power" (True Energy Waste: HVAC/lighting left active overnight or on weekends in empty zone)
    # B) "Nighttime HVAC Overcooling" (True Energy Waste: AC compressors running at full blast while outdoor temp is low)
    # C) "Weekend Equipment Left On" (True Energy Waste: lab equipment left running on Sunday with 0 occupants)
    # D) "Sensor Glitch Spike" (Statistical outlier / meter fault: momentary +50 kW spike, not persistent waste)
    # E) "Sensor Drop / Outage" (Power dropped near zero during daytime due to localized trip)

    total_rows = len(df)
    
    # A) Empty Room High Power (Night or Weekend with 0 occupancy, but power jumps by 15-35 kW)
    empty_candidates = df[(df["occupancy"] == 0) & ((df["hour"] >= 22) | (df["hour"] <= 5) | (df["is_weekend"] == 1))].index
    num_empty_anomalies = int(len(empty_candidates) * 0.035)
    selected_empty = np.random.choice(empty_candidates, size=num_empty_anomalies, replace=False)
    for idx in selected_empty:
        excess = np.random.uniform(14.0, 32.0)
        df.loc[idx, "actual_power_kw"] = round(df.loc[idx, "actual_power_kw"] + excess, 2)
        df.loc[idx, "is_anomaly"] = 1
        df.loc[idx, "anomaly_type"] = "Empty Room High Consumption (Waste)"

    # B) Nighttime HVAC Overcooling (Idle hours with low outdoor temp, yet AC is maxed out)
    night_candidates = df[(df["occupancy"] <= 2) & (df["hour"].between(1, 4)) & (~df.index.isin(selected_empty))].index
    num_night_anomalies = int(len(night_candidates) * 0.04)
    selected_night = np.random.choice(night_candidates, size=num_night_anomalies, replace=False)
    for idx in selected_night:
        excess = np.random.uniform(12.0, 24.0)
        df.loc[idx, "actual_power_kw"] = round(df.loc[idx, "actual_power_kw"] + excess, 2)
        df.loc[idx, "is_anomaly"] = 1
        df.loc[idx, "anomaly_type"] = "Nighttime HVAC Overcooling (Waste)"

    # C) Weekend Equipment Left Running in Labs or Classrooms
    weekend_candidates = df[(df["is_weekend"] == 1) & (df["occupancy"] == 0) & (df["building"].isin(["Academic Block A", "Science Complex"])) & (~df.index.isin(selected_empty)) & (~df.index.isin(selected_night))].index
    num_weekend_anomalies = int(len(weekend_candidates) * 0.04)
    selected_weekend = np.random.choice(weekend_candidates, size=num_weekend_anomalies, replace=False)
    for idx in selected_weekend:
        excess = np.random.uniform(16.0, 28.0)
        df.loc[idx, "actual_power_kw"] = round(df.loc[idx, "actual_power_kw"] + excess, 2)
        df.loc[idx, "is_anomaly"] = 1
        df.loc[idx, "anomaly_type"] = "Weekend Equipment Left Running (Waste)"

    # D) Sensor Glitch Spikes (Statistical Outlier - momentary metering error)
    remaining_candidates = df[df["is_anomaly"] == 0].index
    num_spikes = 20
    selected_spikes = np.random.choice(remaining_candidates, size=num_spikes, replace=False)
    for idx in selected_spikes:
        excess = np.random.uniform(35.0, 55.0)
        df.loc[idx, "actual_power_kw"] = round(df.loc[idx, "actual_power_kw"] + excess, 2)
        df.loc[idx, "is_anomaly"] = 1
        df.loc[idx, "anomaly_type"] = "Sensor Glitch Spike"

    # E) Sensor Drop / Localized Outage (Statistical Anomaly - drop)
    remaining_candidates_day = df[(df["is_anomaly"] == 0) & (df["occupancy"] > 20)].index
    num_drops = 15
    selected_drops = np.random.choice(remaining_candidates_day, size=num_drops, replace=False)
    for idx in selected_drops:
        df.loc[idx, "actual_power_kw"] = round(max(0.5, df.loc[idx, "actual_power_kw"] * 0.15), 2)
        df.loc[idx, "is_anomaly"] = 1
        df.loc[idx, "anomaly_type"] = "Localized Power Outage / Drop"

    # Sort chronologically by timestamp and building
    df = df.sort_values(by=["timestamp", "building"]).reset_index(drop=True)
    return df


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "energy_data.csv")

    print("=" * 70)
    print("Generating Realistic Campus Electricity Dataset...")
    print("=" * 70)
    df = generate_campus_energy_dataset()
    df.to_csv(output_path, index=False)

    print(f"\n[OK] Dataset successfully generated and saved to: {output_path}")
    print(f"Total Rows: {len(df):,}")
    print(f"Date Range: {df['timestamp'].min()} to {df['timestamp'].max()}")
    print(f"Buildings Covered: {df['building'].nunique()} ({list(df['building'].unique())})")
    print(f"Average Power: {df['actual_power_kw'].mean():.2f} kW (Min: {df['actual_power_kw'].min()} kW, Max: {df['actual_power_kw'].max()} kW)")
    print(f"Average Occupancy: {df['occupancy'].mean():.1f} people (Max: {df['occupancy'].max()})")
    
    anomaly_counts = df["anomaly_type"].value_counts()
    print("\nAnomaly Breakdown (For Ground-Truth Evaluation Only):")
    for atype, count in anomaly_counts.items():
        pct = (count / len(df)) * 100
        print(f" - {atype:<45}: {count:4d} ({pct:.2f}%)")
    
    total_anomalies = df['is_anomaly'].sum()
    print(f"\nTotal Anomalies: {total_anomalies} ({(total_anomalies / len(df)) * 100:.2f}% of dataset)")
    print("=" * 70)
