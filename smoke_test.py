"""Quick end-to-end smoke test against the running server on port 8001."""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8001"

def post_json(path, body):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())

def get_json(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


print("=" * 55)
print("  WattWise End-to-End Smoke Test")
print("=" * 55)

# 1. Health check
code, body = get_json("/api/health")
assert code == 200 and body["status"] == "healthy", f"FAIL health: {body}"
print(f"✅  /api/health → {body['status']}")

# 2. Register student
code, body = post_json("/api/auth/register", {
    "email": "smoke@test.ww", "password": "smoke1234", "full_name": "Smoke Test"
})
assert code in (201, 409), f"FAIL register: {code} {body}"
print(f"✅  /api/auth/register → {code} (201=created, 409=already exists)")

# 3. Login as student
code, body = post_json("/api/auth/token", {"email": "smoke@test.ww", "password": "smoke1234"})
assert code == 200, f"FAIL login: {code} {body}"
student_token = body["access_token"]
print(f"✅  /api/auth/token → role={body['role']}, name={body['full_name']}")

# 4. /me endpoint
code, me = get_json("/api/auth/me", student_token)
assert code == 200 and me["email"] == "smoke@test.ww"
assert "hashed_password" not in str(me)
print(f"✅  /api/auth/me → {me['email']} (no password in response)")

# 5. Student can see buildings
code, buildings = get_json("/api/energy/buildings", student_token)
assert code == 200 and len(buildings) >= 4
print(f"✅  /api/energy/buildings → {len(buildings)} buildings")

# 6. Student can see dashboard KPIs
code, kpi = get_json("/api/energy/dashboard", student_token)
assert code == 200 and "total_readings" in kpi
print(f"✅  /api/energy/dashboard → {kpi['total_readings']} readings, {kpi['waste_incidents']} waste events")

# 7. Student CANNOT access admin endpoint (403 expected)
code, body = get_json("/api/admin/dashboard", student_token)
assert code == 403, f"FAIL: student should get 403 on /api/admin/dashboard, got {code}"
print(f"✅  Student → /api/admin/dashboard → 403 Forbidden ✓")

# 8. Unauthenticated → 401
code, body = get_json("/api/energy/readings")
assert code == 401, f"FAIL: expected 401 without token, got {code}"
print(f"✅  No token → /api/energy/readings → 401 Unauthorized ✓")

# 9. Wrong password → 401
code, body = post_json("/api/auth/token", {"email": "smoke@test.ww", "password": "WRONG"})
assert code == 401
print(f"✅  Wrong password → 401 ✓")

# 10. Energy data carries simulated label
assert "simulated" in kpi.get("data_source_note", "").lower()
print(f"✅  data_source_note: '{kpi['data_source_note']}'")

print()
print("=" * 55)
print("  ALL SMOKE TESTS PASSED ✅")
print("=" * 55)
