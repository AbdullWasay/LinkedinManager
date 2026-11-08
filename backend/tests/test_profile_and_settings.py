from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body
    assert body["db"] is True


def test_profile_seeded():
    res = client.get("/api/v1/profile")
    assert res.status_code == 200
    body = res.json()
    assert body["full_name"] == "Abdul Wasay"
    assert "React" in body["professional_background"]["skills"]
    assert "USA" in body["target_markets"]


def test_profile_update():
    res = client.put(
        "/api/v1/profile",
        json={"portfolio_url": "https://abdulwasaycodes.vercel.app/"},
    )
    assert res.status_code == 200
    assert res.json()["portfolio_url"].startswith("https://")


def test_settings_blocks_auto_send():
    res = client.patch("/api/v1/settings", json={"auto_send_enabled": True})
    assert res.status_code == 400


def test_emergency_stop():
    res = client.post("/api/v1/automation/emergency-stop")
    assert res.status_code == 200
    body = res.json()
    assert body["emergency_stop"] is True
    assert body["automation_paused"] is True
    # resume for other tests
    client.post("/api/v1/automation/resume")


def test_auth_status():
    res = client.get("/api/v1/auth/status")
    assert res.status_code == 200
    body = res.json()
    assert body["authenticated"] is True
    assert body["google_connected"] is False


def test_analytics_overview():
    res = client.get("/api/v1/analytics/overview")
    assert res.status_code == 200
    body = res.json()
    assert "jobs_discovered" in body
    assert "applications_by_stage" in body
