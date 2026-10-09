"""Top-class fleet features: fuel tracking, idle detection, inspections,
cost + utilization KPIs, and CSV exports."""
import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models import User
from app.schemas.fuel import FuelCreate
from app.schemas.inspection import InspectionCreate
from app.schemas.location import LocationCreate
from app.schemas.maintenance import MaintenanceCreate
from app.schemas.route import RouteCreate, RouteStopCreate
from app.schemas.vehicle import VehicleCreate
from app.services import (
    alert_service,
    dashboard_service,
    fuel_service,
    inspection_service,
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
        email=f"top{_uid['n']}@test.com",
        name="Top User",
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


def _register(client, email, role="driver"):
    r = client.post("/api/auth/register", json={"email": email, "name": "T User", "password": "Secret123!", "role": role})
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


def _bootstrap_manager(client, email="topboss@test.com"):
    r = _register(client, email, role="manager")
    assert r.status_code == 201, r.text
    return _login(client, email)


class TestFuelService:
    def test_log_and_list(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-FU-01", "VINFU0000001")
        f = fuel_service.log_fill(
            db_session, FuelCreate(vehicle_id=v.id, liters=40.0, cost=4000.0, odometer_km=1000.0))
        assert f.id is not None
        logs, total = fuel_service.list_for_vehicle(db_session, vehicle_id=v.id)
        assert total == 1
        assert logs[0].liters == 40.0

    def test_log_fill_missing_vehicle(self, db_session):
        with pytest.raises(ValueError):
            fuel_service.log_fill(
                db_session, FuelCreate(vehicle_id=999999, liters=10.0, cost=100.0, odometer_km=500.0))

    def test_efficiency_math(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-FU-02", "VINFU0000002")
        # 500 km on 50 L -> 10 km/L; 400 km on 50 L -> 8 km/L
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=1000.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5500.0, odometer_km=1500.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=6000.0, odometer_km=1900.0))
        stats = fuel_service.efficiency_stats(db_session, v.id)
        assert stats["fills"] == 3
        assert stats["total_km"] == 900.0
        assert stats["total_liters"] == 150.0
        assert stats["km_per_liter"] == pytest.approx(900.0 / 100.0)
        assert stats["cost_per_km"] == pytest.approx(16500.0 / 900.0, abs=0.01)

    def test_efficiency_single_fill_no_intervals(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-FU-03", "VINFU0000003")
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=30.0, cost=3000.0, odometer_km=700.0))
        stats = fuel_service.efficiency_stats(db_session, v.id)
        assert stats["fills"] == 1
        assert stats["km_per_liter"] is None
        assert stats["cost_per_km"] is None

    def test_efficiency_drop_creates_alert(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-FU-04", "VINFU0000004")
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=1000.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=1500.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=2000.0))
        # Latest: 250 km on 50 L = 5 km/L vs prior avg 10 km/L -> 50% drop
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=2250.0))
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        fuel_alerts = [a for a in alerts if a.type == "fuel"]
        assert len(fuel_alerts) == 1
        assert fuel_alerts[0].severity == "warning"

    def test_efficiency_drop_throttled(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-FU-05", "VINFU0000005")
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=1000.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=1500.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=2000.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=2250.0))
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=60.0, cost=6000.0, odometer_km=2300.0))
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert len([a for a in alerts if a.type == "fuel"]) == 1

    def test_no_drop_no_alert(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-FU-06", "VINFU0000006")
        for odo in (1000.0, 1500.0, 2000.0, 2500.0):
            fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=odo))
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert not [a for a in alerts if a.type == "fuel"]


