"""
Dashboard service layer - aggregated statistics for the fleet overview.
"""
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.geofence import Geofence
from app.models.location import Location
from app.models.maintenance import Maintenance
from app.models.route import Route
from app.models.vehicle import Vehicle
from app.schemas.dashboard import DashboardSummary


def get_summary(
    db: Session,
    vehicle_ids: list[int] | None = None,
    owner_id: int | None = None,
) -> Dict[str, int]:
    """
    Compute aggregated dashboard statistics.

    Returns a dict with exactly these 7 integer keys:
      total_vehicles, active_vehicles, total_routes, active_routes,
      pending_maintenance, unread_alerts, total_geofences

    Pass vehicle_ids to scope every vehicle-linked metric to those vehicles
    (global alerts with no vehicle stay visible); pass owner_id to scope the
    geofence count to that owner's zones. Both default to None (fleet-wide).
    """
    from sqlalchemy import or_

    vehicles = db.query(Vehicle)
    routes = db.query(Route)
    maintenance = db.query(Maintenance)
    alerts = db.query(Alert)
    geofences = db.query(Geofence)
    if vehicle_ids is not None:
        vehicles = vehicles.filter(Vehicle.id.in_(vehicle_ids))
        routes = routes.filter(Route.vehicle_id.in_(vehicle_ids))
        maintenance = maintenance.filter(Maintenance.vehicle_id.in_(vehicle_ids))
        alerts = alerts.filter(
            or_(Alert.vehicle_id.in_(vehicle_ids), Alert.vehicle_id.is_(None))
        )
    if owner_id is not None:
        geofences = geofences.filter(Geofence.owner_id == owner_id)

    total_vehicles = vehicles.count()
    active_vehicles = vehicles.filter(Vehicle.status == "active").count()
    total_routes = routes.count()
    active_routes = routes.filter(Route.status == "in_progress").count()
    pending_maintenance = maintenance.filter(Maintenance.status != "completed").count()
    unread_alerts = alerts.filter(Alert.is_read == False).count()  # noqa: E712
    total_geofences = geofences.count()

    return {
        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "total_routes": total_routes,
        "active_routes": active_routes,
        "pending_maintenance": pending_maintenance,
        "unread_alerts": unread_alerts,
        "total_geofences": total_geofences,
    }


def get_report(db: Session, days: int = 30) -> Dict:
    from app.services import behavior_service as behavior

    days = max(1, min(int(days), 365))
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    routes = db.query(Route).all()

    def _aware(dt):
        if dt is None:
            return None
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

    recent_routes = []
    for r in routes:
        start = _aware(r.start_time)
        if start is None or start >= cutoff:
            recent_routes.append(r)
    trips = len(recent_routes)
    distance = round(float(sum(float(r.distance_km or 0) for r in recent_routes)), 2)

    alerts = db.query(Alert).all()
    recent_alerts = [a for a in alerts if (_aware(a.created_at) or cutoff) >= cutoff]
    alerts_by_type = dict(Counter(a.type for a in recent_alerts))

    maint = db.query(Maintenance).all()
    maintenance_by_status = dict(Counter(m.status for m in maint))
    pending = sum(1 for m in maint if m.status != "completed")

    scores = []
    for v in db.query(Vehicle).all():
        try:
            res = behavior.compute_vehicle_score(db, v.id)
            if res.get("samples", 0) > 0:
                scores.append(res["score"])
        except Exception:
            continue
    avg_score = round(sum(scores) / len(scores), 2) if scores else None

    # --- Cost KPIs: fuel + maintenance spend inside the window ---
    from app.models.fuel import FuelLog
    from app.models.route import RouteStop

    def _windowed(dt):
        aware = _aware(dt)
        return aware is not None and aware >= cutoff

    fuel_logs = db.query(FuelLog).all()
    window_fuel = [f for f in fuel_logs if _windowed(f.filled_at)]
    fuel_cost_total = round(float(sum(float(f.cost or 0) for f in window_fuel)), 2)
    fuel_liters_total = round(float(sum(float(f.liters or 0) for f in window_fuel)), 2)

    maint_records = db.query(Maintenance).all()
    maintenance_cost_total = round(float(sum(
        float(m.cost or 0)
        for m in maint_records
        if m.status == "completed" and _windowed(m.completed_at or m.created_at)
    )), 2)

    cost_per_km = (
        round((fuel_cost_total + maintenance_cost_total) / distance, 2)
        if distance > 0 else None
    )

    # --- Utilization: active vehicles with >=1 ping in window / total ---
    total_vehicles = db.query(Vehicle).count()
    active_vehicle_ids = {
        v.id for v in db.query(Vehicle).filter(Vehicle.status == "active").all()
    }
    pinged_vehicle_ids = set()
    for loc in db.query(Location.vehicle_id, Location.recorded_at).all():
        if _windowed(loc.recorded_at):
            pinged_vehicle_ids.add(loc.vehicle_id)
    active_pinged = len(active_vehicle_ids & pinged_vehicle_ids)
    utilization = (
        round(active_pinged / total_vehicles * 100, 2) if total_vehicles > 0 else None
    )

    # --- On-time rate: arrived stops with actual <= planned / arrived ---
    arrived_stops = (
        db.query(RouteStop)
        .filter(RouteStop.actual_arrival.isnot(None))
        .all()
    )
    # Also treat status='arrived' without timestamp as arrived (late-unknown -> late).
    arrived_stops += (
        db.query(RouteStop)
        .filter(RouteStop.status == "arrived", RouteStop.actual_arrival.is_(None))
        .all()
    )
    on_time = 0
    for s in arrived_stops:
        planned = _aware(s.planned_arrival)
        actual = _aware(s.actual_arrival)
        if planned is None or actual is None:
            if actual is not None:
                on_time += 1
            continue
        if actual <= planned:
            on_time += 1
    on_time_rate = (
        round(on_time / len(arrived_stops) * 100, 2) if arrived_stops else None
    )

    return {
        "days": days,
        "trips": trips,
        "distance_km": distance,
        "alerts_by_type": alerts_by_type,
        "maintenance_by_status": maintenance_by_status,
        "pending_maintenance": pending,
        "avg_driver_score": avg_score,
        "fuel_cost_total": fuel_cost_total,
        "fuel_liters_total": fuel_liters_total,
        "maintenance_cost_total": maintenance_cost_total,
        "cost_per_km": cost_per_km,
        "utilization": utilization,
        "on_time_rate": on_time_rate,
        "summary": get_summary(db),
    }
