"""
Report export API endpoints (CSV).

All endpoints are under /api/reports and require a valid JWT.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.authorization import (
    is_manager,
    owned_vehicle_ids,
    require_vehicle_access,
)
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.services import alert_service as alert_svc
from app.services import fuel_service as fuel_svc
from app.services import location_service as location_svc

router = APIRouter(prefix="/reports", tags=["reports"])


def _csv_response(filename: str, header: str, rows: list) -> Response:
    body = header + "\n" + "\n".join(rows)
    if rows:
        body += "\n"
    return Response(
        content=body,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


def _cutoff(days: int) -> datetime:
    days = max(1, min(int(days), 365))
    return datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days)


def _aware_or_naive(dt):
    if dt is None:
        return None
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


@router.get("/locations.csv")
def export_locations_csv(
    vehicle_id: Optional[int] = Query(default=None, ge=1),
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export location pings as CSV (timestamp,lat,lng,speed)."""
    cutoff = _cutoff(days)
    if vehicle_id is not None:
        require_vehicle_access(db, vehicle_id, current_user)
        locations, _ = location_svc.list_locations(
            db, vehicle_id=vehicle_id, skip=0, limit=10000
        )
    else:
        if not is_manager(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers can export fleet-wide locations",
            )
        locations, _ = location_svc.list_locations(db, skip=0, limit=10000)
    rows = []
    for loc in locations:
        recorded = _aware_or_naive(loc.recorded_at)
        if recorded is not None and recorded < cutoff:
            continue
        rows.append(
            f"{loc.recorded_at.isoformat() if loc.recorded_at else ''},"
            f"{loc.latitude},{loc.longitude},{loc.speed if loc.speed is not None else ''}"
        )
    return _csv_response("locations.csv", "timestamp,lat,lng,speed", rows)


@router.get("/alerts.csv")
def export_alerts_csv(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export scoped alerts as CSV."""
    cutoff = _cutoff(days)
    if is_manager(current_user):
        alerts, _ = alert_svc.list_alerts(db, skip=0, limit=10000)
    else:
        scope = owned_vehicle_ids(db, current_user)
        alerts, _ = alert_svc.list_alerts(db, skip=0, limit=10000, vehicle_ids=scope)
    rows = []
    for a in alerts:
        created = _aware_or_naive(a.created_at)
        if created is not None and created < cutoff:
            continue
        msg = (a.message or "").replace('"', '""')
        rows.append(
            f"{a.id},{a.vehicle_id if a.vehicle_id is not None else ''},"
            f"{a.type},{a.severity},\"{msg}\",{a.is_read},"
            f"{a.created_at.isoformat() if a.created_at else ''}"
        )
    return _csv_response(
        "alerts.csv", "id,vehicle_id,type,severity,message,is_read,created_at", rows
    )


@router.get("/fuel.csv")
def export_fuel_csv(
    vehicle_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Export fuel logs as CSV."""
    if vehicle_id is not None:
        require_vehicle_access(db, vehicle_id, current_user)
        logs, _ = fuel_svc.list_for_vehicle(db, vehicle_id=vehicle_id, skip=0, limit=10000)
    else:
        if not is_manager(current_user):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers can export fleet-wide fuel logs",
            )
        logs, _ = fuel_svc.list_for_vehicle(db, vehicle_id=None, skip=0, limit=10000)
    rows = []
    for f in logs:
        note = (f.note or "").replace('"', '""')
        rows.append(
            f"{f.id},{f.vehicle_id},{f.liters},{f.cost},{f.odometer_km},"
            f"{f.filled_at.isoformat() if f.filled_at else ''},\"{note}\""
        )
    return _csv_response(
        "fuel.csv", "id,vehicle_id,liters,cost,odometer_km,filled_at,note", rows
    )