class TestIdleDetection:
    def test_idle_event_recorded(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-ID-01", "VINID0000001")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=30.0))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.9701, longitude=77.5901, speed=0.5))
        days = location_service.idle_days(db_session, v.id, days=7)
        assert len(days) == 1
        assert days[0]["idle_minutes"] >= 0
        assert "date" in days[0]

    def test_moving_no_idle(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-ID-02", "VINID0000002")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=30.0))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.98, longitude=77.60, speed=40.0))
        assert location_service.idle_days(db_session, v.id, days=7) == []

    def test_far_coords_no_idle(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-ID-03", "VINID0000003")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=30.0))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=13.50, longitude=78.00, speed=1.0))
        assert location_service.idle_days(db_session, v.id, days=7) == []


class TestInspections:
    def test_passed_no_alert(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-IN-01", "VININ0000001")
        rec = inspection_service.create_inspection(
            db_session, InspectionCreate(vehicle_id=v.id, type="pre_trip", passed=True), inspector_id=u.id)
        assert rec.passed is True
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert not [a for a in alerts if a.type == "maintenance" and a.severity == "high"]

    def test_failed_creates_high_alert(self, db_session):
        u = _make_user(db_session, role="driver")
        v = _make_vehicle(db_session, u.id, "KA-01-IN-02", "VININ0000002")
        rec = inspection_service.create_inspection(
            db_session, InspectionCreate(vehicle_id=v.id, type="post_trip", passed=False, notes="Brake worn"),
            inspector_id=u.id)
        assert rec.passed is False
        alerts, _ = alert_service.list_alerts(db_session, vehicle_id=v.id)
        high = [a for a in alerts if a.type == "maintenance" and a.severity == "high"]
        assert len(high) == 1

    def test_missing_vehicle(self, db_session):
        u = _make_user(db_session, role="driver")
        with pytest.raises(ValueError):
            inspection_service.create_inspection(
                db_session, InspectionCreate(vehicle_id=999999, type="pre_trip", passed=True),
                inspector_id=u.id)


class TestReportKpis:
    def test_report_has_new_keys(self, db_session):
        u = _make_user(db_session, role="manager")
        v = _make_vehicle(db_session, u.id, "KA-01-RP-01", "VINRP0000001")
        route = route_service.plan_route(
            db_session,
            RouteCreate(
                vehicle_id=v.id, driver_id=u.id,
                stops=[RouteStopCreate(sequence=1, latitude=12.97, longitude=77.59),
                       RouteStopCreate(sequence=2, latitude=12.93, longitude=77.62)]),
        )
        route.distance_km = 100.0
        db_session.commit()
        fuel_service.log_fill(db_session, FuelCreate(vehicle_id=v.id, liters=50.0, cost=5000.0, odometer_km=1000.0))
        rec = maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="repair", status="scheduled", cost=2000.0))
        from app.schemas.maintenance import MaintenanceUpdate
        maintenance_service.update_maintenance(
            db_session, rec.id, MaintenanceUpdate(status="completed"))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97, longitude=77.59, speed=30.0))
        report = dashboard_service.get_report(db_session, days=30)
        for key in ("fuel_cost_total", "fuel_liters_total", "maintenance_cost_total",
                    "cost_per_km", "utilization", "on_time_rate"):
            assert key in report, f"missing {key}"
        assert report["fuel_cost_total"] == 5000.0
        assert report["fuel_liters_total"] == 50.0
        assert report["maintenance_cost_total"] == 2000.0
        assert report["cost_per_km"] == pytest.approx(7000.0 / 100.0)
        assert report["utilization"] == 100.0

    def test_report_zero_distance_guards(self, db_session):
        report = dashboard_service.get_report(db_session, days=30)
        assert report["cost_per_km"] is None
        assert report["on_time_rate"] is None


