"""Intelligence features: behavior scoring, auto alerts, geofence breach,
maintenance due, issue reporting, fleet report."""
import json
from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import User
from app.schemas.geofence import GeofenceCreate
from app.schemas.location import LocationCreate
from app.schemas.maintenance import MaintenanceCreate
from app.schemas.route import RouteCreate, RouteStopCreate
from app.schemas.vehicle import VehicleCreate
from app.services import (
    alert_service,
    behavior_service,
    dashboard_service,
    geofence_service,
    location_service,
    maintenance_service,
    route_service,
    vehicle_service,
)
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


_uid = {"n": 0}


def _make_user(db: Session, role="manager") -> User:
    _uid["n"] += 1
    u = User(
        email=f"intel{_uid['n']}@test.com",
        name="Intel User",
        password_hash=hash_password("Secret123!"),
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_vehicle(db_session, owner_id, plate, vin):
    return vehicle_service.create_vehicle(
        db_session, owner_id,
        VehicleCreate(license_plate=plate, make="Tata", model="Ace", year=2021, vin=vin),
    )


def _make_route(db_session, vehicle_id, driver_id=None):
    return route_service.plan_route(
        db_session,
        RouteCreate(
            vehicle_id=vehicle_id, driver_id=driver_id,
            stops=[
                RouteStopCreate(sequence=1, latitude=12.97, longitude=77.59),
                RouteStopCreate(sequence=2, latitude=12.93, longitude=77.62),
            ],
        ),
    )


def _register(client, email, role="driver"):
    r = client.post("/api/auth/register", json={"email": email, "name": "I User", "password": "Secret123!", "role": role})
    if r.status_code == 201:
        otp = r.json()["data"]["dev_otp"]
        v = client.post(
            "/api/auth/verify-signup",
            json={"email": email, "code": otp, "purpose": "signup_verify"},
        )
        assert v.status_code == 200, v.text
    return r


def _login(client, email):
    r = client.post("/api/auth/login", data={"username": email, "password": "Secret123!"})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['data']['access_token']}"}


def _bootstrap_manager(client, email="intboss@test.com"):
    r = _register(client, email, role="manager")
    assert r.status_code == 201, r.text
    return _login(client, email)


class TestBehaviorScoring:
    def test_clean_driving_scores_100(self, db_session):
        out = behavior_service.compute_score_from_speeds([40.0, 45.0, 50.0, 48.0])
        assert out["score"] == 100
        assert out["speeding_events"] == 0

    def test_speeding_harsh_brake_rapid_accel_lower_score(self, db_session):
        out = behavior_service.compute_score_from_speeds([40.0, 120.0, 50.0, 90.0], speed_limit=100)
        assert out["speeding_events"] == 1
        assert out["harsh_braking_events"] >= 1
        assert out["rapid_acceleration_events"] >= 1
        assert 0 <= out["score"] < 100

    def test_compute_route_score_persists(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-BS-01", "VINBS0000001")
        r = _make_route(db_session, v.id, driver_id=u.id)
        for speed in (30.0, 35.0, 120.0):
            location_service.record_location(
                db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=speed))
        res = behavior_service.compute_route_score(db_session, r.id)
        assert 0 <= res["score"] <= 100
        assert res["speeding_events"] >= 1
        assert db_session.query(route_service.Route).filter_by(id=r.id).first().score == res["score"]

    def test_compute_driver_score(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-BS-02", "VINBS0000002")
        _make_route(db_session, v.id, driver_id=u.id)
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.9, longitude=77.5, speed=20.0))
        res = behavior_service.compute_driver_score(db_session, u.id)
        assert res["driver_id"] == u.id
        assert res["score"] == 100


