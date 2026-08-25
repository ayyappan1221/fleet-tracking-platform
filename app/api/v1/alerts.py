"""
Alert API endpoints.

All endpoints are under /api/alerts and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.alert import AlertCreate, AlertRead, AlertListResponse
from app.schemas.common import ApiResponse
from app.services import alert_service as alert_svc

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.post(
    "/",
    response_model=ApiResponse[AlertRead],
    status_code=status.HTTP_201_CREATED,
)
def create_alert(
    alert_data: AlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new fleet alert notification."""
    try:
        alert = alert_svc.create_alert(db, alert_data)
        return api_success(alert, "Alert created")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[AlertListResponse])
def list_alerts(
    vehicle_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List alerts, optionally filtered by vehicle_id or read status."""
    alerts, total = alert_svc.list_alerts(
        db, vehicle_id=vehicle_id, is_read=is_read, skip=skip, limit=limit
    )
    return api_success(
        {"alerts": alerts, "total": total},
        "Alerts fetched",
    )


@router.patch("/{alert_id}/read", response_model=ApiResponse[AlertRead])
def mark_alert_read(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Mark a single alert as read."""
    alert = alert_svc.mark_alert_read(db, alert_id)
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert {alert_id} not found",
        )
    return api_success(alert, "Alert marked as read")
