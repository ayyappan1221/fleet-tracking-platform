"""Pydantic schema for dashboard summary statistics."""

from pydantic import BaseModel


class DashboardSummary(BaseModel):
    """Aggregated counts for the dashboard overview."""

    total_vehicles: int
    active_vehicles: int
    total_routes: int
    active_routes: int
    pending_maintenance: int
    unread_alerts: int
    total_geofences: int
