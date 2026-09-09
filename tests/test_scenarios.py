"""
Scenario tests against existing endpoints (auth, vehicles, routes).

S1: signup -> login -> vehicle list
S2: route lifecycle (plan -> start -> arrive -> complete)
S3: error cases (unauthorized, duplicate email, duplicate license plate)
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


def test_s1_signup_login_vehicle_list(client):
    # register s1@test.com
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "s1@test.com",
            "name": "S1 User",
            "password": "secret123",
            "role": "manager",
        },
    )
    assert reg.status_code == 201
    body = reg.json()
    assert body["success"] is True

    # login with form data
    login = client.post(
        "/api/auth/login",
        data={"username": "s1@test.com", "password": "secret123"},
    )
    assert login.status_code == 200
    login_body = login.json()
    assert login_body["success"] is True
    assert "access_token" in login_body["data"]
    assert login_body["data"]["access_token"]

    token = login_body["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # GET /api/vehicles/ with Bearer
    resp = client.get("/api/vehicles/", headers=headers)
    assert resp.status_code == 200
    v_body = resp.json()
    assert v_body["success"] is True
    assert "vehicles" in v_body["data"]
    assert isinstance(v_body["data"]["vehicles"], list)


def test_s2_route_lifecycle(client):
    # register + login as s2@test.com
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "s2@test.com",
            "name": "S2 User",
            "password": "secret123",
            "role": "manager",
        },
    )
    assert reg.status_code == 201
    assert reg.json()["success"] is True

    login = client.post(
        "/api/auth/login",
        data={"username": "s2@test.com", "password": "secret123"},
    )
    assert login.status_code == 200
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # create vehicle
    vehicle_resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "KA-03-S2-0001",
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": "TESTVINS2",
        },
        headers=headers,
    )
    assert vehicle_resp.status_code == 201
    v_body = vehicle_resp.json()
    assert v_body["success"] is True
    vehicle_id = v_body["data"]["id"]

    # plan route with 2 Bangalore stops
    route_resp = client.post(
        "/api/routes/",
        json={
            "vehicle_id": vehicle_id,
            "start_location": "Bangalore Start",
            "end_location": "Bangalore End",
            "stops": [
                {"sequence": 1, "latitude": 12.9716, "longitude": 77.5946},
                {"sequence": 2, "latitude": 12.9352, "longitude": 77.6245},
            ],
        },
        headers=headers,
    )
    assert route_resp.status_code == 201
    r_body = route_resp.json()
    assert r_body["success"] is True
    assert float(r_body["data"]["distance_km"]) > 0
    assert len(r_body["data"]["stops"]) >= 2

    route_id = r_body["data"]["id"]
    first_stop_id = r_body["data"]["stops"][0]["id"]

    # POST start -> in_progress
    start_resp = client.post(f"/api/routes/{route_id}/start", headers=headers)
    assert start_resp.status_code == 200
    s_body = start_resp.json()
    assert s_body["success"] is True
    assert s_body["data"]["status"] == "in_progress"

    # POST /stops/{first_stop_id}/arrive (actual path is /api/routes/stops/{id}/arrive)
    arrive_resp = client.post(f"/api/routes/stops/{first_stop_id}/arrive", headers=headers)
    # fallback if mounted at /api/stops per spec
    if arrive_resp.status_code == 404:
        arrive_resp = client.post(f"/api/stops/{first_stop_id}/arrive", headers=headers)
    assert arrive_resp.status_code == 200
    a_body = arrive_resp.json()
    assert a_body["success"] is True

    # POST complete -> completed
    complete_resp = client.post(f"/api/routes/{route_id}/complete", headers=headers)
    assert complete_resp.status_code == 200
    c_body = complete_resp.json()
    assert c_body["success"] is True
    assert c_body["data"]["status"] == "completed"


def test_s3_errors(client):
    # GET /api/vehicles/ without token -> 401
    no_auth = client.get("/api/vehicles/")
    assert no_auth.status_code == 401

    # register dup email twice -> second 400
    first = client.post(
        "/api/auth/register",
        json={
            "email": "dup@test.com",
            "name": "Dup User",
            "password": "secret123",
            "role": "manager",
        },
    )
    assert first.status_code == 201
    second = client.post(
        "/api/auth/register",
        json={
            "email": "dup@test.com",
            "name": "Dup User",
            "password": "secret123",
            "role": "manager",
        },
    )
    assert second.status_code == 400

    # create same license plate twice -> second 400
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "plate@test.com",
            "name": "Plate User",
            "password": "secret123",
            "role": "manager",
        },
    )
    assert reg.status_code == 201
    login = client.post(
        "/api/auth/login",
        data={"username": "plate@test.com", "password": "secret123"},
    )
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    v1 = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "KA-04-DUP-0001",
            "make": "Tata",
            "model": "Ace",
            "year": 2022,
            "vin": "DUPVIN0001",
        },
        headers=headers,
    )
    assert v1.status_code == 201
    assert v1.json()["success"] is True

    v2 = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "KA-04-DUP-0001",
            "make": "Tata",
            "model": "Ace",
            "year": 2022,
            "vin": "DUPVIN0002",
        },
        headers=headers,
    )
    assert v2.status_code == 400
