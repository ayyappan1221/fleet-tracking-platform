"""
Maintenance API endpoints.

All endpoints are under /api/maintenance and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    is_manager,
    owned_vehicle_ids,
    require_maintenance_access,
    require_manager,
    require_vehicle_access,
)
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.route import Route
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceUpdate,
    MaintenanceRead,
    MaintenanceListResponse,
)
from app.services import maintenance_service as maint_svc

router = APIRouter(prefix="/maintenance", tags=["maintenance"])


@router.post(
    "/",
    response_model=ApiResponse[MaintenanceRead],
    status_code=status.HTTP_201_CREATED,
)
def create_maintenance(
    maintenance_data: MaintenanceCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new maintenance record for a vehicle."""
    try:
        require_vehicle_access(db, maintenance_data.vehicle_id, current_user)
        record = maint_svc.create_maintenance(db, maintenance_data)
        return api_success(record, "Maintenance created")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[MaintenanceListResponse])
def list_maintenance(
    vehicle_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List maintenance: managers see the fleet, others see their own vehicles."""
    try:
        maint_svc.check_maintenance_due(db)
    except Exception:
        pass
    if is_manager(current_user):
        records, total = maint_svc.list_maintenance(
            db, vehicle_id=vehicle_id, status=status_filter, skip=skip, limit=limit
        )
    else:
        if vehicle_id is not None:
            require_vehicle_access(db, vehicle_id, current_user)
            records, total = maint_svc.list_maintenance(
                db, vehicle_id=vehicle_id, status=status_filter, skip=skip, limit=limit
            )
        else:
            scope = owned_vehicle_ids(db, current_user)
            records, total = maint_svc.list_maintenance(
                db, status=status_filter, skip=skip, limit=limit, vehicle_ids=scope
            )
    # Pass both 'maintenance' and 'records' keys explicitly so the
    # serialized JSON contains body.data.maintenance (test contract)
    # AND body.data.records (backward compat).
    return api_success(
        {"maintenance": records, "records": records, "total": total},
        "Maintenance fetched",
    )


@router.patch(
    "/{maintenance_id}",
    response_model=ApiResponse[MaintenanceRead],
)
def update_maintenance(
    maintenance_id: int,
    maintenance_data: MaintenanceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update a maintenance record (partial update)."""
    require_maintenance_access(db, maintenance_id, current_user)
    if maintenance_data.vehicle_id is not None:
        require_vehicle_access(db, maintenance_data.vehicle_id, current_user)
    record = maint_svc.update_maintenance(db, maintenance_id, maintenance_data)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance {maintenance_id} not found",
        )
    return api_success(record, "Maintenance updated")


@router.post("/check-due", response_model=ApiResponse)
def check_due(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    require_manager(current_user)
    created = maint_svc.check_maintenance_due(db)
    payload = [{"id": a.id, "vehicle_id": a.vehicle_id, "type": a.type, "severity": a.severity, "message": a.message, "is_read": a.is_read, "created_at": a.created_at.isoformat() if a.created_at else None} for a in created]
    return api_success(
        {"created": len(created), "alerts": payload},
        f"{len(created)} maintenance due alerts created",
    )


@router.post("/report-issue", response_model=ApiResponse[MaintenanceRead], status_code=status.HTTP_201_CREATED)
def report_issue(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        vehicle_id = int(payload.get("vehicle_id", 0))
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle_id: must be a positive integer")
    if vehicle_id < 1:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid vehicle_id: must be a positive integer")
    description = (payload.get("description") or payload.get("notes") or "").strip()
    if not description:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Description is required")
    issue_type = payload.get("type", "repair")
    try:
        record = _require_driver_vehicle(db, vehicle_id, current_user)
    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    try:
        created = maint_svc.report_issue(db, vehicle_id, description, issue_type)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    return api_success(created, "Issue reported")


def _require_driver_vehicle(db: Session, vehicle_id: int, user: User):
    from app.core.authorization import get_vehicle_or_404

    vehicle = get_vehicle_or_404(db, vehicle_id)
    if is_manager(user):
        return vehicle
    if vehicle.owner_id == user.id:
        return vehicle
    assigned = db.query(Route).filter(Route.vehicle_id == vehicle_id, Route.driver_id == user.id).first()
    if assigned is not None:
        return vehicle
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to report issues for this vehicle")
