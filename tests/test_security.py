"""Review-II security tests: registration hardening, ownership, validation."""

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
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def _register(client, email, role="driver"):
    return client.post(
        "/api/auth/register",
        json={"email": email, "name": "Sec User", "password": "Secret123!", "role": role},
    )


def _login(client, email):
    login = client.post(
        "/api/auth/login", data={"username": email, "password": "Secret123!"}
    )
    assert login.status_code == 200, login.text
    return {"Authorization": f"Bearer {login.json()['data']['access_token']}"}


def _verify(client, email, reg):
    otp = reg.json()["data"]["dev_otp"]
    verify = client.post(
        "/api/auth/verify-signup",
        json={"email": email, "code": otp, "purpose": "signup_verify"},
    )
    assert verify.status_code == 200, verify.text


def _bootstrap_manager(client, email="boss@test.com"):
    resp = _register(client, email, role="manager")
    assert resp.status_code == 201, resp.text
    assert resp.json()["data"]["role"] == "manager"
    _verify(client, email, resp)
    return _login(client, email)


def _driver(client, email):
    resp = _register(client, email, role="driver")
    assert resp.status_code == 201, resp.text
    _verify(client, email, resp)
    return _login(client, email)


def _vehicle(client, headers, plate, vin):
    resp = client.post(
        "/api/vehicles/",
        json={
            "license_plate": plate,
            "make": "Tata",
            "model": "Ace",
            "year": 2021,
            "vin": vin,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["data"]["id"]


def test_privileged_self_registration_forbidden(client):
    _bootstrap_manager(client)
    resp = _register(client, "evil@test.com", role="manager")
    assert resp.status_code == 403


def test_driver_registration_allowed_after_bootstrap(client):
    _bootstrap_manager(client)
    resp = _register(client, "drv@test.com", role="driver")
    assert resp.status_code == 201
    assert resp.json()["data"]["role"] == "driver"


def test_cross_user_vehicle_forbidden(client):
    mgr = _bootstrap_manager(client)
    ha = _driver(client, "a@test.com")
    hb = _driver(client, "b@test.com")
    vid = _vehicle(client, ha, "KA-01-SEC-01", "VINSEC000001")

    assert client.get(f"/api/vehicles/{vid}", headers=hb).status_code == 403
    assert (
        client.patch(f"/api/vehicles/{vid}", json={"make": "X"}, headers=hb).status_code
        == 403
    )
    assert client.delete(f"/api/vehicles/{vid}", headers=hb).status_code == 403

    body = client.get("/api/vehicles/", headers=hb).json()["data"]
    assert all(v["id"] != vid for v in body["vehicles"])

    assert client.get(f"/api/vehicles/{vid}", headers=mgr).status_code == 200


def test_cross_user_route_forbidden(client):
    _bootstrap_manager(client)
    ha = _driver(client, "ra@test.com")
    hb = _driver(client, "rb@test.com")
    vid = _vehicle(client, ha, "KA-01-SEC-02", "VINSEC000002")
    planned = client.post(
        "/api/routes/",
        json={
            "vehicle_id": vid,
            "stops": [
                {"sequence": 1, "latitude": 12.97, "longitude": 77.59},
                {"sequence": 2, "latitude": 12.93, "longitude": 77.62},
            ],
        },
        headers=ha,
    )
    assert planned.status_code == 201, planned.text
    rid = planned.json()["data"]["id"]
    stop_id = planned.json()["data"]["stops"][0]["id"]

    assert client.get(f"/api/routes/{rid}", headers=hb).status_code == 403
    assert client.post(f"/api/routes/{rid}/start", headers=hb).status_code == 403
    assert (
        client.post(f"/api/routes/stops/{stop_id}/arrive", headers=hb).status_code
        == 403
    )

    assert client.post(f"/api/routes/{rid}/start", headers=ha).status_code == 200
    assert client.post(f"/api/routes/{rid}/complete", headers=ha).status_code == 200


def test_cross_user_location_forbidden(client):
    _bootstrap_manager(client)
    ha = _driver(client, "la@test.com")
    hb = _driver(client, "lb@test.com")
    vid = _vehicle(client, ha, "KA-01-SEC-03", "VINSEC000003")
    created = client.post(
        "/api/locations/",
        json={"vehicle_id": vid, "latitude": 12.97, "longitude": 77.59},
        headers=ha,
    )
    assert created.status_code == 201

    assert (
        client.post(
            "/api/locations/",
            json={"vehicle_id": vid, "latitude": 12.97, "longitude": 77.59},
            headers=hb,
        ).status_code
        == 403
    )
    assert (
        client.get(f"/api/locations/vehicle/{vid}/latest", headers=hb).status_code
        == 403
    )
    assert (
        client.get(f"/api/locations/vehicle/{vid}/latest", headers=ha).status_code
        == 200
    )


def test_cross_user_alert_forbidden(client):
    _bootstrap_manager(client)
    ha = _driver(client, "aa@test.com")
    hb = _driver(client, "ab@test.com")
    vid = _vehicle(client, ha, "KA-01-SEC-04", "VINSEC000004")
    created = client.post(
        "/api/alerts/",
        json={
            "vehicle_id": vid,
            "type": "speed",
            "severity": "warning",
            "message": "too fast",
        },
        headers=ha,
    )
    assert created.status_code == 201
    aid = created.json()["data"]["id"]

    assert client.patch(f"/api/alerts/{aid}/read", headers=hb).status_code == 403
    body = client.get("/api/alerts/", headers=hb).json()["data"]
    assert all(a["id"] != aid for a in body["alerts"])
    assert client.patch(f"/api/alerts/{aid}/read", headers=ha).status_code == 200


def test_cross_user_maintenance_forbidden(client):
    _bootstrap_manager(client)
    ha = _driver(client, "ma@test.com")
    hb = _driver(client, "mb@test.com")
    vid = _vehicle(client, ha, "KA-01-SEC-05", "VINSEC000005")
    created = client.post(
        "/api/maintenance/",
        json={"vehicle_id": vid, "type": "oil_change", "status": "scheduled"},
        headers=ha,
    )
    assert created.status_code == 201
    mid = created.json()["data"]["id"]

    assert (
        client.patch(
            f"/api/maintenance/{mid}", json={"status": "completed"}, headers=hb
        ).status_code
        == 403
    )
    body = client.get("/api/maintenance/", headers=hb).json()["data"]
    assert all(r["id"] != mid for r in body["maintenance"])
    assert (
        client.patch(
            f"/api/maintenance/{mid}", json={"status": "in_progress"}, headers=ha
        ).status_code
        == 200
    )


def test_geofence_ownership_and_delete_lifecycle(client):
    mgr = _bootstrap_manager(client)
    ha = _driver(client, "ga@test.com")
    hb = _driver(client, "gb@test.com")
    payload = {
        "name": "Zone A",
        "type": "inclusion",
        "coordinates": "POLYGON((12.97 77.59, 12.98 77.60, 12.96 77.61, 12.97 77.59))",
    }
    gid = client.post("/api/geofences/", json=payload, headers=ha).json()["data"]["id"]

    assert (
        client.patch(f"/api/geofences/{gid}", json={"name": "Hijack"}, headers=hb).status_code
        == 403
    )
    assert client.delete(f"/api/geofences/{gid}", headers=hb).status_code == 403
    assert client.delete(f"/api/geofences/{gid}", headers=mgr).status_code == 200
    assert client.delete(f"/api/geofences/{gid}", headers=mgr).status_code == 404

    gid2 = client.post("/api/geofences/", json=payload, headers=ha).json()["data"]["id"]
    assert client.delete(f"/api/geofences/{gid2}", headers=ha).status_code == 200


def test_invalid_payloads_rejected(client):
    mgr = _bootstrap_manager(client)
    vid = _vehicle(client, mgr, "KA-01-SEC-06", "VINSEC000006")

    bad_geo = client.post(
        "/api/locations/",
        json={"vehicle_id": vid, "latitude": 200.0, "longitude": 77.59},
        headers=mgr,
    )
    assert bad_geo.status_code == 422

    bad_status = client.patch(
        f"/api/vehicles/{vid}", json={"status": "flying"}, headers=mgr
    )
    assert bad_status.status_code == 422

    weak = client.post(
        "/api/auth/register",
        json={"email": "weak@test.com", "name": "W", "password": "123", "role": "driver"},
    )
    assert weak.status_code == 422

    assert client.get("/api/vehicles/0", headers=mgr).status_code == 400
    assert client.get("/api/vehicles/999999", headers=mgr).status_code == 404

def test_dashboard_summary_scoped_to_non_manager(client):
    mgr = _bootstrap_manager(client)
    ha = _driver(client, 'da@test.com')
    hb = _driver(client, 'db@test.com')
    _vehicle(client, ha, 'KA-01-SC-01', 'VINSC0000001')
    _vehicle(client, hb, 'KA-01-SC-02', 'VINSC0000002')
    sa = client.get('/api/dashboard/summary', headers=ha).json()['data']
    assert sa['total_vehicles'] == 1
    sb = client.get('/api/dashboard/summary', headers=hb).json()['data']
    assert sb['total_vehicles'] == 1
    sm = client.get('/api/dashboard/summary', headers=mgr).json()['data']
    assert sm['total_vehicles'] == 2

def test_vehicle_score_endpoint_access(client):
    mgr = _bootstrap_manager(client)
    ha = _driver(client, 'sa@test.com')
    hb = _driver(client, 'sb@test.com')
    vid = _vehicle(client, ha, 'KA-01-SC-11', 'VINSC0000011')
    ok = client.get(f'/api/vehicles/{vid}/score', headers=ha)
    assert ok.status_code == 200, ok.text
    assert 'score' in ok.json()['data']
    assert client.get(f'/api/vehicles/{vid}/score', headers=hb).status_code == 403
    assert client.get(f'/api/vehicles/{vid}/score', headers=mgr).status_code == 200
    assert client.get('/api/vehicles/999999/score', headers=mgr).status_code == 404
