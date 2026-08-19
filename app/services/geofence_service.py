"""
Geofence service layer - business logic for geographic boundary management.
"""
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.geofence import Geofence
from app.models.user import User
from app.schemas.geofence import GeofenceCreate, GeofenceUpdate


def get_geofence_by_id(db: Session, geofence_id: int) -> Optional[Geofence]:
    """Look up a single geofence by its ID."""
    return db.query(Geofence).filter(Geofence.id == geofence_id).first()


def list_geofences(
    db: Session,
    owner_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Geofence], int]:
    """
    Get a paginated list of geofences.
    If owner_id is provided, only returns geofences owned by that user.
    """
    query = db.query(Geofence)
    if owner_id:
        query = query.filter(Geofence.owner_id == owner_id)

    total = query.count()
    geofences = query.offset(skip).limit(limit).all()
    return geofences, total


def create_geofence(db: Session, owner_id: int, data: GeofenceCreate) -> Geofence:
    """
    Create a new geofence boundary.
    The owner_id should come from the authenticated user.
    """
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner:
        raise ValueError("Owner user not found")

    geofence = Geofence(
        owner_id=owner_id,
        name=data.name,
        type=data.type,
        coordinates=data.coordinates,
        is_active=True,
    )
    db.add(geofence)
    db.commit()
    db.refresh(geofence)
    return geofence


def update_geofence(
    db: Session, geofence_id: int, data: GeofenceUpdate
) -> Optional[Geofence]:
    """
    Update geofence details. Only non-None fields are updated.
    """
    geofence = get_geofence_by_id(db, geofence_id)
    if not geofence:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(geofence, field, value)

    db.commit()
    db.refresh(geofence)
    return geofence


def delete_geofence(db: Session, geofence_id: int) -> bool:
    """Remove a geofence. Returns True if deleted."""
    geofence = get_geofence_by_id(db, geofence_id)
    if not geofence:
        return False

    db.delete(geofence)
    db.commit()
    return True
