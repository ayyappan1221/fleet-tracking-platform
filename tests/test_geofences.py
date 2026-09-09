"""
RED tests for geofences endpoints — expect 404 until Wave 3 implements router.
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


def _register_and_login(client, email="geo@test.com"):
    """Helper flow: register user, login via form data, return auth headers."""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Geo User",
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


def test_create_geofence(client):
    headers = _register_and_login(client, email="geo_create@test.com")
    resp = client.post(
        "/api/geofences/",
        json={
            "name": "Warehouse Zone",
            "type": "inclusion",
            "coordinates": "POLYGON((12.97 77.59, 12.98 77.60, 12.96 77.61, 12.97 77.59))",
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True
    assert body["data"]["name"] == "Warehouse Zone"
    assert body["data"]["type"] == "inclusion"
    # owner_id is set from JWT, not from request body — verify it exists
    assert "owner_id" in body["data"]
    assert "id" in body["data"]


def test_list_geofences(client):
    headers = _register_and_login(client, email="geo_list@test.com")
    # create one so list is non-empty
    client.post(
        "/api/geofences/",
        json={
            "name": "List Zone",
            "type": "inclusion",
            "coordinates": "POLYGON((12.97 77.59, 12.98 77.60, 12.96 77.61, 12.97 77.59))",
        },
        headers=headers,
    )
    resp = client.get("/api/geofences/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "geofences" in body["data"]
    assert "total" in body["data"]
    assert isinstance(body["data"]["geofences"], list)
    assert isinstance(body["data"]["total"], int)


def test_geofences_require_auth(client):
    resp = client.get("/api/geofences/")
    assert resp.status_code == 401


def test_update_geofence(client):
    headers = _register_and_login(client, email="geo_update@test.com")
    created = client.post(
        "/api/geofences/",
        json={
            "name": "Old Name",
            "type": "inclusion",
            "coordinates": "POLYGON((12.97 77.59, 12.98 77.60, 12.96 77.61, 12.97 77.59))",
        },
        headers=headers,
    )
    assert created.status_code == 201
    geofence_id = created.json()["data"]["id"]

    resp = client.patch(
        f"/api/geofences/{geofence_id}",
        json={"name": "New Name"},
        headers=headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["name"] == "New Name"
