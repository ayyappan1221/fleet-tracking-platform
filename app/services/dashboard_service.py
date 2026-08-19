"""
Dashboard service layer - aggregated statistics for the fleet overview.
"""
from typing import Dict

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.geofence import Geofence
from app.models.maintenance import Maintenance
from app.models.route import Route
from app.models.vehicle import Vehicle
from app.schemas.dashboard import DashboardSummary


def get_summary(db: Session) -> Dict[str, int]:
    """
    Compute aggregated fleet dashboard statistics.

    Returns a dict with exactly these 7 integer keys:
      total_vehicles, active_vehicles, total_routes, active_routes,
      pending_maintenance, unread_alerts, total_geofences
    """
    total_vehicles = db.query(Vehicle).count()
    active_vehicles = db.query(Vehicle).filter(Vehicle.status == "active").count()
    total_routes = db.query(Route).count()
    active_routes = db.query(Route).filter(Route.status == "in_progress").count()
    pending_maintenance = (
        db.query(Maintenance).filter(Maintenance.status != "completed").count()
    )
    unread_alerts = db.query(Alert).filter(Alert.is_read == False).count()  # noqa: E712
    total_geofences = db.query(Geofence).count()

    return {
        "total_vehicles": total_vehicles,
        "active_vehicles": active_vehicles,
        "total_routes": total_routes,
        "active_routes": active_routes,
        "pending_maintenance": pending_maintenance,
        "unread_alerts": unread_alerts,
        "total_geofences": total_geofences,
    }
