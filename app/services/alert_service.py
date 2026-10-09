"""
Alert service layer - business logic for fleet notifications and warnings.
"""
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple

from sqlalchemy import desc, or_
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.schemas.alert import AlertCreate


def _ensure_aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def recent_alert_exists(
    db: Session, vehicle_id: int, alert_types: List[str], minutes: int = 5
) -> bool:
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    q = db.query(Alert).filter(Alert.vehicle_id == vehicle_id)
    if len(alert_types) == 1:
        q = q.filter(Alert.type == alert_types[0])
    else:
        q = q.filter(Alert.type.in_(alert_types))
    for alert in q.order_by(desc(Alert.created_at)).limit(20).all():
        created = _ensure_aware(alert.created_at)
        if created is not None and created >= cutoff:
            return True
    return False


def get_alert_by_id(db: Session, alert_id: int) -> Optional[Alert]:
    """Look up a single alert by its ID."""
    return db.query(Alert).filter(Alert.id == alert_id).first()


def list_alerts(
    db: Session,
    vehicle_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
    vehicle_ids: Optional[list] = None,
) -> Tuple[List[Alert], int]:
    """
    Get a paginated list of alerts.
    Optional filters: vehicle_id, is_read status.
    """
    query = db.query(Alert)
    if vehicle_id is not None:
        query = query.filter(Alert.vehicle_id == vehicle_id)
    if vehicle_ids is not None:
        query = query.filter(
            or_(Alert.vehicle_id.in_(vehicle_ids), Alert.vehicle_id.is_(None))
        )
    if is_read is not None:
        query = query.filter(Alert.is_read == is_read)

    total = query.count()
    alerts = (
        query.order_by(desc(Alert.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return alerts, total


def create_alert(db: Session, data: AlertCreate) -> Alert:
    """Create a new alert notification."""
    alert = Alert(
        vehicle_id=data.vehicle_id,
        type=data.type,
        severity=data.severity,
        message=data.message,
        is_read=False,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


def mark_alert_read(db: Session, alert_id: int) -> Optional[Alert]:
    """Mark an alert as read. Returns None if not found."""
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        return None

    alert.is_read = True
    db.commit()
    db.refresh(alert)
    return alert


def delete_alert(db: Session, alert_id: int) -> bool:
    """Remove an alert. Returns True if deleted."""
    alert = get_alert_by_id(db, alert_id)
    if not alert:
        return False

    db.delete(alert)
    db.commit()
    return True
