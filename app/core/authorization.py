"""Reusable role + ownership authorization helpers.

Routers call these at the boundary so business logic in services stays
focused on persistence. Convention:
  - missing resource -> 404
  - existing resource owned by someone else (non-manager caller) -> 403
  - managers bypass ownership checks (fleet-wide access)
"""

from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.geofence import Geofence
from app.models.maintenance import Maintenance
from app.models.route import Route, RouteStop
from app.models.user import User
from app.models.vehicle import Vehicle

MANAGER_ROLE = "manager"
# Roles that must never be self-assigned via public registration.
PRIVILEGED_ROLES = {"manager", "admin", "superuser", "owner", "root"}


def is_manager(user: User) -> bool:
    """Return True when the user holds the fleet-manager role."""
    return bool(user) and user.role == MANAGER_ROLE


def require_manager(user: User) -> None:
    """Raise 403 unless the caller is a manager."""
    if not is_manager(user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Manager role required",
        )


def validate_positive_id(value: int, name: str = "id") -> int:
    """Reject non-positive IDs with 400 before hitting the database."""
    if value is None or int(value) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {name}: must be a positive integer",
        )
    return int(value)


def get_vehicle_or_404(db: Session, vehicle_id: int) -> Vehicle:
    """Fetch a vehicle or raise 404."""
    validate_positive_id(vehicle_id, "vehicle_id")
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Vehicle {vehicle_id} not found",
        )
    return vehicle


def require_vehicle_access(db: Session, vehicle_id: int, user: User) -> Vehicle:
    """Return the vehicle if the caller may access it (owner or manager)."""
    vehicle = get_vehicle_or_404(db, vehicle_id)
    if is_manager(user):
        return vehicle
    if vehicle.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this vehicle",
        )
    return vehicle


def owned_vehicle_ids(db: Session, user: User) -> Optional[List[int]]:
    """IDs of vehicles owned by the user; None means unrestricted (manager)."""
    if is_manager(user):
        return None
    rows = db.query(Vehicle.id).filter(Vehicle.owner_id == user.id).all()
    return [r[0] for r in rows]


def get_route_or_404(db: Session, route_id: int) -> Route:
    """Fetch a route or raise 404."""
    validate_positive_id(route_id, "route_id")
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Route {route_id} not found",
        )
    return route


def require_route_access(db: Session, route_id: int, user: User) -> Route:
    """Return the route if the caller owns its vehicle, drives it, or manages."""
    route = get_route_or_404(db, route_id)
    if is_manager(user):
        return route
    vehicle = db.query(Vehicle).filter(Vehicle.id == route.vehicle_id).first()
    owns_vehicle = vehicle is not None and vehicle.owner_id == user.id
    is_driver = route.driver_id is not None and route.driver_id == user.id
    if not (owns_vehicle or is_driver):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this route",
        )
    return route


def require_stop_access(db: Session, stop_id: int, user: User) -> RouteStop:
    """Return the stop if the caller may access its parent route."""
    validate_positive_id(stop_id, "stop_id")
    stop = db.query(RouteStop).filter(RouteStop.id == stop_id).first()
    if not stop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Stop {stop_id} not found",
        )
    require_route_access(db, stop.route_id, user)
    return stop


def require_alert_access(db: Session, alert_id: int, user: User) -> Alert:
    """Return the alert if the caller owns its vehicle (or manages)."""
    validate_positive_id(alert_id, "alert_id")
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    if is_manager(user):
        return alert
    if alert.vehicle_id is None:
        # Fleet-wide alert: visible to all authenticated users, but only
        # managers may mutate it; callers decide read vs write.
        return alert
    require_vehicle_access(db, alert.vehicle_id, user)
    return alert


def require_maintenance_access(
    db: Session, maintenance_id: int, user: User
) -> Maintenance:
    """Return the maintenance record if the caller owns its vehicle (or manages)."""
    validate_positive_id(maintenance_id, "maintenance_id")
    record = (
        db.query(Maintenance).filter(Maintenance.id == maintenance_id).first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance {maintenance_id} not found",
        )
    if is_manager(user):
        return record
    require_vehicle_access(db, record.vehicle_id, user)
    return record


def get_geofence_or_404(db: Session, geofence_id: int) -> Geofence:
    """Fetch a geofence or raise 404."""
    validate_positive_id(geofence_id, "geofence_id")
    geofence = db.query(Geofence).filter(Geofence.id == geofence_id).first()
    if not geofence:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Geofence {geofence_id} not found",
        )
    return geofence


def require_geofence_access(db: Session, geofence_id: int, user: User) -> Geofence:
    """Return the geofence if the caller owns it (or manages)."""
    geofence = get_geofence_or_404(db, geofence_id)
    if is_manager(user):
        return geofence
    if geofence.owner_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this geofence",
        )
    return geofence
