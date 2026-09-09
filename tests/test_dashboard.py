"""
RED tests for dashboard summary endpoint — expect 404 until Wave 3 implements it.
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


def _register_and_login(client, email="dash@test.com"):
    """Helper flow: register user, login via form data, return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Dash User",
            "password": "secret123",
            "role": "manager",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": email, "password": "secret123"},
    )
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers


def test_dashboard_summary(client):
    headers = _register_and_login(client, email="dash_summary@test.com")
    resp = client.get("/api/dashboard/summary", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True
    expected_keys = {
        "total_vehicles",
        "active_vehicles",
        "total_routes",
        "active_routes",
        "pending_maintenance",
        "unread_alerts",
        "total_geofences",
    }
    assert expected_keys.issubset(set(body["data"].keys()))
    for key in expected_keys:
        assert isinstance(body["data"][key], int), f"{key} should be int, got {type(body['data'][key])}"


def test_dashboard_require_auth(client):
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 401
