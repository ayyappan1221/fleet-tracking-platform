"""
Coverage floor tests — Task 8 of capstone-review2 plan.

Covers:
  (a) Vehicle duplicate plate → 400
  (b) Route plan with 1 stop → 422
  (c) Route plan with lat=200 → 422
  (d) 401-no-token on locations/dashboard/alerts/geofences/maintenance (5 tests)
  (e) Dashboard summary returns all 7 expected keys with int values
  (f) Happy-path locations POST → GET roundtrip
"""

from tests.test_api import client  # noqa: F401 — shared TestClient fixture


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _register_and_login(client, email="coverage@test.com"):
    """Register a user and return Bearer headers."""
    client.post(
        "/api/auth/register",
        json={
            "email": email,
            "name": "Coverage Tester",
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
    return {"Authorization": f"Bearer {token}"}


def _create_vehicle(client, headers, plate="KA-01-CFV-001", vin_suffix="CFV01"):
    """Create a vehicle and return its id."""
    resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": plate,
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": f"VIN{vin_suffix}12345",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


# ===== (a) Vehicle duplicate plate → 400 =====================================

def test_vehicle_duplicate_plate_returns_400(client):
    """Creating two vehicles with the same plate must fail with 400."""
    headers = _register_and_login(client, email="dup1@test.com")
    _create_vehicle(client, headers, plate="DUP-PLATE-1", vin_suffix="DP1")

    resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "DUP-PLATE-1",  # exact same case
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": "VINDUP1X12345",
        },
        headers=headers,
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


def test_vehicle_duplicate_plate_case_insensitive_400(client):
    """Duplicate check is case-insensitive (plates upper-normalize)."""
    headers = _register_and_login(client, email="dup2@test.com")
    _create_vehicle(client, headers, plate="CASE-PLATE-2", vin_suffix="CP2")

    resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": "case-plate-2",  # lower-case variant
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": "VINCASE2X12345",
        },
        headers=headers,
    )
    assert resp.status_code == 400, f"Expected 400, got {resp.status_code}: {resp.text}"


# ===== (b) Route plan with 1 stop → 422 ======================================

def test_route_plan_single_stop_returns_422(client):
    """Route with only 1 stop must fail (min_length=2 on stops)."""
    headers = _register_and_login(client, email="route1@test.com")
    vehicle_id = _create_vehicle(client, headers, plate="RT-1-STOP", vin_suffix="RS1")

    resp = client.post(
        "/api/routes/",
        json={
            "vehicle_id": vehicle_id,
            "stops": [
                {
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "sequence": 1,
                }
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ===== (c) Route plan with lat=200 → 422 =====================================

def test_route_plan_out_of_range_latitude_returns_422(client):
    """Stop latitude=200 exceeds ±90 bounds → 422."""
    headers = _register_and_login(client, email="route2@test.com")
    vehicle_id = _create_vehicle(client, headers, plate="RT-BADLAT", vin_suffix="RL1")

    resp = client.post(
        "/api/routes/",
        json={
            "vehicle_id": vehicle_id,
            "stops": [
                {
                    "latitude": 200.0,  # out of range (max 90)
                    "longitude": 77.5946,
                    "sequence": 1,
                },
                {
                    "latitude": 12.9716,
                    "longitude": 77.5946,
                    "sequence": 2,
                },
            ],
        },
        headers=headers,
    )
    assert resp.status_code == 422, f"Expected 422, got {resp.status_code}: {resp.text}"


# ===== (d) 401-no-token on each router ========================================

def test_locations_401_without_token(client):
    """GET /api/locations/ without auth → 401."""
    resp = client.get("/api/locations/")
    assert resp.status_code == 401


def test_dashboard_401_without_token(client):
    """GET /api/dashboard/summary without auth → 401."""
    resp = client.get("/api/dashboard/summary")
    assert resp.status_code == 401


def test_alerts_401_without_token(client):
    """GET /api/alerts/ without auth → 401."""
    resp = client.get("/api/alerts/")
    assert resp.status_code == 401


def test_geofences_401_without_token(client):
    """GET /api/geofences/ without auth → 401."""
    resp = client.get("/api/geofences/")
    assert resp.status_code == 401


def test_maintenance_401_without_token(client):
    """GET /api/maintenance/ without auth → 401."""
    resp = client.get("/api/maintenance/")
    assert resp.status_code == 401


# ===== (e) Dashboard summary returns all 7 keys with int values =============

def test_dashboard_summary_keys_and_types(client):
    """Dashboard summary must contain exactly 7 int-valued keys."""
    headers = _register_and_login(client, email="dash@test.com")

    resp = client.get("/api/dashboard/summary", headers=headers)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["success"] is True

    data = body["data"]
    expected_keys = {
        "total_vehicles",
        "active_vehicles",
        "total_routes",
        "active_routes",
        "pending_maintenance",
        "unread_alerts",
        "total_geofences",
    }
    assert set(data.keys()) == expected_keys, f"Missing keys: {expected_keys - set(data.keys())}"
    for key in expected_keys:
        assert isinstance(data[key], int), f"{key} should be int, got {type(data[key])}"


# ===== (f) Happy-path: locations POST → GET roundtrip ========================

def test_locations_post_get_roundtrip(client):
    """Create a vehicle, record a location, then retrieve it."""
    headers = _register_and_login(client, email="roundtrip@test.com")
    vehicle_id = _create_vehicle(client, headers, plate="RT-TRIP-1", vin_suffix="RP1")

    # POST a location
    post_resp = client.post(
        "/api/locations/",
        json={
            "vehicle_id": vehicle_id,
            "latitude": 13.0827,
            "longitude": 80.2707,
            "speed": 60.0,
            "heading": 45.0,
        },
        headers=headers,
    )
    assert post_resp.status_code == 201, post_resp.text
    loc_id = post_resp.json()["data"]["id"]

    # GET the list — our vehicle's location should appear
    list_resp = client.get(
        f"/api/locations/?vehicle_id={vehicle_id}", headers=headers
    )
    assert list_resp.status_code == 200
    locations = list_resp.json()["data"]["locations"]
    assert any(loc["id"] == loc_id for loc in locations), (
        f"Location {loc_id} not found in list"
    )

    # GET latest for this vehicle
    latest_resp = client.get(
        f"/api/locations/vehicle/{vehicle_id}/latest", headers=headers
    )
    assert latest_resp.status_code == 200
    latest = latest_resp.json()["data"]
    assert latest["latitude"] == 13.0827
    assert latest["longitude"] == 80.2707
