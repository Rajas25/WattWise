"""Quick admin + ML endpoint verification."""
import urllib.request
import urllib.error
import json

BASE = "http://localhost:8001"


def post(path, body, token=None):
    data = json.dumps(body).encode()
    req = urllib.request.Request(
        BASE + path, data=data,
        headers={"Content-Type": "application/json"}, method="POST"
    )
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def get(path, token=None):
    req = urllib.request.Request(BASE + path)
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


# Login as admin (created by test suite)
code, body = post("/api/auth/token", {"email": "admin@test.ww", "password": "adminpass123"})
print(f"Admin login: {code}")

if code != 200:
    print("Admin not found in wattwise.db. Run: python backend/create_admin.py")
else:
    token = body["access_token"]
    print(f"  Role: {body['role']}, Name: {body['full_name']}")

    # Run ML analysis
    code2, res = post("/api/ml/analyze", {}, token)
    print(f"ML analyze: {code2} -> {res}")

    # Admin dashboard
    code3, dash = get("/api/admin/dashboard", token)
    print(f"Admin dashboard ({code3}):")
    print(f"  users={dash.get('total_users')}, buildings={dash.get('total_buildings')}")
    print(f"  readings={dash.get('total_readings')}, anomalies={dash.get('total_anomalies')}")
    print(f"  waste_kwh={dash.get('total_waste_kwh')}, waste_inr={dash.get('total_waste_inr')}")

    # ML model info
    code4, info = get("/api/ml/info", token)
    print(f"ML model info ({code4}): {info.get('model_name', info.get('error'))}")

print("\nDone.")
