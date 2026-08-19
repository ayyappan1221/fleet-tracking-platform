"""
Maintenance service layer - business logic for vehicle maintenance records.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.maintenance import Maintenance
from app.models.vehicle import Vehicle
from app.schemas.maintenance import MaintenanceCreate, MaintenanceUpdate


def get_maintenance_by_id(db: Session, maintenance_id: int) -> Optional[Maintenance]:
    """Look up a single maintenance record by its ID."""
    return db.query(Maintenance).filter(Maintenance.id == maintenance_id).first()


def list_maintenance(
    db: Session,
    vehicle_id: Optional[int] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Maintenance], int]:
    """
    Get a paginated list of maintenance records.
    Optional filters: vehicle_id, status.
    """
    query = db.query(Maintenance)
    if vehicle_id:
        query = query.filter(Maintenance.vehicle_id == vehicle_id)
    if status:
        query = query.filter(Maintenance.status == status)

    total = query.count()
    records = (
        query.order_by(desc(Maintenance.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return records, total


def create_maintenance(db: Session, data: MaintenanceCreate) -> Maintenance:
    """
    Create a new maintenance record for a vehicle.
    The vehicle must already exist.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle {data.vehicle_id} not found")

    record = Maintenance(
        vehicle_id=data.vehicle_id,
        type=data.type,
        status=data.status,
        due_mileage=data.due_mileage,
        due_date=data.due_date,
        notes=data.notes,
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


def update_maintenance(
    db: Session, maintenance_id: int, data: MaintenanceUpdate
) -> Optional[Maintenance]:
    """
    Update maintenance record details. Only non-None fields are updated.
    If status is changed to 'completed', sets completed_at timestamp.
    """
    record = get_maintenance_by_id(db, maintenance_id)
    if not record:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(record, field, value)

    # Auto-set completed_at when status transitions to completed
    if data.status == "completed" and record.completed_at is None:
        record.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(record)
    return record


def delete_maintenance(db: Session, maintenance_id: int) -> bool:
    """Remove a maintenance record. Returns True if deleted."""
    record = get_maintenance_by_id(db, maintenance_id)
    if not record:
        return False

    db.delete(record)
    db.commit()
    return True