class TestSpeedingAutoAlert:
    def test_speeding_creates_alert(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SP-01", "VINSP0000001")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.9, longitude=77.5, speed=150.0))
        alerts, total = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert total >= 1
        assert any(a.type in ("speed", "speeding") for a in alerts)

    def test_speeding_throttled_within_5min(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SP-02", "VINSP0000002")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.9, longitude=77.5, speed=150.0))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.91, longitude=77.51, speed=160.0))
        _, total = alert_service.list_alerts(db_session, vehicle_id=v.id)
        speeding = [a for a in alert_service.list_alerts(db_session, vehicle_id=v.id)[0] if a.type in ("speed", "speeding")]
        assert len(speeding) == 1
        assert total >= 1

    def test_normal_speed_no_alert(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SP-03", "VINSP0000003")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.9, longitude=77.5, speed=40.0))
        _, total = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert total == 0


class TestGeofenceBreach:
    def test_breach_creates_alert(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-GF-01", "VINGF0000001")
        geofence_service.create_geofence(
            db_session, u.id,
            GeofenceCreate(name="Small Zone", type="inclusion",
                           coordinates=json.dumps({"bbox": [12.9, 77.5, 13.0, 77.6]})))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=20.0, longitude=80.0, speed=10.0))
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert any(a.type == "geofence" for a in alerts)

    def test_inside_no_breach(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-GF-02", "VINGF0000002")
        geofence_service.create_geofence(
            db_session, u.id,
            GeofenceCreate(name="Big Zone", type="inclusion",
                           coordinates=json.dumps({"bbox": [12.0, 77.0, 14.0, 78.0]})))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=10.0))
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert not any(a.type == "geofence" for a in alerts)

    def test_exclusion_inside_breach(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-GF-03", "VINGF0000003")
        geofence_service.create_geofence(
            db_session, u.id,
            GeofenceCreate(name="NoGo", type="exclusion",
                           coordinates=json.dumps({"bbox": [12.0, 77.0, 14.0, 78.0]})))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=10.0))
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert any(a.type == "geofence" for a in alerts)


