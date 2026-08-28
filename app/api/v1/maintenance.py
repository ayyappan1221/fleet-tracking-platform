"""
Maintenance API endpoints.

All endpoints are under /api/maintenance and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
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
    """List all maintenance records, optionally filtered by vehicle or status."""
    records, total = maint_svc.list_maintenance(
        db, vehicle_id=vehicle_id, status=status_filter, skip=skip, limit=limit
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
    record = maint_svc.update_maintenance(db, maintenance_id, maintenance_data)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Maintenance {maintenance_id} not found",
        )
    return api_success(record, "Maintenance updated")
