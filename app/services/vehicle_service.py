"""
Vehicle service layer - business logic for fleet vehicle management.
"""
from decimal import Decimal
from typing import List, Optional

from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.vehicle import VehicleCreate, VehicleUpdate


def get_vehicle_by_id(db: Session, vehicle_id: int) -> Optional[Vehicle]:
    """Look up a single vehicle by its ID."""
    return db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()


def get_vehicle_by_plate(db: Session, license_plate: str) -> Optional[Vehicle]:
    """Find a vehicle by license plate (case-insensitive)."""
    return db.query(Vehicle).filter(
        Vehicle.license_plate == license_plate.upper()
    ).first()


def list_vehicles(
    db: Session,
    owner_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[List[Vehicle], int]:
    """
    Get a paginated list of vehicles.
    If owner_id is provided, only returns vehicles owned by that user.
    """
    query = db.query(Vehicle)
    if owner_id:
        query = query.filter(Vehicle.owner_id == owner_id)
    if status:
        query = query.filter(Vehicle.status == status)

    total = query.count()
    vehicles = query.offset(skip).limit(limit).all()
    return vehicles, total


def create_vehicle(db: Session, owner_id: int, data: VehicleCreate) -> Vehicle:
    """
    Register a new vehicle in the fleet.
    The owner_id should come from the authenticated user (manager role).
    """
    # Check for duplicate license plate
    existing = get_vehicle_by_plate(db, data.license_plate)
    if existing:
        raise ValueError(f"Vehicle with license plate {data.license_plate} already registered")

    # Verify the owner exists
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner:
        raise ValueError("Owner user not found")

    vehicle = Vehicle(
        owner_id=owner_id,
        license_plate=data.license_plate,
        make=data.make,
        model=data.model,
        year=data.year,
        vin=data.vin,
        fleet_id=data.fleet_id,
        status="active",
        current_mileage=Decimal("0.00"),
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle


def update_vehicle(
    db: Session, vehicle_id: int, data: VehicleUpdate
) -> Optional[Vehicle]:
    """
    Update vehicle details. Only non-None fields are updated.
    """
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(vehicle, field, value)

    db.commit()
    db.refresh(vehicle)
    return vehicle


def delete_vehicle(db: Session, vehicle_id: int) -> bool:
    """
    Remove a vehicle from the fleet. Returns True if deleted.
    """
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        return False

    db.delete(vehicle)
    db.commit()
    return True


def update_mileage(db: Session, vehicle_id: int, new_mileage: Decimal) -> Optional[Vehicle]:
    """
    Update the current mileage for a vehicle. Used when GPS pings come in
    with updated odometer data.
    """
    vehicle = get_vehicle_by_id(db, vehicle_id)
    if not vehicle:
        return None

    vehicle.current_mileage = new_mileage
    db.commit()
    db.refresh(vehicle)
    return vehicle
