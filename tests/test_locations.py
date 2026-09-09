"""
Location tests — Wave 2 RED contract.

All /api/locations/* endpoints are expected to 404 until Wave 3
implements the locations router. These tests are the contract.
"""

from tests.test_api import client  # noqa: F401 — pytest fixture import


def _register_and_login(client, email="loc@test.com"):
    """Register a user and return Bearer headers + token."""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Loc Tester",
            "password": "secret123",
            "role": "manager",
        },
    )
    login = client.post(
        "/api/auth/login",
        data={"username": email, "password": "secret123"},
    )
    assert login.status_code == 200, login.text
    token = login.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    return headers, token


def _create_vehicle(client, headers, suffix="LOC1"):
    """Create a vehicle and return its id."""
    resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": f"KA-01-LOC-{suffix}",
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": f"VINLOC{suffix}12345",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def test_record_location(client):
    headers, _ = _register_and_login(client, email="record@test.com")
    vehicle_id = _create_vehicle(client, headers, suffix="REC1")

    resp = client.post(
        "/api/locations/",
        json={
            "vehicle_id": vehicle_id,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "speed": 45.5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert set(body.keys()) == {"success", "data", "message"}
    assert body["success"] is True


def test_list_locations(client):
    headers, _ = _register_and_login(client, email="list@test.com")
    _create_vehicle(client, headers, suffix="LST1")

    resp = client.get("/api/locations/", headers=headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "locations" in body["data"]
    assert "total" in body["data"]
    assert isinstance(body["data"]["locations"], list)
    assert isinstance(body["data"]["total"], int)


def test_locations_require_auth(client):
    resp = client.get("/api/locations/")
    assert resp.status_code == 401


def test_latest_location(client):
    headers, _ = _register_and_login(client, email="latest@test.com")
    vehicle_id = _create_vehicle(client, headers, suffix="LAT1")

    # record a location first so latest has data
    created = client.post(
        "/api/locations/",
        json={
            "vehicle_id": vehicle_id,
            "latitude": 12.9716,
            "longitude": 77.5946,
            "speed": 30.0,
        },
        headers=headers,
    )
    assert created.status_code == 201

    resp = client.get(f"/api/locations/vehicle/{vehicle_id}/latest", headers=headers)
    assert resp.status_code == 200
