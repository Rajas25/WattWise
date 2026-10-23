"""WattWise complete database audit script."""
import sqlite3
import os

DB = 'data/wattwise.db'
conn = sqlite3.connect(DB)
conn.row_factory = sqlite3.Row

print('=' * 60)
print('  WATTWISE DATABASE AUDIT')
print(f'  File: {DB}')
print('=' * 60)

# ── Tables ────────────────────────────────────────────────────────────────────
tables = conn.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()
print(f'\n[TABLES] ({len(tables)} total)')
for t in tables:
    n = t['name']
    cnt = conn.execute(f'SELECT COUNT(*) FROM {n}').fetchone()[0]
    cols = [c[1] for c in conn.execute(f'PRAGMA table_info({n})').fetchall()]
    print(f'  {n:25s} {cnt:>6} rows   cols: {", ".join(cols)}')

# ── Users ─────────────────────────────────────────────────────────────────────
print('\n[USERS]')
users = conn.execute(
    'SELECT id, email, full_name, role, is_active, created_at FROM users'
).fetchall()
for u in users:
    active = "ACTIVE" if u['is_active'] else "inactive"
    print(f'  #{u["id"]:>2}  {u["full_name"]:25s}  role={u["role"]:7s}  {u["email"]}  [{active}]')

# ── Buildings ─────────────────────────────────────────────────────────────────
print('\n[BUILDINGS]')
for b in conn.execute(
    'SELECT id, name, zone, base_kw, max_occupancy, is_active FROM buildings'
).fetchall():
    active = "ACTIVE" if b['is_active'] else "inactive"
    print(f'  #{b["id"]}  {b["name"]:30s}  zone={b["zone"]}  base={b["base_kw"]}kW  max_occ={b["max_occupancy"]}  [{active}]')

# ── Meters ────────────────────────────────────────────────────────────────────
print('\n[METERS]')
for m in conn.execute(
    'SELECT meter_id, building_id, description, is_active, last_reading_at FROM meters'
).fetchall():
    active = "ACTIVE" if m['is_active'] else "inactive"
    last = str(m['last_reading_at'] or 'never')[:16]
    print(f'  {m["meter_id"]:20s}  bldg_id={m["building_id"]}  {str(m["description"] or "")[:35]}  last={last}  [{active}]')


# ── Energy Readings ───────────────────────────────────────────────────────────
print('\n[ENERGY READINGS]')
r = conn.execute('''
    SELECT
        COUNT(*) AS total,
        MIN(timestamp) AS earliest,
        MAX(timestamp) AS latest,
        ROUND(AVG(actual_power_kw), 2) AS avg_kw,
        ROUND(SUM(actual_power_kw) / 1000.0, 2) AS total_mwh,
        data_source
    FROM energy_readings
    GROUP BY data_source
''').fetchone()
if r:
    print(f'  Count   : {r["total"]:,} readings')
    print(f'  Period  : {str(r["earliest"])[:16]} → {str(r["latest"])[:16]}')
    print(f'  Avg Pwr : {r["avg_kw"]} kW')
    print(f'  Total   : {r["total_mwh"]} MWh')
    print(f'  Source  : {r["data_source"]}')

# Per-building breakdown
print('\n  Per-building reading counts:')
for row in conn.execute('''
    SELECT building, COUNT(*) cnt,
           ROUND(AVG(actual_power_kw),2) avg_kw
    FROM energy_readings
    GROUP BY building ORDER BY building
''').fetchall():
    print(f'    {row["building"]:30s}  {row["cnt"]:>5} readings  avg {row["avg_kw"]} kW')

# ── Anomalies ─────────────────────────────────────────────────────────────────
print('\n[ANOMALIES / WASTE EVENTS]')
a = conn.execute('''
    SELECT
        COUNT(*) total,
        ROUND(SUM(COALESCE(excess_cost_inr, 0)), 2) total_inr,
        ROUND(MAX(COALESCE(residual_kw, 0)), 2) max_kw,
        COUNT(CASE WHEN waste_severity="High" THEN 1 END) high_sev,
        COUNT(CASE WHEN waste_severity="Medium" THEN 1 END) med_sev,
        COUNT(CASE WHEN waste_severity="Low" THEN 1 END) low_sev
    FROM anomalies
''').fetchone()
print(f'  Total events   : {a["total"]}')
print(f'  Estimated cost : INR {(a["total_inr"] or 0):,.2f}')
print(f'  Max residual   : {a["max_kw"] or 0} kW')
print(f'  Severity split : High={a["high_sev"]}  Medium={a["med_sev"]}  Low={a["low_sev"]}')


# ── Alerts ────────────────────────────────────────────────────────────────────
print('\n[ALERTS]')
al = conn.execute('''
    SELECT
        COUNT(*) total,
        SUM(CASE WHEN is_read=0 THEN 1 ELSE 0 END) unread,
        SUM(CASE WHEN severity="High" THEN 1 ELSE 0 END) high
    FROM alerts
''').fetchone()
print(f'  Total: {al["total"]}  Unread: {al["unread"]}  High-severity: {al["high"]}')

# ── DB file info ──────────────────────────────────────────────────────────────
conn.close()
size_mb = os.path.getsize(DB) / 1024 / 1024
print(f'\n[DB FILE]  {os.path.abspath(DB)}')
print(f'           {size_mb:.2f} MB on disk')
print('\n' + '=' * 60)
print('  AUDIT COMPLETE')
print('=' * 60)
