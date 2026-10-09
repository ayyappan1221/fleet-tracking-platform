"""
Inspection service layer - business logic for DVIR-lite vehicle inspections.
"""
from typing import List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.inspection import Inspection
from app.models.vehicle import Vehicle
from app.schemas.inspection import InspectionCreate


def get_inspection_by_id(db: Session, inspection_id: int) -> Optional[Inspection]:
    """Look up a single inspection by its ID."""
    return db.query(Inspection).filter(Inspection.id == inspection_id).first()


def list_inspections(
    db: Session,
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    vehicle_ids: Optional[list] = None,
) -> Tuple[List[Inspection], int]:
    """Get a paginated list of inspections, optionally scoped to owned vehicles."""
    query = db.query(Inspection)
    if vehicle_id:
        query = query.filter(Inspection.vehicle_id == vehicle_id)
    if vehicle_ids is not None:
        query = query.filter(Inspection.vehicle_id.in_(vehicle_ids))
    total = query.count()
    records = (
        query.order_by(desc(Inspection.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records, total


def create_inspection(
    db: Session, data: InspectionCreate, inspector_id: int
) -> Inspection:
    """
    Record a new inspection. A failed inspection auto-creates a
    'maintenance' alert with 'high' severity.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle {data.vehicle_id} not found")

    record = Inspection(
        vehicle_id=data.vehicle_id,
        inspector_id=inspector_id,
        type=data.type,
        passed=data.passed,
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    if not record.passed:
        try:
            from app.models.alert import Alert

            db.add(Alert(
                vehicle_id=data.vehicle_id,
                type="maintenance",
                severity="high",
                message=(
                    f"Failed {data.type} inspection for vehicle {data.vehicle_id} "
                    f"by inspector {inspector_id}"
                ),
            ))
            db.commit()
            db.refresh(record)
        except Exception:
            db.rollback()
    return record
