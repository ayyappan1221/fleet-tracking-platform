"""
RED tests for /api/alerts/* endpoints.

These MUST fail with 404 until Wave 3 implements the alerts router.
Reuses the client fixture from tests/test_api.py and matches the import
line from tests/test_scenarios.py exactly.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from tests.conftest import TestingSessionLocal, test_engine


@pytest.fixture
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def _auth_headers(client, email="alert@test.com"):
    """Helper: register + login via form data, return Bearer headers."""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Alert Tester",
            "password": "secret123",
            "role": "manager",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": email, "password": "secret123"},
    )
    token = login.json()["data"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def _create_vehicle(client, headers):
    """Helper: create a vehicle (optional for alert tests, used for vehicle_id)."""
    resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "KA-01-ALERT-0001",
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": "ALERTVIN0001",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    return resp.json()["data"]["id"]


def test_create_alert(client):
    headers = _auth_headers(client, email="alert-create@test.com")
    vehicle_id = _create_vehicle(client, headers)

    resp = client.post(
        "/api/alerts/",
        json={
            "vehicle_id": vehicle_id,
            "type": "speed",
            "severity": "warning",
            "message": "Vehicle exceeded speed limit",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True


def test_list_alerts(client):
    headers = _auth_headers(client, email="alert-list@test.com")
    vehicle_id = _create_vehicle(client, headers)

    # ensure at least one alert exists
    client.post(
        "/api/alerts/",
        json={
            "vehicle_id": vehicle_id,
            "type": "geofence",
            "severity": "info",
            "message": "Vehicle entered geofence",
        },
        headers=headers,
    )

    resp = client.get("/api/alerts/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True
    assert "alerts" in body["data"]
    assert isinstance(body["data"]["alerts"], list)
    assert "total" in body["data"]


def test_alerts_require_auth(client):
    resp = client.get("/api/alerts/")
    assert resp.status_code == 401


def test_mark_alert_read(client):
    headers = _auth_headers(client, email="alert-read@test.com")
    vehicle_id = _create_vehicle(client, headers)

    created = client.post(
        "/api/alerts/",
        json={
            "vehicle_id": vehicle_id,
            "type": "low_fuel",
            "severity": "critical",
            "message": "Fuel level critically low",
        },
        headers=headers,
    )
    assert created.status_code == 201
    alert_id = created.json()["data"]["id"]

    resp = client.patch(f"/api/alerts/{alert_id}/read", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True
