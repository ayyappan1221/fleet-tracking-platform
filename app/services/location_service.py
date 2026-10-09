"""
Location service layer - business logic for GPS location tracking.
"""
from datetime import datetime, timedelta, timezone
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
    vehicle_ids: Optional[list] = None,
) -> Tuple[List[Location], int]:
    """
    Get a paginated list of location records.
    If vehicle_id is provided, only returns locations for that vehicle.
    """
    query = db.query(Location)
    if vehicle_id:
        query = query.filter(Location.vehicle_id == vehicle_id)
    if vehicle_ids is not None:
        query = query.filter(Location.vehicle_id.in_(vehicle_ids))

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

    previous = (
        db.query(Location)
        .filter(Location.vehicle_id == data.vehicle_id)
        .order_by(desc(Location.recorded_at))
        .first()
    )
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
    try:
        _record_idle_event(db, location, previous)
    except Exception:
        pass
    try:
        _run_intelligence_checks(db, location)
    except Exception:
        pass
    return location


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometers."""
    from math import atan2, cos, radians, sin, sqrt

    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * atan2(sqrt(a), sqrt(1 - a))


def _ensure_aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _record_idle_event(db: Session, location: Location, previous: Optional[Location]) -> None:
    """
    Detect idle: speed < 3 km/h AND a prior ping within the last 10 minutes
    at nearly the same coordinates (haversine < 0.05 km).

    Records an IdleEvent with minutes equal to the gap since the prior ping.
    """
    from app.models.idle import IdleEvent

    if location.speed is None or location.speed >= 3:
        return
    if previous is None:
        return
    now = _ensure_aware(location.recorded_at) or datetime.now(timezone.utc)
    prev_at = _ensure_aware(previous.recorded_at)
    if prev_at is None:
        return
    gap_minutes = (now - prev_at).total_seconds() / 60.0
    if gap_minutes < 0 or gap_minutes > 10:
        return
    if previous.latitude is None or previous.longitude is None:
        return
    dist = _haversine_km(
        float(previous.latitude), float(previous.longitude),
        float(location.latitude), float(location.longitude),
    )
    if dist >= 0.05:
        return
    minutes = round(max(gap_minutes, 0.0), 2)
    db.add(IdleEvent(
        vehicle_id=location.vehicle_id,
        started_at=now,
        minutes=minutes,
    ))
    db.commit()


def idle_days(db: Session, vehicle_id: int, days: int = 7) -> list:
    """Aggregate idle minutes per day for the last `days` days."""
    from collections import defaultdict

    from app.models.idle import IdleEvent

    days = max(1, min(int(days), 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    events = (
        db.query(IdleEvent)
        .filter(IdleEvent.vehicle_id == vehicle_id)
        .all()
    )
    per_day: dict = defaultdict(float)
    for e in events:
        started = _ensure_aware(e.started_at)
        if started is None or started < cutoff:
            continue
        per_day[started.date().isoformat()] += float(e.minutes or 0)
    return [
        {"date": day, "idle_minutes": round(per_day[day], 2)}
        for day in sorted(per_day)
    ]


def _run_intelligence_checks(db: Session, location: Location) -> None:
    from app.core.config import settings
    from app.models.alert import Alert
    from app.services import alert_service as alerts
    from app.services import geofence_service as geofences

    limit = float(getattr(settings, "SPEED_LIMIT_KMH", 100))
    if location.speed is not None and location.speed > limit:
        if not alerts.recent_alert_exists(db, location.vehicle_id, ["speed", "speeding"], minutes=5):
            db.add(Alert(
                vehicle_id=location.vehicle_id,
                type="speeding",
                severity="warning",
                message=f"Speeding detected: {location.speed:.1f} km/h exceeds limit {limit:.0f} km/h (vehicle {location.vehicle_id})",
            ))
            db.commit()
    try:
        all_fences, _ = geofences.list_geofences(db)
    except Exception:
        return
    for fence in all_fences:
        if not fence.is_active:
            continue
        parsed = geofences.parse_coordinates(fence.coordinates or "")
        if parsed.get("kind") == "unknown":
            continue
        inside = geofences.is_inside(location.latitude, location.longitude, parsed)
        if geofences.is_breach(fence.type, inside):
            if not alerts.recent_alert_exists(db, location.vehicle_id, ["geofence"], minutes=5):
                db.add(Alert(
                    vehicle_id=location.vehicle_id,
                    type="geofence",
                    severity="warning",
                    message=f"Geofence breach: vehicle {location.vehicle_id} violated '{fence.name}' ({fence.type})",
                ))
                db.commit()
            break


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
