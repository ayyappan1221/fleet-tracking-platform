"""
Dashboard API endpoints.

All endpoints are under /api/dashboard and require a valid JWT.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.authorization import is_manager, require_manager
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.route import Route
from app.models.user import User
from app.models.vehicle import Vehicle
from app.schemas.common import ApiResponse
from app.schemas.dashboard import DashboardSummary
from app.services import dashboard_service as dashboard_svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=ApiResponse[DashboardSummary])
def get_dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get dashboard statistics.

    Managers see the whole fleet; other roles see only their own vehicles
    (owned, or assigned as route driver) plus global alerts.
    """
    if is_manager(current_user):
        summary = dashboard_svc.get_summary(db)
    else:
        owned = {
            v_id
            for (v_id,) in db.query(Vehicle.id)
            .filter(Vehicle.owner_id == current_user.id)
            .all()
        }
        driven = {
            vehicle_id
            for (vehicle_id,) in db.query(Route.vehicle_id)
            .filter(Route.driver_id == current_user.id)
            .all()
        }
        summary = dashboard_svc.get_summary(
            db,
            vehicle_ids=sorted(owned | driven),
            owner_id=current_user.id,
        )
    return api_success(summary, "Dashboard summary fetched")


@router.get("/report", response_model=ApiResponse)
def get_fleet_report(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_manager(current_user)
    report = dashboard_svc.get_report(db, days=days)
    return api_success(report, "Fleet report generated")
