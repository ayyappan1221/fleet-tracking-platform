"""
Inspection API endpoints.

All endpoints are under /api/inspections and require a valid JWT.
"""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.authorization import (
    is_manager,
    owned_vehicle_ids,
    require_vehicle_access,
)
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.inspection import (
    InspectionCreate,
    InspectionListResponse,
    InspectionRead,
)
from app.services import inspection_service as insp_svc

router = APIRouter(prefix="/inspections", tags=["inspections"])


@router.post(
    "/",
    response_model=ApiResponse[InspectionRead],
    status_code=status.HTTP_201_CREATED,
)
def create_inspection(
    inspection_data: InspectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Record a pre-trip/post-trip inspection for a vehicle."""
    try:
        require_vehicle_access(db, inspection_data.vehicle_id, current_user)
        record = insp_svc.create_inspection(
            db, inspection_data, inspector_id=current_user.id
        )
        return api_success(record, "Inspection recorded")
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )


@router.get("/", response_model=ApiResponse[InspectionListResponse])
def list_inspections(
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inspections: managers see the fleet, others see their own vehicles."""
    if is_manager(current_user):
        records, total = insp_svc.list_inspections(
            db, vehicle_id=vehicle_id, skip=skip, limit=limit
        )
        return api_success(
            {"inspections": records, "total": total},
            "Inspections fetched",
        )
    if vehicle_id is not None:
        require_vehicle_access(db, vehicle_id, current_user)
        records, total = insp_svc.list_inspections(
            db, vehicle_id=vehicle_id, skip=skip, limit=limit
        )
        return api_success(
            {"inspections": records, "total": total},
            "Inspections fetched",
        )
    scope = owned_vehicle_ids(db, current_user)
    records, total = insp_svc.list_inspections(
        db, skip=skip, limit=limit, vehicle_ids=scope
    )
    return api_success(
        {"inspections": records, "total": total},
        "Inspections fetched",
    )


@router.get(
    "/vehicle/{vehicle_id}",
    response_model=ApiResponse[InspectionListResponse],
)
def list_vehicle_inspections(
    vehicle_id: int,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List inspections for one vehicle."""
    require_vehicle_access(db, vehicle_id, current_user)
    records, total = insp_svc.list_inspections(
        db, vehicle_id=vehicle_id, skip=skip, limit=limit
    )
    return api_success(
        {"inspections": records, "total": total},
        "Inspections fetched",
    )
