"""
API-level tests: response envelope and JWT protection.

Uses FastAPI's TestClient with an overridden get_db dependency so no
database server is required.
"""
import pytest
from fastapi.testclient import TestClient

from app.core.database import Base, get_db
from app.main import app
from tests.conftest import test_engine, TestingSessionLocal


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


def test_register_returns_envelope(client):
    resp = client.post(
        "/api/auth/register",
        json={
            "email": "api@test.com",
            "name": "API Tester",
            "password": "secret123",
            "role": "manager",
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True
    assert body["data"]["email"] == "api@test.com"


def test_vehicles_require_auth(client):
    resp = client.get("/api/vehicles/")
    assert resp.status_code == 401


def test_routes_require_auth(client):
    resp = client.get("/api/routes/")
    assert resp.status_code == 401


def test_create_vehicle_with_jwt_sets_owner(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "owner@test.com",
            "name": "Fleet Owner",
            "password": "secret123",
            "role": "manager",
        },
    )
    user_id = reg.json()["data"]["id"]

    login = client.post(
        "/api/auth/login",
        data={"username": "owner@test.com", "password": "secret123"},
    )
    token = login.json()["data"]["access_token"]

    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "KA-01-AB-1234",
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": "TESTVIN12345",
        },
        headers=headers,
    )
    assert created.status_code == 201
    body = created.json()
    assert body["success"] is True
    assert body["data"]["owner_id"] == user_id
    assert body["message"] == "Vehicle created"