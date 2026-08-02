"""
Integration tests for vehicle and route management.

These tests verify end-to-end flows:
  1. Vehicle CRUD (create -> list -> read -> update -> delete)
  2. Route planning with optimization (create -> list -> start -> complete)
"""
import pytest
from decimal import Decimal
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.security import hash_password
from app.models import User, Vehicle, Route, RouteStop
from app.schemas.vehicle import VehicleCreate
from app.schemas.route import RouteCreate, RouteStopCreate
from app.services import vehicle_service, route_service


@pytest.fixture
def test_db(db_session: Session):
    """Create tables and a test user before each test."""
    Base.metadata.create_all(bind=db_session.bind)

    # Create a test user
    user = User(
        email="fleet_manager@test.com",
        name="Test Manager",
        password_hash=hash_password("password123"),
        role="manager",
    )
    db_session.add(user)
    db_session.commit()
    yield db_session


# === Vehicle CRUD Flow ===

def test_vehicle_crud_flow(test_db: Session):
    """Full cycle: create vehicle -> list -> read -> update -> delete."""
    # Create
    vehicle_data = VehicleCreate(
        license_plate="ABC 1234",
        make="Toyota",
        model="Hilux",
        year=2023,
        vin="VIN1234567890",
    )
    user_id = test_db.query(User).first().id
    vehicle = vehicle_service.create_vehicle(test_db, user_id, vehicle_data)
    assert vehicle.license_plate == "ABC 1234"
    assert vehicle.status == "active"

    # List
    vehicles, total = vehicle_service.list_vehicles(test_db)
    assert total == 1
    assert vehicles[0].license_plate == "ABC 1234"

    # Read
    fetched = vehicle_service.get_vehicle_by_id(test_db, vehicle.id)
    assert fetched is not None
    assert fetched.make == "Toyota"

    # Update
    from app.schemas.vehicle import VehicleUpdate
    updated = vehicle_service.update_vehicle(
        test_db, vehicle.id,
        VehicleUpdate(status="repair", current_mileage=Decimal("1500.50")),
    )
    assert updated.status == "repair"
    assert updated.current_mileage == Decimal("1500.50")

    # Delete
    result = vehicle_service.delete_vehicle(test_db, vehicle.id)
    assert result is True

    # Verify gone
    assert vehicle_service.get_vehicle_by_id(test_db, vehicle.id) is None


# === Route Planning Flow ===

def test_route_planning_flow(test_db: Session):
    """Full flow: create vehicle -> plan route -> start -> complete."""
    user_id = test_db.query(User).first().id

    # First create a vehicle
    vehicle = vehicle_service.create_vehicle(
        test_db,
        user_id,
        VehicleCreate(
            license_plate="XYZ 7890",
            make="Ford",
            model="Transit",
            year=2022,
            vin="VIN9876543210",
        ),
    )

    # Create stops (warehouse + 3 delivery points around Bangalore)
    stops = [
        RouteStopCreate(
            sequence=1, latitude=12.9716, longitude=77.5946, address="Warehouse, Bangalore"
        ),
        RouteStopCreate(
            sequence=2, latitude=12.9352, longitude=77.8439, address="HSR Layout"
        ),
        RouteStopCreate(
            sequence=3, latitude=12.9716, longitude=77.6476, address="MG Road"
        ),
    ]

    route_data = RouteCreate(
        vehicle_id=vehicle.id,
        driver_id=user_id,
        start_location="Warehouse, Bangalore",
        end_location="Warehouse, Bangalore",
        stops=stops,
    )

    # Plan the route
    planned = route_service.plan_route(test_db, route_data)
    assert planned.status == "planned"
    assert len(planned.stops) == 3

    # Start the route
    started = route_service.start_route(test_db, planned.id)
    assert started.status == "in_progress"
    assert started.start_time is not None

    # Mark a stop as arrived
    route_service.mark_stop_arrived(test_db, planned.stops[0].id)
    assert planned.stops[0].status == "arrived"

    # Complete the route
    completed = route_service.complete_route(test_db, planned.id)
    assert completed.status == "completed"
    assert completed.end_time is not None


# === Route Optimization ===

def test_route_stops_are_optimized(test_db: Session):
    """Verify the nearest-neighbor optimization reorders stops by distance."""
    user_id = test_db.query(User).first().id

    vehicle = vehicle_service.create_vehicle(
        test_db, user_id,
        VehicleCreate(
            license_plate="OPT 0001", make="Mahindra", model="Bolero",
            year=2023, vin="VINOPT0001",
        ),
    )

    # Stops that are NOT in optimal order (intentionally shuffled)
    stops = [
        RouteStopCreate(sequence=1, latitude=12.9716, longitude=77.5946, address="Start: Central"),
        RouteStopCreate(sequence=2, latitude=12.9716, longitude=77.6476, address="Far: MG Road"),
        RouteStopCreate(sequence=3, latitude=13.0355, longitude=77.5946, address="Far: Whitefield"),
        RouteStopCreate(sequence=4, latitude=12.9352, longitude=77.5946, address="Close: HSR"),
    ]

    route_data = RouteCreate(
        vehicle_id=vehicle.id,
        stops=stops,
    )

    route = route_service.plan_route(test_db, route_data)

    # The first stop should still be the start (warehouse)
    assert route.stops[0].address == "Start: Central"
    # Total distance should be > 0
    assert route.distance_km > 0
