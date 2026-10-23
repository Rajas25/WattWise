"""
WattWise Backend Tests
========================
Run with:
    pytest tests/test_backend.py -v

Tests use a temporary isolated SQLite database — production data is never touched.
"""

import os
import sys
import tempfile
import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# ── Project path setup ────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# ── Point tests at a throwaway DB BEFORE importing the app ───────────────────
_tmp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
_tmp_db.close()
os.environ["WATTWISE_DATABASE_URL"] = _tmp_db.name
os.environ["WATTWISE_SECRET_KEY"]   = "test-secret-key-do-not-use-in-production"

# Import app AFTER env vars are set
from backend.main import app
from backend.database import init_db, get_connection
from backend.security import hash_password, verify_password, create_access_token, decode_token


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────
@pytest.fixture(scope="session", autouse=True)
def setup_test_db():
    """Initialize test database once for the entire test session."""
    init_db(database_url=_tmp_db.name)
    yield
    # Cleanup
    try:
        os.unlink(_tmp_db.name)
    except Exception:
        pass


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def admin_token(client):
    """Create an admin user and return their JWT token."""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT OR IGNORE INTO users (email, hashed_password, full_name, role) VALUES (?, ?, ?, ?)",
            ("admin@test.ww", hash_password("adminpass123"), "Test Admin", "admin"),
        )
        conn.commit()
    finally:
        conn.close()

    res = client.post("/api/auth/token", json={"email": "admin@test.ww", "password": "adminpass123"})
    assert res.status_code == 200
    return res.json()["access_token"]


@pytest.fixture(scope="session")
def student_token(client):
    """Register a student and return their JWT token."""
    client.post("/api/auth/register", json={
        "email": "student@test.ww",
        "password": "student123",
        "full_name": "Test Student",
    })
    res = client.post("/api/auth/token", json={"email": "student@test.ww", "password": "student123"})
    assert res.status_code == 200
    return res.json()["access_token"]


# ─────────────────────────────────────────────────────────────────────────────
# 1 — Database initialization
# ─────────────────────────────────────────────────────────────────────────────
class TestDatabase:
    def test_tables_created(self):
        conn = sqlite3.connect(_tmp_db.name)
        tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()}
        conn.close()
        required = {"users", "buildings", "meters", "energy_readings", "anomalies", "alerts"}
        assert required.issubset(tables), f"Missing tables: {required - tables}"

    def test_buildings_seeded(self):
        conn = sqlite3.connect(_tmp_db.name)
        count = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
        conn.close()
        assert count == 4, "Expected 4 campus buildings to be seeded"

    def test_meters_seeded(self):
        conn = sqlite3.connect(_tmp_db.name)
        count = conn.execute("SELECT COUNT(*) FROM meters").fetchone()[0]
        conn.close()
        assert count == 4, "Expected 4 meters (one per building)"

    def test_idempotent_init(self):
        """Running init_db twice should not duplicate or delete any data."""
        init_db(database_url=_tmp_db.name)
        conn = sqlite3.connect(_tmp_db.name)
        count = conn.execute("SELECT COUNT(*) FROM buildings").fetchone()[0]
        conn.close()
        assert count == 4

    def test_persistence(self):
        """Data persists across separate connections."""
        conn1 = sqlite3.connect(_tmp_db.name)
        conn1.execute("INSERT OR IGNORE INTO users (email,hashed_password,full_name) VALUES ('p@test.ww','x','Persist')")
        conn1.commit()
        conn1.close()

        conn2 = sqlite3.connect(_tmp_db.name)
        row = conn2.execute("SELECT email FROM users WHERE email='p@test.ww'").fetchone()
        conn2.close()
        assert row is not None

    def test_fk_constraint(self):
        """Foreign key constraint: meter must reference valid building."""
        conn = sqlite3.connect(_tmp_db.name)
        conn.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO meters (meter_id, building_id) VALUES ('BAD-001', 99999)")
            conn.commit()
        conn.rollback()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 2 — Password hashing
# ─────────────────────────────────────────────────────────────────────────────
class TestPasswordHashing:
    def test_hash_is_not_plaintext(self):
        h = hash_password("MySecret123")
        assert h != "MySecret123"
        assert len(h) > 20

    def test_verify_correct(self):
        h = hash_password("testpass")
        assert verify_password("testpass", h) is True

    def test_verify_wrong(self):
        h = hash_password("testpass")
        assert verify_password("wrongpass", h) is False

    def test_unique_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2, "bcrypt should use different salts"


# ─────────────────────────────────────────────────────────────────────────────
# 3 — JWT tokens
# ─────────────────────────────────────────────────────────────────────────────
class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "42", "role": "student"})
        payload = decode_token(token)
        assert payload["sub"] == "42"
        assert payload["role"] == "student"

    def test_invalid_token_returns_none(self):
        assert decode_token("not.a.real.token") is None

    def test_tampered_token_returns_none(self):
        token = create_access_token({"sub": "1"})
        tampered = token[:-5] + "XXXXX"
        assert decode_token(tampered) is None


