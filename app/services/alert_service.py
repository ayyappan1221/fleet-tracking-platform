"""
Alert service layer - business logic for fleet notifications and warnings.
"""
from datetime import datetime, timezone
from typing import List, Optional, Tuple

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.schemas.alert import AlertCreate


def get_alert_by_id(db: Session, alert_id: int) -> Optional[Alert]:
    """Look up a single alert by its ID."""
    return db.query(Alert).filter(Alert.id == alert_id).first()


def list_alerts(
    db: Session,
    vehicle_id: Optional[int] = None,
    is_read: Optional[bool] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Alert], int]:
    """
    Get a paginated list of alerts.
    Optional filters: vehicle_id, is_read status.
    """
    query = db.query(Alert)
    if vehicle_id is not None:
        query = query.filter(Alert.vehicle_id == vehicle_id)
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
