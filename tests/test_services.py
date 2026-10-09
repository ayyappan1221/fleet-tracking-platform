"""Review-II service-layer unit tests: direct coverage for all major services.

Uses the isolated in-memory SQLite ``db_session`` fixture from conftest.py.
No network, no file writes, no app/ changes. Complements (does not duplicate)
the API-level tests in test_security.py / test_integration.py which already
cover auth scoping (404/403), manager bypass, and envelope shape.
"""
from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models import User
from app.schemas.alert import AlertCreate
from app.schemas.geofence import GeofenceCreate, GeofenceUpdate
from app.schemas.location import LocationCreate
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate
from app.schemas.route import RouteCreate, RouteStopCreate
from app.schemas.vehicle import VehicleCreate, VehicleUpdate
from app.services import (
    alert_service,
    dashboard_service,
    geofence_service,
    location_service,
    maintenance_service,
    route_service,
    vehicle_service,
)
from app.services.route_service import _haversine_km, _optimize_stops


# ---------- helpers ----------

_uid = {"n": 0}


def _make_user(db: Session, role="manager") -> User:
    _uid["n"] += 1
    u = User(
        email=f"svc{_uid['n']}@test.com",
        name="Svc User",
        password_hash=hash_password("Secret123!"),
        role=role,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _make_vehicle(db: Session, owner_id: int, plate: str, vin: str):
    return vehicle_service.create_vehicle(
        db,
        owner_id,
        VehicleCreate(
            license_plate=plate, make="Tata", model="Ace",
            year=2021, vin=vin,
        ),
    )


def _make_route(db: Session, vehicle_id: int, n_stops: int = 2) -> object:
    pts = [
        (12.9716, 77.5946, "Warehouse"),
        (12.9352, 77.6246, "HSR"),
        (13.0355, 77.5946, "Whitefield"),
        (12.9900, 77.6600, "MG Road"),
    ][:n_stops]
    stops = [
        RouteStopCreate(sequence=i + 1, latitude=la, longitude=lo, address=a)
        for i, (la, lo, a) in enumerate(pts)
    ]
    return route_service.plan_route(
        db, RouteCreate(vehicle_id=vehicle_id, stops=stops)
    )


# ================= vehicle_service =================

class TestVehicleService:
    def test_create_happy(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SV-01", "VINSVC000001")
        assert v.status == "active"
        assert v.current_mileage == Decimal("0.00")
        assert v.owner_id == u.id

    def test_create_duplicate_plate(self, db_session: Session):
        u = _make_user(db_session)
        _make_vehicle(db_session, u.id, "KA-01-SV-02", "VINSVC000002")
        with pytest.raises(ValueError, match="already registered"):
            _make_vehicle(db_session, u.id, "ka-01-sv-02", "VINSVC000099")

    def test_create_missing_owner(self, db_session: Session):
        with pytest.raises(ValueError, match="Owner user not found"):
            vehicle_service.create_vehicle(
                db_session, 999999,
                VehicleCreate(license_plate="KA-01-SV-03", make="T", model="M",
                              year=2020, vin="VINSVC000003"),
            )

    def test_get_by_plate_case_insensitive(self, db_session: Session):
        u = _make_user(db_session)
        _make_vehicle(db_session, u.id, "KA-01-SV-04", "VINSVC000004")
        assert vehicle_service.get_vehicle_by_plate(db_session, "ka-01-sv-04") is not None
        assert vehicle_service.get_vehicle_by_plate(db_session, "NOPE-00") is None

    def test_get_missing_returns_none(self, db_session: Session):
        assert vehicle_service.get_vehicle_by_id(db_session, 999999) is None

    def test_list_filters_and_pagination(self, db_session: Session):
        u1 = _make_user(db_session)
        u2 = _make_user(db_session)
        v1 = _make_vehicle(db_session, u1.id, "KA-01-SV-05", "VINSVC000005")
        _make_vehicle(db_session, u2.id, "KA-01-SV-06", "VINSVC000006")
        vehicle_service.update_vehicle(
            db_session, v1.id, VehicleUpdate(status="repair"))

        owned, total = vehicle_service.list_vehicles(db_session, owner_id=u1.id)
        assert total == 1 and owned[0].id == v1.id

        rep, total = vehicle_service.list_vehicles(db_session, status="repair")
        assert total == 1

        page, total = vehicle_service.list_vehicles(db_session, skip=1, limit=1)
        assert total == 2 and len(page) == 1

    def test_update_and_update_missing(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SV-07", "VINSVC000007")
        upd = vehicle_service.update_vehicle(
            db_session, v.id,
            VehicleUpdate(status="inactive", current_mileage=Decimal("1500.50")))
        assert upd.status == "inactive"
        assert upd.current_mileage == Decimal("1500.50")
        assert vehicle_service.update_vehicle(
            db_session, 999999, VehicleUpdate(status="repair")) is None

    def test_delete_and_delete_missing(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SV-08", "VINSVC000008")
        assert vehicle_service.delete_vehicle(db_session, v.id) is True
        assert vehicle_service.get_vehicle_by_id(db_session, v.id) is None
        assert vehicle_service.delete_vehicle(db_session, 999999) is False

    def test_update_mileage(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SV-09", "VINSVC000009")
        out = vehicle_service.update_mileage(db_session, v.id, Decimal("42.25"))
        assert out.current_mileage == Decimal("42.25")
        assert vehicle_service.update_mileage(db_session, 999999, Decimal("1")) is None


# ================= route_service =================

class TestRouteService:
    def test_plan_happy_distance(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SR-01", "VINSRR000001")
        r = _make_route(db_session, v.id, 3)
        assert r.status == "planned"
        assert len(r.stops) == 3
        assert r.distance_km > 0

    def test_plan_missing_vehicle(self, db_session: Session):
        with pytest.raises(ValueError, match="not found"):
            route_service.plan_route(
                db_session,
                RouteCreate(vehicle_id=999999, stops=[
                    RouteStopCreate(sequence=1, latitude=12.9, longitude=77.5),
                    RouteStopCreate(sequence=2, latitude=12.8, longitude=77.6),
                ]),
            )

    def test_plan_requires_two_stops_schema(self):
        with pytest.raises(ValidationError):
            RouteCreate(vehicle_id=1, stops=[
                RouteStopCreate(sequence=1, latitude=12.9, longitude=77.5)])

    def test_lifecycle_start_complete(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SR-02", "VINSRR000002")
        r = _make_route(db_session, v.id)
        started = route_service.start_route(db_session, r.id)
        assert started.status == "in_progress" and started.start_time is not None
        done = route_service.complete_route(db_session, r.id)
        assert done.status == "completed" and done.end_time is not None

    def test_start_invalid_transitions(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SR-03", "VINSRR000003")
        r = _make_route(db_session, v.id)
        route_service.start_route(db_session, r.id)
        with pytest.raises(ValueError, match="cannot start"):
            route_service.start_route(db_session, r.id)
        with pytest.raises(ValueError, match="not found"):
            route_service.start_route(db_session, 999999)

    def test_complete_invalid_transitions(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SR-04", "VINSRR000004")
        r = _make_route(db_session, v.id)
        with pytest.raises(ValueError, match="cannot complete"):
            route_service.complete_route(db_session, r.id)  # still planned
        with pytest.raises(ValueError, match="not found"):
            route_service.complete_route(db_session, 999999)

    def test_mark_stop_arrived_and_missing(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SR-05", "VINSRR000005")
        r = _make_route(db_session, v.id)
        stop = route_service.mark_stop_arrived(db_session, r.stops[0].id)
        assert stop.status == "arrived" and stop.actual_arrival is not None
        with pytest.raises(ValueError, match="not found"):
            route_service.mark_stop_arrived(db_session, 999999)

    def test_list_filters(self, db_session: Session):
        u = _make_user(db_session)
        v1 = _make_vehicle(db_session, u.id, "KA-01-SR-06", "VINSRR000006")
        v2 = _make_vehicle(db_session, u.id, "KA-01-SR-07", "VINSRR000007")
        _make_route(db_session, v1.id)
        _make_route(db_session, v2.id)
        routes, total = route_service.list_routes(db_session, vehicle_id=v1.id)
        assert total == 1
        routes, total = route_service.list_routes(
            db_session, vehicle_ids=[v1.id, v2.id])
        assert total == 2
        assert route_service.get_route_by_id(db_session, 999999) is None

    def test_optimize_ordering_and_haversine(self):
        assert _haversine_km(12.97, 77.59, 12.97, 77.59) == pytest.approx(0.0)
        assert _haversine_km(12.97, 77.59, 13.03, 77.59) > 0
        assert _optimize_stops([{"lat": 1.0, "lng": 1.0}]) == [{"lat": 1.0, "lng": 1.0}]
        stops = [
            {"lat": 12.9716, "lng": 77.5946, "tag": "start"},
            {"lat": 13.0355, "lng": 77.5946, "tag": "far"},
            {"lat": 12.9352, "lng": 77.5946, "tag": "near"},
        ]
        ordered = _optimize_stops(stops)
        assert ordered[0]["tag"] == "start"
        assert ordered[1]["tag"] == "near"  # nearest-neighbor picks closer first


# ================= location_service =================

class TestLocationService:
    def test_record_happy(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SL-01", "VINSLC000001")
        loc = location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.97,
                                       longitude=77.59, speed=40.0, heading=90.0))
        assert loc.id is not None
        assert location_service.get_location_by_id(db_session, loc.id) is not None

    def test_record_missing_vehicle(self, db_session: Session):
        with pytest.raises(ValueError, match="not found"):
            location_service.record_location(
                db_session, LocationCreate(vehicle_id=999999, latitude=12.9,
                                           longitude=77.5))

    def test_invalid_coordinates_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            LocationCreate(vehicle_id=1, latitude=200.0, longitude=77.5)
        with pytest.raises(ValidationError):
            LocationCreate(vehicle_id=1, latitude=12.9, longitude=-190.0)

    def test_latest_returns_most_recent(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SL-02", "VINSLC000002")
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=12.9, longitude=77.5))
        second = location_service.record_location(
            db_session, LocationCreate(vehicle_id=v.id, latitude=13.0, longitude=77.6))
        latest = location_service.get_latest_location(db_session, v.id)
        assert latest.id == second.id
        assert location_service.get_latest_location(db_session, 999999) is None

    def test_list_filter_and_delete(self, db_session: Session):
        u = _make_user(db_session)
        v1 = _make_vehicle(db_session, u.id, "KA-01-SL-03", "VINSLC000003")
        v2 = _make_vehicle(db_session, u.id, "KA-01-SL-04", "VINSLC000004")
        loc = location_service.record_location(
            db_session, LocationCreate(vehicle_id=v1.id, latitude=12.9, longitude=77.5))
        location_service.record_location(
            db_session, LocationCreate(vehicle_id=v2.id, latitude=12.8, longitude=77.4))
        locs, total = location_service.list_locations(db_session, vehicle_id=v1.id)
        assert total == 1
        assert location_service.delete_location(db_session, loc.id) is True
        assert location_service.delete_location(db_session, 999999) is False
        assert location_service.get_location_by_id(db_session, 999999) is None


# ================= alert_service =================

class TestAlertService:
    def test_create_and_get(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SA-01", "VINSAL000001")
        a = alert_service.create_alert(
            db_session, AlertCreate(vehicle_id=v.id, type="speed",
                                    severity="warning", message="too fast"))
        assert a.is_read is False
        assert alert_service.get_alert_by_id(db_session, a.id) is not None
        assert alert_service.get_alert_by_id(db_session, 999999) is None

    def test_invalid_type_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            AlertCreate(vehicle_id=1, type="alien", message="x")

    def test_list_filters(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SA-02", "VINSAL000002")
        alert_service.create_alert(
            db_session, AlertCreate(vehicle_id=v.id, type="speed", message="m1"))
        a2 = alert_service.create_alert(
            db_session, AlertCreate(vehicle_id=v.id, type="low_fuel", message="m2"))
        alert_service.mark_alert_read(db_session, a2.id)
        unread, total = alert_service.list_alerts(db_session, is_read=False)
        assert total == 1
        by_veh, total = alert_service.list_alerts(db_session, vehicle_id=v.id)
        assert total == 2
        scoped, total = alert_service.list_alerts(db_session, vehicle_ids=[v.id])
        assert total == 2

    def test_mark_read_and_missing(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SA-03", "VINSAL000003")
        a = alert_service.create_alert(
            db_session, AlertCreate(vehicle_id=v.id, type="geofence", message="exit"))
        out = alert_service.mark_alert_read(db_session, a.id)
        assert out.is_read is True
        assert alert_service.mark_alert_read(db_session, 999999) is None

    def test_delete_and_missing(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SA-04", "VINSAL000004")
        a = alert_service.create_alert(
            db_session, AlertCreate(vehicle_id=v.id, type="speed", message="x"))
        assert alert_service.delete_alert(db_session, a.id) is True
        assert alert_service.delete_alert(db_session, 999999) is False


# ================= maintenance_service =================

class TestMaintenanceService:
    def test_create_happy(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SM-01", "VINSMA000001")
        r = maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="oil_change",
                                          status="scheduled",
                                          due_mileage=Decimal("5000"),
                                          due_date=date(2026, 12, 1),
                                          notes="due soon"))
        assert r.id is not None
        assert maintenance_service.get_maintenance_by_id(db_session, r.id) is not None

    def test_create_missing_vehicle(self, db_session: Session):
        with pytest.raises(ValueError, match="not found"):
            maintenance_service.create_maintenance(
                db_session, MaintenanceCreate(vehicle_id=999999, type="tire"))

    def test_invalid_type_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            MaintenanceCreate(vehicle_id=1, type="warp_drive")

    def test_update_and_completed_transition(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SM-02", "VINSMA000002")
        r = maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="inspection"))
        out = maintenance_service.update_maintenance(
            db_session, r.id, MaintenanceUpdate(status="in_progress"))
        assert out.status == "in_progress" and out.completed_at is None
        done = maintenance_service.update_maintenance(
            db_session, r.id, MaintenanceUpdate(status="completed"))
        assert done.status == "completed" and done.completed_at is not None
        assert maintenance_service.update_maintenance(
            db_session, 999999, MaintenanceUpdate(status="completed")) is None

    def test_list_filters_and_delete(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SM-03", "VINSMA000003")
        r = maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="tire",
                                          status="scheduled"))
        by_veh, total = maintenance_service.list_maintenance(
            db_session, vehicle_id=v.id)
        assert total == 1
        by_status, total = maintenance_service.list_maintenance(
            db_session, status="scheduled")
        assert total >= 1
        scoped, total = maintenance_service.list_maintenance(
            db_session, vehicle_ids=[v.id])
        assert total == 1
        assert maintenance_service.delete_maintenance(db_session, r.id) is True
        assert maintenance_service.delete_maintenance(db_session, 999999) is False
        assert maintenance_service.get_maintenance_by_id(db_session, 999999) is None


# ================= geofence_service =================

class TestGeofenceService:
    def _payload(self):
        return GeofenceCreate(
            name="Zone A", type="inclusion",
            coordinates="POLYGON((12.97 77.59, 12.98 77.60, 12.96 77.61, 12.97 77.59))")

    def test_create_happy(self, db_session: Session):
        u = _make_user(db_session)
        g = geofence_service.create_geofence(db_session, u.id, self._payload())
        assert g.is_active is True and g.owner_id == u.id
        assert geofence_service.get_geofence_by_id(db_session, g.id) is not None

    def test_create_missing_owner(self, db_session: Session):
        with pytest.raises(ValueError, match="Owner user not found"):
            geofence_service.create_geofence(db_session, 999999, self._payload())

    def test_invalid_type_rejected_by_schema(self):
        with pytest.raises(ValidationError):
            GeofenceCreate(name="Z", type="circle", coordinates="x")

    def test_list_owner_filter(self, db_session: Session):
        u1 = _make_user(db_session)
        u2 = _make_user(db_session)
        geofence_service.create_geofence(db_session, u1.id, self._payload())
        geofence_service.create_geofence(db_session, u2.id, self._payload())
        mine, total = geofence_service.list_geofences(db_session, owner_id=u1.id)
        assert total == 1 and mine[0].owner_id == u1.id
        all_g, total = geofence_service.list_geofences(db_session)
        assert total == 2

    def test_update_and_missing(self, db_session: Session):
        u = _make_user(db_session)
        g = geofence_service.create_geofence(db_session, u.id, self._payload())
        out = geofence_service.update_geofence(
            db_session, g.id, GeofenceUpdate(name="Zone B", is_active=False))
        assert out.name == "Zone B" and out.is_active is False
        assert geofence_service.update_geofence(
            db_session, 999999, GeofenceUpdate(name="X")) is None

    def test_delete_geofence_lifecycle(self, db_session: Session):
        u = _make_user(db_session)
        g = geofence_service.create_geofence(db_session, u.id, self._payload())
        assert geofence_service.delete_geofence(db_session, g.id) is True
        assert geofence_service.delete_geofence(db_session, g.id) is False
        assert geofence_service.get_geofence_by_id(db_session, 999999) is None


# ================= dashboard_service =================

class TestDashboardService:
    EXPECTED_KEYS = {"total_vehicles", "active_vehicles", "total_routes",
                     "active_routes", "pending_maintenance", "unread_alerts",
                     "total_geofences"}

    def test_empty_summary_keys_and_types(self, db_session: Session):
        s = dashboard_service.get_summary(db_session)
        assert set(s.keys()) == self.EXPECTED_KEYS
        assert all(isinstance(v, int) for v in s.values())
        assert all(v == 0 for v in s.values())

    def test_populated_aggregation(self, db_session: Session):
        u = _make_user(db_session)
        v = _make_vehicle(db_session, u.id, "KA-01-SD-01", "VINSDS000001")
        vehicle_service.update_vehicle(
            db_session, v.id, VehicleUpdate(status="repair"))
        r = _make_route(db_session, v.id)
        route_service.start_route(db_session, r.id)
        maintenance_service.create_maintenance(
            db_session, MaintenanceCreate(vehicle_id=v.id, type="oil_change"))
        alert_service.create_alert(
            db_session, AlertCreate(vehicle_id=v.id, type="speed", message="fast"))
        geofence_service.create_geofence(
            db_session, u.id,
            GeofenceCreate(name="Z", type="inclusion", coordinates="POLYGON((1 1, 2 2, 3 3, 1 1))"))
        s = dashboard_service.get_summary(db_session)
        assert s["total_vehicles"] == 1
        assert s["active_vehicles"] == 0  # vehicle moved to repair
        assert s["total_routes"] == 1
        assert s["active_routes"] == 1
        assert s["pending_maintenance"] == 1
        assert s["unread_alerts"] == 1
        assert s["total_geofences"] == 1
        done_m = maintenance_service.list_maintenance(db_session)[0][0]
        maintenance_service.update_maintenance(
            db_session, done_m.id, MaintenanceUpdate(status="completed"))
        s2 = dashboard_service.get_summary(db_session)
        assert s2["pending_maintenance"] == 0
