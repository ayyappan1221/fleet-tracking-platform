"""
Route service - handles route planning, starting, and completion.

Includes a basic distance-based optimization for multi-stop routes.
"""
from decimal import Decimal
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.route import Route, RouteStop
from app.models.vehicle import Vehicle
from app.schemas.route import RouteCreate


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate great-circle distance between two points in kilometers."""
    from math import radians, sin, cos, sqrt, atan2

    R = 6371  # Earth radius in km
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c


def _optimize_stops(stops: List[dict]) -> List[dict]:
    """
    Basic nearest-neighbor route optimization.

    Takes a list of stop dicts with 'lat' and 'lng' keys,
    returns them reordered to minimize total distance from start.
    """
    if len(stops) <= 2:
        return stops

    # Start from the first stop (the pickup point)
    ordered = [stops[0]]
    remaining = stops[1:]

    while remaining:
        last = ordered[-1]
        # Find nearest unvisited stop
        nearest = min(
            remaining,
            key=lambda s: _haversine_km(
                last["lat"], last["lng"], s["lat"], s["lng"]
            ),
        )
        ordered.append(nearest)
        remaining.remove(nearest)

    return ordered


def get_route_by_id(db: Session, route_id: int) -> Optional[Route]:
    """Fetch a single route with its stops."""
    return (
        db.query(Route)
        .filter(Route.id == route_id)
        .first()
    )


def list_routes(
    db: Session,
    vehicle_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Route], int]:
    """List routes with optional filters."""
    query = db.query(Route)
    if vehicle_id:
        query = query.filter(Route.vehicle_id == vehicle_id)
    if driver_id:
        query = query.filter(Route.driver_id == driver_id)

    total = query.count()
    routes = query.offset(skip).limit(limit).all()
    return routes, total


def plan_route(db: Session, data: RouteCreate) -> Route:
    """
    Create a new route with stops.

    The stops are optimized using nearest-neighbor for efficiency.
    Returns the created Route with all stops attached.
    """
    # Verify the vehicle exists
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle {data.vehicle_id} not found")

    # Convert stops to dicts for optimization
    stop_dicts = [
        {"lat": s.latitude, "lng": s.longitude, "data": s}
        for s in data.stops
    ]
    optimized = _optimize_stops(stop_dicts)

    # Create the route
    route = Route(
        vehicle_id=data.vehicle_id,
        driver_id=data.driver_id,
        start_location=data.start_location,
        end_location=data.end_location,
        status="planned",
        distance_km=Decimal("0.00"),
    )
    db.add(route)
    db.flush()  # Get the route ID before adding stops

    # Add the stops in optimized order
    total_distance = 0.0
    prev_lat = None
    prev_lng = None

    for i, sd in enumerate(optimized):
        stop = sd["data"]
        route_stop = RouteStop(
            route_id=route.id,
            sequence=stop.sequence,
            latitude=stop.latitude,
            longitude=stop.longitude,
            address=stop.address,
            planned_arrival=stop.planned_arrival,
        )
        db.add(route_stop)

        # Calculate distance incrementally
        if prev_lat and prev_lng:
            total_distance += _haversine_km(
                prev_lat, prev_lng, stop.latitude, stop.longitude
            )
        prev_lat = stop.latitude
        prev_lng = stop.longitude

    route.distance_km = Decimal(str(round(total_distance, 2)))
    db.commit()
    db.refresh(route)

    # Reload with stops
    db.expire(route)
    return route


def start_route(db: Session, route_id: int, started_at: Optional[datetime] = None) -> Route:
    """Mark a route as in-progress."""
    route = get_route_by_id(db, route_id)
    if not route:
        raise ValueError(f"Route {route_id} not found")

    if route.status != "planned":
        raise ValueError(f"Route is already {route.status}, cannot start")

    route.status = "in_progress"
    route.start_time = started_at or datetime.now(timezone.utc)
    db.commit()
    db.refresh(route)
    return route


def complete_route(db: Session, route_id: int) -> Route:
    """Mark a route as completed."""
    route = get_route_by_id(db, route_id)
    if not route:
        raise ValueError(f"Route {route_id} not found")

    if route.status != "in_progress":
        raise ValueError(f"Route is {route.status}, cannot complete")

    route.status = "completed"
    route.end_time = datetime.now(timezone.utc)
    db.commit()
    db.refresh(route)
    return route


def mark_stop_arrived(db: Session, stop_id: int) -> RouteStop:
    """Mark a route stop as arrived."""
    stop = db.query(RouteStop).filter(RouteStop.id == stop_id).first()
    if not stop:
        raise ValueError(f"Stop {stop_id} not found")

    stop.status = "arrived"
    stop.actual_arrival = datetime.now(timezone.utc)
    db.commit()
    db.refresh(stop)
    return stop