class TestMaintenanceDue:
    def test_due_soon_creates_alert(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-MD-01", "VINMD0000001")
        maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="oil_change", status="scheduled",
                                          due_date=date.today() + timedelta(days=3)))
        created = maintenance_service.check_maintenance_due(db_session)
        assert len(created) == 1
        assert created[0].type == "maintenance"

    def test_far_future_no_alert(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-MD-02", "VINMD0000002")
        maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="tire", status="scheduled",
                                          due_date=date.today() + timedelta(days=60)))
        assert maintenance_service.check_maintenance_due(db_session) == []

    def test_no_duplicate_due_alerts(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-MD-03", "VINMD0000003")
        maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="inspection", status="scheduled",
                                          due_date=date.today() + timedelta(days=2)))
        assert len(maintenance_service.check_maintenance_due(db_session)) == 1
        assert len(maintenance_service.check_maintenance_due(db_session)) == 0

    def test_report_issue_creates_pending(self, db_session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-MD-04", "VINMD0000004")
        rec = maintenance_service.report_issue(db_session, v.id, "Brake noise", "repair")
        assert rec.status == "pending"
        assert "Brake noise" in (rec.notes or "")


class TestEndpoints:
    def test_route_score_endpoint(self, client):
        mgr = _bootstrap_manager(client, "scoreboss@test.com")
        d = _login(client, "scoreboss@test.com") if False else None
        drv = _register(client, "scoredrv@test.com", role="driver")
        assert drv.status_code == 201
        dh = _login(client, "scoredrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-E1-01", "make": "T", "model": "M", "year": 2021, "vin": "VINE10000001"}, headers=dh)
        assert v.status_code == 201, v.text
        vid = v.json()["data"]["id"]
        r = client.post("/api/routes/", json={"vehicle_id": vid, "stops": [{"sequence": 1, "latitude": 12.97, "longitude": 77.59}, {"sequence": 2, "latitude": 12.93, "longitude": 77.62}]}, headers=dh)
        assert r.status_code == 201, r.text
        rid = r.json()["data"]["id"]
        client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.97, "longitude": 77.59, "speed": 150.0}, headers=dh)
        s = client.get(f"/api/routes/{rid}/score", headers=dh)
        assert s.status_code == 200, s.text
        assert s.json()["data"]["score"] < 100
        assert client.get("/api/routes/999999/score", headers=dh).status_code == 404
        other = _register(client, "scoreother@test.com", role="driver")
        oh = _login(client, "scoreother@test.com")
        assert client.get(f"/api/routes/{rid}/score", headers=oh).status_code == 403
        bad = client.get("/api/routes/0/score", headers=mgr)
        assert bad.status_code == 400

    def test_driver_me_score(self, client):
        _bootstrap_manager(client, "meboss@test.com")
        _register(client, "medrv@test.com", role="driver")
        dh = _login(client, "medrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-E1-02", "make": "T", "model": "M", "year": 2021, "vin": "VINE10000002"}, headers=dh)
        vid = v.json()["data"]["id"]
        client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.97, "longitude": 77.59, "speed": 30.0}, headers=dh)
        s = client.get("/api/drivers/me/score", headers=dh)
        assert s.status_code == 200, s.text
        assert "score" in s.json()["data"]
        assert client.get("/api/drivers/me/score").status_code in (401, 403)

    def test_speeding_auto_alert_via_api(self, client):
        _bootstrap_manager(client, "spdboss@test.com")
        _register(client, "spddrv@test.com", role="driver")
        dh = _login(client, "spddrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-E1-03", "make": "T", "model": "M", "year": 2021, "vin": "VINE10000003"}, headers=dh)
        vid = v.json()["data"]["id"]
        r1 = client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.9, "longitude": 77.5, "speed": 150.0}, headers=dh)
        assert r1.status_code == 201, r1.text
        r2 = client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.91, "longitude": 77.51, "speed": 160.0}, headers=dh)
        assert r2.status_code == 201
        al = client.get(f"/api/alerts/?vehicle_id={vid}", headers=dh).json()["data"]["alerts"]
        speeding = [a for a in al if a["type"] in ("speed", "speeding")]
        assert len(speeding) == 1

    def test_check_due_manager_only(self, client):
        mgr = _bootstrap_manager(client, "dueboss@test.com")
        _register(client, "duedrv@test.com", role="driver")
        dh = _login(client, "duedrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-E1-04", "make": "T", "model": "M", "year": 2021, "vin": "VINE10000004"}, headers=dh)
        vid = v.json()["data"]["id"]
        due = (date.today() + timedelta(days=3)).isoformat()
        c = client.post("/api/maintenance/", json={"vehicle_id": vid, "type": "oil_change", "status": "scheduled", "due_date": due}, headers=dh)
        assert c.status_code == 201, c.text
        assert client.post("/api/maintenance/check-due", headers=dh).status_code == 403
        ok = client.post("/api/maintenance/check-due", headers=mgr)
        assert ok.status_code == 200, ok.text
        assert ok.json()["data"]["created"] >= 1

    def test_issue_report(self, client):
        _bootstrap_manager(client, "issboss@test.com")
        _register(client, "issdrv@test.com", role="driver")
        dh = _login(client, "issdrv@test.com")
        _register(client, "issdrv2@test.com", role="driver")
        dh2 = _login(client, "issdrv2@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-E1-05", "make": "T", "model": "M", "year": 2021, "vin": "VINE10000005"}, headers=dh)
        vid = v.json()["data"]["id"]
        ok = client.post("/api/maintenance/report-issue", json={"vehicle_id": vid, "description": "Engine knocking"}, headers=dh)
        assert ok.status_code == 201, ok.text
        assert ok.json()["data"]["status"] == "pending"
        assert client.post("/api/maintenance/report-issue", json={"vehicle_id": vid, "description": "x"}, headers=dh2).status_code == 403
        bad = client.post("/api/maintenance/report-issue", json={"vehicle_id": 0, "description": "x"}, headers=dh)
        assert bad.status_code == 400
        missing = client.post("/api/maintenance/report-issue", json={"vehicle_id": vid, "description": ""}, headers=dh)
        assert missing.status_code == 400

    def test_report_endpoint_auth(self, client):
        mgr = _bootstrap_manager(client, "repboss@test.com")
        _register(client, "repdrv@test.com", role="driver")
        dh = _login(client, "repdrv@test.com")
        assert client.get("/api/dashboard/report?days=30").status_code in (401, 403)
        assert client.get("/api/dashboard/report?days=30", headers=dh).status_code == 403
        ok = client.get("/api/dashboard/report?days=30", headers=mgr)
        assert ok.status_code == 200, ok.text
        data = ok.json()["data"]
        for key in ("trips", "distance_km", "alerts_by_type", "maintenance_by_status", "avg_driver_score"):
            assert key in data