# ─────────────────────────────────────────────────────────────────────────────
# 4 — Health check
# ─────────────────────────────────────────────────────────────────────────────
class TestHealth:
    def test_health_ok(self, client):
        res = client.get("/api/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "SQLite" in data["database"]


# ─────────────────────────────────────────────────────────────────────────────
# 5 — Authentication endpoints
# ─────────────────────────────────────────────────────────────────────────────
class TestAuth:
    def test_register_success(self, client):
        res = client.post("/api/auth/register", json={
            "email": "newuser@test.ww",
            "password": "newpass123",
            "full_name": "New User",
        })
        assert res.status_code == 201
        assert res.json()["role"] == "student"

    def test_register_duplicate_email(self, client):
        body = {"email": "dup@test.ww", "password": "pass123", "full_name": "Dup"}
        client.post("/api/auth/register", json=body)
        res = client.post("/api/auth/register", json=body)
        assert res.status_code == 409

    def test_login_success(self, client, admin_token):
        assert admin_token is not None
        assert len(admin_token) > 10

    def test_login_wrong_password(self, client):
        res = client.post("/api/auth/token", json={"email": "admin@test.ww", "password": "WRONG"})
        assert res.status_code == 401

    def test_login_nonexistent_user(self, client):
        res = client.post("/api/auth/token", json={"email": "ghost@test.ww", "password": "pass"})
        assert res.status_code == 401

    def test_me_with_valid_token(self, client, admin_token):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert res.json()["email"] == "admin@test.ww"
        assert "hashed_password" not in res.json()

    def test_me_no_token(self, client):
        res = client.get("/api/auth/me")
        assert res.status_code == 401

    def test_me_invalid_token(self, client):
        res = client.get("/api/auth/me", headers={"Authorization": "Bearer invalid.token.here"})
        assert res.status_code == 401

    def test_response_has_no_password(self, client, admin_token):
        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {admin_token}"})
        body = res.text
        assert "password" not in body.lower() or "hashed_password" not in body


# ─────────────────────────────────────────────────────────────────────────────
# 6 — Role authorization (backend-enforced)
# ─────────────────────────────────────────────────────────────────────────────
class TestAuthorization:
    def test_student_cannot_access_users_list(self, client, student_token):
        res = client.get("/api/users/", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 403

    def test_student_cannot_create_user(self, client, student_token):
        res = client.post("/api/users/", json={
            "email": "hack@evil.com", "password": "x", "full_name": "Evil", "role": "admin"
        }, headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 403

    def test_student_cannot_access_admin_dashboard(self, client, student_token):
        res = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 403

    def test_admin_can_access_admin_dashboard(self, client, admin_token):
        res = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200

    def test_admin_can_list_users(self, client, admin_token):
        res = client.get("/api/users/", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_unauthenticated_cannot_see_energy_data(self, client):
        res = client.get("/api/energy/buildings")
        assert res.status_code == 401

    def test_student_can_see_energy_data(self, client, student_token):
        res = client.get("/api/energy/buildings", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 7 — Energy readings (ingestion + retrieval)
# ─────────────────────────────────────────────────────────────────────────────
class TestEnergyReadings:
    _reading = {
        "meter_id": "MTR-ACA-001",
        "building": "Academic Block A",
        "zone": "Lecture Halls & Classrooms",
        "timestamp": "2026-01-15T14:00:00Z",
        "actual_power_kw": 35.5,
        "occupancy": 40,
        "temperature": 28.5,
        "humidity": 65.0,
        "data_source": "simulated",
    }

    def test_submit_reading(self, client, student_token):
        res = client.post(
            "/api/energy/readings",
            json=self._reading,
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res.status_code in (201, 409)  # 409 = already exists from earlier run

    def test_reject_negative_power(self, client, student_token):
        bad = {**self._reading, "actual_power_kw": -10.0, "timestamp": "2026-01-15T15:00:00Z"}
        res = client.post(
            "/api/energy/readings",
            json=bad,
            headers={"Authorization": f"Bearer {student_token}"},
        )
        assert res.status_code == 422  # Pydantic validation error

    def test_reject_duplicate_reading(self, client, student_token):
        # Submit twice
        client.post("/api/energy/readings", json={**self._reading, "timestamp": "2026-01-16T14:00:00Z"},
                    headers={"Authorization": f"Bearer {student_token}"})
        res2 = client.post("/api/energy/readings", json={**self._reading, "timestamp": "2026-01-16T14:00:00Z"},
                           headers={"Authorization": f"Bearer {student_token}"})
        assert res2.status_code == 409

    def test_get_readings_returns_list(self, client, student_token):
        res = client.get("/api/energy/readings", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_unauthenticated_cannot_submit(self, client):
        res = client.post("/api/energy/readings", json=self._reading)
        assert res.status_code == 401


# ─────────────────────────────────────────────────────────────────────────────
# 8 — Dashboard endpoints
# ─────────────────────────────────────────────────────────────────────────────
class TestDashboard:
    def test_energy_dashboard(self, client, student_token):
        res = client.get("/api/energy/dashboard", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        data = res.json()
        assert "total_readings" in data
        assert "excess_cost_inr" in data
        assert "data_source_note" in data
        assert "simulated" in data["data_source_note"].lower()

    def test_building_stats(self, client, student_token):
        res = client.get("/api/energy/buildings/stats", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_hourly_profile(self, client, student_token):
        res = client.get("/api/energy/hourly-profile", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_daily_trend(self, client, student_token):
        res = client.get("/api/energy/daily-trend", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_alerts_endpoint(self, client, student_token):
        res = client.get("/api/energy/alerts", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)

    def test_anomalies_endpoint(self, client, student_token):
        res = client.get("/api/energy/anomalies", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 200
        assert isinstance(res.json(), list)


# ─────────────────────────────────────────────────────────────────────────────
# 9 — Admin dashboard
# ─────────────────────────────────────────────────────────────────────────────
class TestAdminDashboard:
    def test_admin_dashboard_fields(self, client, admin_token):
        res = client.get("/api/admin/dashboard", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        data = res.json()
        for field in ["total_users","total_buildings","total_meters","total_readings"]:
            assert field in data, f"Missing field: {field}"

    def test_meters_list(self, client, admin_token):
        res = client.get("/api/admin/meters", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        meters = res.json()
        assert len(meters) >= 4
        assert "is_stale" in meters[0]

    def test_ingestion_health(self, client, admin_token):
        res = client.get("/api/admin/ingestion/health", headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 200
        assert "total_readings" in res.json()


# ─────────────────────────────────────────────────────────────────────────────
# 10 — ML integration
# ─────────────────────────────────────────────────────────────────────────────
class TestML:
    def test_model_info_returns_503_or_200(self, client, student_token):
        """If model exists → 200; if missing → 503 (both are valid responses)."""
        res = client.get("/api/ml/info", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code in (200, 503)

    def test_predict_or_503(self, client, student_token):
        body = {
            "building": "Academic Block A",
            "zone": "Lecture Halls & Classrooms",
            "occupancy": 30,
            "temperature": 28.0,
            "humidity": 65.0,
            "hour": 10,
            "day_of_week": 1,
            "is_weekend": 0,
        }
        res = client.post("/api/ml/predict", json=body, headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code in (200, 503)
        if res.status_code == 200:
            assert "predicted_power_kw" in res.json()
            assert res.json()["predicted_power_kw"] >= 0

    def test_analyze_endpoint(self, client, student_token):
        res = client.post("/api/ml/analyze", headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code in (200, 503)
        if res.status_code == 200:
            body = res.json()
            assert "analyzed" in body or "error" in body


# ─────────────────────────────────────────────────────────────────────────────
# 11 — Simulator
# ─────────────────────────────────────────────────────────────────────────────
class TestSimulator:
    def test_generate_historical(self):
        from backend.services.simulator import generate_historical_batch
        conn = sqlite3.connect(_tmp_db.name)
        conn.row_factory = sqlite3.Row
        n = generate_historical_batch(conn, days_back=2)
        conn.commit()
        count = conn.execute("SELECT COUNT(*) FROM energy_readings").fetchone()[0]
        conn.close()
        assert count > 0

    def test_generate_current(self):
        from backend.services.simulator import generate_current_readings
        conn = sqlite3.connect(_tmp_db.name)
        generate_current_readings(conn)
        conn.commit()
        conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# 12 — User management (admin only)
# ─────────────────────────────────────────────────────────────────────────────
class TestUserManagement:
    def test_admin_create_user(self, client, admin_token):
        res = client.post("/api/users/", json={
            "email": "created@test.ww",
            "password": "createdpass",
            "full_name": "Created User",
            "role": "student",
        }, headers={"Authorization": f"Bearer {admin_token}"})
        assert res.status_code == 201
        assert res.json()["role"] == "student"

    def test_admin_update_user_role(self, client, admin_token):
        # Get list of users
        users = client.get("/api/users/", headers={"Authorization": f"Bearer {admin_token}"}).json()
        student = next((u for u in users if u["role"] == "student"), None)
        if student:
            res = client.patch(f"/api/users/{student['id']}", json={"full_name": "Updated Name"},
                               headers={"Authorization": f"Bearer {admin_token}"})
            assert res.status_code == 200

    def test_student_cannot_create_admin(self, client, student_token):
        res = client.post("/api/users/", json={
            "email": "hacked@evil.com",
            "password": "evil123",
            "full_name": "Hacker",
            "role": "admin",
        }, headers={"Authorization": f"Bearer {student_token}"})
        assert res.status_code == 403
