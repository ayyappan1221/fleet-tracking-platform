"""
Location service layer - business logic for GPS location tracking.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.location import Location
from app.models.vehicle import Vehicle
from app.schemas.location import LocationCreate


def get_location_by_id(db: Session, location_id: int) -> Optional[Location]:
    """Look up a single location record by its ID."""
    return db.query(Location).filter(Location.id == location_id).first()


def list_locations(
    db: Session,
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Location], int]:
    """
    Get a paginated list of location records.
    If vehicle_id is provided, only returns locations for that vehicle.
    """
    query = db.query(Location)
    if vehicle_id:
        query = query.filter(Location.vehicle_id == vehicle_id)

    total = query.count()
    locations = (
        query.order_by(desc(Location.recorded_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return locations, total


def record_location(db: Session, data: LocationCreate) -> Location:
    """
    Record a new GPS location for a vehicle.
    The vehicle must already exist.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle {data.vehicle_id} not found")

    location = Location(
        vehicle_id=data.vehicle_id,
        latitude=data.latitude,
        longitude=data.longitude,
        speed=data.speed,
        heading=data.heading,
    )
    db.add(location)
    db.commit()
    db.refresh(location)
    return location


def get_latest_location(db: Session, vehicle_id: int) -> Optional[Location]:
    """Get the most recent GPS location for a specific vehicle."""
    return (
        db.query(Location)
        .filter(Location.vehicle_id == vehicle_id)
        .order_by(desc(Location.recorded_at))
        .first()
    )


def delete_location(db: Session, location_id: int) -> bool:
    """Remove a location record. Returns True if deleted."""
    location = get_location_by_id(db, location_id)
    if not location:
        return False

    db.delete(location)
    db.commit()
    return True