class TestEndpoints:
    def test_fuel_crud_api(self, client):
        _bootstrap_manager(client, "fuelboss@test.com")
        _register(client, "fueldrv@test.com", role="driver")
        dh = _login(client, "fueldrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-T1-01", "make": "T", "model": "M", "year": 2021, "vin": "VINT10000001"}, headers=dh)
        assert v.status_code == 201, v.text
        vid = v.json()["data"]["id"]
        bad = client.post("/api/fuel/", json={"vehicle_id": vid, "liters": -5, "cost": 0, "odometer_km": 100}, headers=dh)
        assert bad.status_code == 422
        ok = client.post("/api/fuel/", json={"vehicle_id": vid, "liters": 50, "cost": 5000, "odometer_km": 1000}, headers=dh)
        assert ok.status_code == 201, ok.text
        assert ok.json()["success"] is True
        lst = client.get(f"/api/fuel/vehicle/{vid}", headers=dh)
        assert lst.status_code == 200
        assert lst.json()["data"]["total"] == 1
        eff = client.get(f"/api/fuel/vehicle/{vid}/efficiency", headers=dh)
        assert eff.status_code == 200
        assert eff.json()["data"]["fills"] == 1
        assert client.get(f"/api/fuel/vehicle/999999", headers=dh).status_code == 404
        assert client.get(f"/api/fuel/vehicle/0", headers=dh).status_code == 400
        assert client.post("/api/fuel/", json={"vehicle_id": vid, "liters": 10, "cost": 0, "odometer_km": 1100}).status_code in (401, 403)

    def test_fuel_cross_user_403(self, client):
        _bootstrap_manager(client, "fuelboss2@test.com")
        _register(client, "fueldrvA@test.com", role="driver")
        _register(client, "fueldrvB@test.com", role="driver")
        ha = _login(client, "fueldrvA@test.com")
        hb = _login(client, "fueldrvB@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-T1-02", "make": "T", "model": "M", "year": 2021, "vin": "VINT10000002"}, headers=ha)
        vid = v.json()["data"]["id"]
        assert client.post("/api/fuel/", json={"vehicle_id": vid, "liters": 10, "cost": 100, "odometer_km": 500}, headers=hb).status_code == 403
        assert client.get(f"/api/fuel/vehicle/{vid}", headers=hb).status_code == 403
        assert client.get(f"/api/fuel/vehicle/{vid}/efficiency", headers=hb).status_code == 403

    def test_fuel_drop_alert_via_api(self, client):
        _bootstrap_manager(client, "fuelboss3@test.com")
        _register(client, "fueldrvC@test.com", role="driver")
        dh = _login(client, "fueldrvC@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-T1-03", "make": "T", "model": "M", "year": 2021, "vin": "VINT10000003"}, headers=dh)
        vid = v.json()["data"]["id"]
        for odo in (1000, 1500, 2000):
            r = client.post("/api/fuel/", json={"vehicle_id": vid, "liters": 50, "cost": 5000, "odometer_km": odo}, headers=dh)
            assert r.status_code == 201, r.text
        r = client.post("/api/fuel/", json={"vehicle_id": vid, "liters": 50, "cost": 5000, "odometer_km": 2250}, headers=dh)
        assert r.status_code == 201
        al = client.get(f"/api/alerts/?vehicle_id={vid}", headers=dh).json()["data"]["alerts"]
        assert any(a["type"] == "fuel" and a["severity"] == "warning" for a in al)

    def test_idle_days_api(self, client):
        _bootstrap_manager(client, "idleboss@test.com")
        _register(client, "idledrv@test.com", role="driver")
        dh = _login(client, "idledrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-T1-04", "make": "T", "model": "M", "year": 2021, "vin": "VINT10000004"}, headers=dh)
        vid = v.json()["data"]["id"]
        client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.97, "longitude": 77.59, "speed": 30.0}, headers=dh)
        client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.9701, "longitude": 77.5901, "speed": 1.0}, headers=dh)
        r = client.get(f"/api/locations/vehicle/{vid}/idle-days?days=7", headers=dh)
        assert r.status_code == 200, r.text
        assert isinstance(r.json()["data"], list)
        assert len(r.json()["data"]) == 1
        assert client.get(f"/api/locations/vehicle/{vid}/idle-days?days=7").status_code in (401, 403)
        _register(client, "idleother@test.com", role="driver")
        oh = _login(client, "idleother@test.com")
        assert client.get(f"/api/locations/vehicle/{vid}/idle-days?days=7", headers=oh).status_code == 403

    def test_inspection_api(self, client):
        mgr = _bootstrap_manager(client, "inspboss@test.com")
        _register(client, "inspdrv@test.com", role="driver")
        dh = _login(client, "inspdrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-T1-05", "make": "T", "model": "M", "year": 2021, "vin": "VINT10000005"}, headers=dh)
        vid = v.json()["data"]["id"]
        bad_type = client.post("/api/inspections/", json={"vehicle_id": vid, "type": "weekly", "passed": True}, headers=dh)
        assert bad_type.status_code == 422
        fail = client.post("/api/inspections/", json={"vehicle_id": vid, "type": "pre_trip", "passed": False, "notes": "lights out"}, headers=dh)
        assert fail.status_code == 201, fail.text
        assert fail.json()["data"]["passed"] is False
        al = client.get(f"/api/alerts/?vehicle_id={vid}", headers=dh).json()["data"]["alerts"]
        assert any(a["type"] == "maintenance" and a["severity"] == "high" for a in al)
        lst = client.get(f"/api/inspections/vehicle/{vid}", headers=dh)
        assert lst.status_code == 200
        assert lst.json()["data"]["total"] == 1
        all_insp = client.get("/api/inspections/", headers=mgr)
        assert all_insp.status_code == 200
        assert all_insp.json()["data"]["total"] >= 1
        assert client.post("/api/inspections/", json={"vehicle_id": vid, "type": "pre_trip", "passed": True}).status_code in (401, 403)
        _register(client, "inspother@test.com", role="driver")
        oh = _login(client, "inspother@test.com")
        assert client.get(f"/api/inspections/vehicle/{vid}", headers=oh).status_code == 403

    def test_csv_exports(self, client):
        mgr = _bootstrap_manager(client, "csvboss@test.com")
        _register(client, "csvdrv@test.com", role="driver")
        dh = _login(client, "csvdrv@test.com")
        v = client.post("/api/vehicles/", json={"license_plate": "KA-01-T1-06", "make": "T", "model": "M", "year": 2021, "vin": "VINT10000006"}, headers=dh)
        vid = v.json()["data"]["id"]
        client.post("/api/locations/", json={"vehicle_id": vid, "latitude": 12.97, "longitude": 77.59, "speed": 30.0}, headers=dh)
        client.post("/api/fuel/", json={"vehicle_id": vid, "liters": 40, "cost": 4000, "odometer_km": 900}, headers=dh)

        loc = client.get(f"/api/reports/locations.csv?vehicle_id={vid}&days=30", headers=dh)
        assert loc.status_code == 200, loc.text
        assert "text/csv" in loc.headers["content-type"]
        assert loc.text.startswith("timestamp,lat,lng,speed")

        al = client.get("/api/reports/alerts.csv?days=30", headers=dh)
        assert al.status_code == 200, al.text
        assert "text/csv" in al.headers["content-type"]
        assert al.text.startswith("id,vehicle_id,type,severity,message,is_read,created_at")

        fu = client.get(f"/api/reports/fuel.csv?vehicle_id={vid}", headers=dh)
        assert fu.status_code == 200, fu.text
        assert "text/csv" in fu.headers["content-type"]
        assert fu.text.startswith("id,vehicle_id,liters,cost,odometer_km,filled_at,note")

        assert client.get(f"/api/reports/locations.csv?vehicle_id={vid}").status_code in (401, 403)

        _register(client, "csvother@test.com", role="driver")
        oh = _login(client, "csvother@test.com")
        assert client.get(f"/api/reports/locations.csv?vehicle_id={vid}", headers=oh).status_code == 403
        assert client.get("/api/reports/locations.csv", headers=oh).status_code == 403

        fleet = client.get("/api/reports/locations.csv?days=30", headers=mgr)
        assert fleet.status_code == 200
        assert "text/csv" in fleet.headers["content-type"]
