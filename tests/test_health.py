from datetime import datetime


def test_health_returns_ok(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "timestamp" in body


def test_health_timestamp_is_valid_iso(client):
    resp = client.get("/api/health")
    ts = resp.json()["timestamp"]
    parsed = datetime.fromisoformat(ts)
    assert parsed.year >= 2024
