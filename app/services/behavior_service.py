"""Driver behavior scoring based on recorded location speeds."""
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.location import Location
from app.models.route import Route


SPEEDING_DROP_POINTS = 5
BRAKE_DROP_POINTS = 7
ACCEL_DROP_POINTS = 5
HARSH_DELTA_KMH = 20.0


def _speed_limit() -> float:
    try:
        return float(getattr(settings, "SPEED_LIMIT_KMH", 100))
    except (TypeError, ValueError):
        return 100.0


def compute_score_from_speeds(speeds: List[Optional[float]], speed_limit: Optional[float] = None) -> Dict:
    limit = float(speed_limit) if speed_limit is not None else _speed_limit()
    clean = [float(s) for s in speeds if s is not None]
    speeding_events = sum(1 for s in clean if s > limit)
    harsh_braking = 0
    rapid_accel = 0
    for prev, curr in zip(clean, clean[1:]):
        if prev - curr > HARSH_DELTA_KMH:
            harsh_braking += 1
        if curr - prev > HARSH_DELTA_KMH:
            rapid_accel += 1
    score = 100 - (speeding_events * SPEEDING_DROP_POINTS) - (harsh_braking * BRAKE_DROP_POINTS) - (rapid_accel * ACCEL_DROP_POINTS)
    score = max(0, min(100, score))
    return {
        "score": float(score),
        "speeding_events": speeding_events,
        "harsh_braking_events": harsh_braking,
        "rapid_acceleration_events": rapid_accel,
        "samples": len(clean),
        "speed_limit_kmh": limit,
    }


def compute_vehicle_score(db: Session, vehicle_id: int) -> Dict:
    locs = db.query(Location).filter(Location.vehicle_id == vehicle_id).order_by(Location.recorded_at.asc(), Location.id.asc()).all()
    return compute_score_from_speeds([l.speed for l in locs])


def compute_route_score(db: Session, route_id: int) -> Dict:
    route = db.query(Route).filter(Route.id == route_id).first()
    if not route:
        raise ValueError(f"Route {route_id} not found")
    result = compute_vehicle_score(db, route.vehicle_id)
    result["route_id"] = route.id
    result["vehicle_id"] = route.vehicle_id
    result["driver_id"] = route.driver_id
    route.score = result["score"]
    db.commit()
    db.refresh(route)
    return result


def compute_driver_score(db: Session, driver_id: int) -> Dict:
    routes = db.query(Route).filter(Route.driver_id == driver_id).all()
    vehicle_ids = sorted({r.vehicle_id for r in routes})
    all_speeds: List[float] = []
    for vid in vehicle_ids:
        locs = db.query(Location).filter(Location.vehicle_id == vid).order_by(Location.recorded_at.asc(), Location.id.asc()).all()
        all_speeds.extend([l.speed for l in locs if l.speed is not None])
    if not all_speeds:
        locs = []
        result = compute_score_from_speeds([])
    else:
        result = compute_score_from_speeds(all_speeds)
    result["driver_id"] = driver_id
    result["routes"] = len(routes)
    result["vehicles"] = len(vehicle_ids)
    return result
