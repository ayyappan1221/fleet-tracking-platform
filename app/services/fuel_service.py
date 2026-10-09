"""
Fuel service layer - business logic for fuel fill tracking and efficiency.
"""
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

from sqlalchemy import asc
from sqlalchemy.orm import Session

from app.models.fuel import FuelLog
from app.models.vehicle import Vehicle
from app.schemas.fuel import FuelCreate


def get_fill_by_id(db: Session, fill_id: int) -> Optional[FuelLog]:
    """Look up a single fuel log by its ID."""
    return db.query(FuelLog).filter(FuelLog.id == fill_id).first()


def list_for_vehicle(
    db: Session,
    vehicle_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
    vehicle_ids: Optional[list] = None,
) -> Tuple[List[FuelLog], int]:
    """Get a paginated list of fuel logs, optionally scoped to owned vehicles."""
    query = db.query(FuelLog)
    if vehicle_id:
        query = query.filter(FuelLog.vehicle_id == vehicle_id)
    if vehicle_ids is not None:
        query = query.filter(FuelLog.vehicle_id.in_(vehicle_ids))
    total = query.count()
    logs = (
        query.order_by(FuelLog.filled_at.desc(), FuelLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return logs, total


def log_fill(db: Session, data: FuelCreate) -> FuelLog:
    """
    Record a new fuel fill-up for a vehicle.
    The vehicle must already exist.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == data.vehicle_id).first()
    if not vehicle:
        raise ValueError(f"Vehicle {data.vehicle_id} not found")

    fill = FuelLog(
        vehicle_id=data.vehicle_id,
        liters=data.liters,
        cost=data.cost or 0,
        odometer_km=data.odometer_km,
        note=data.note,
    )
    db.add(fill)
    db.commit()
    db.refresh(fill)
    try:
        _check_efficiency_drop(db, data.vehicle_id)
    except Exception:
        pass
    return fill


def efficiency_stats(db: Session, vehicle_id: int) -> Dict:
    """
    Compute fuel efficiency from odometer deltas between consecutive fills.

    Fills are ordered by odometer ascending; each interval's km/L comes
    from the odometer delta divided by the later fill's liters.
    """
    fills = (
        db.query(FuelLog)
        .filter(FuelLog.vehicle_id == vehicle_id)
        .order_by(asc(FuelLog.odometer_km), asc(FuelLog.id))
        .all()
    )
    total_liters = round(float(sum(f.liters or 0 for f in fills)), 2)
    total_cost = round(float(sum(f.cost or 0 for f in fills)), 2)

    total_km = 0.0
    liters_in_intervals = 0.0
    for prev, curr in zip(fills, fills[1:]):
        km = float(curr.odometer_km or 0) - float(prev.odometer_km or 0)
        if km <= 0 or not curr.liters or curr.liters <= 0:
            continue
        total_km += km
        liters_in_intervals += float(curr.liters)
    total_km = round(total_km, 2)

    km_per_liter = (
        round(total_km / liters_in_intervals, 2) if liters_in_intervals > 0 else None
    )
    cost_per_km = round(total_cost / total_km, 2) if total_km > 0 else None

    return {
        "fills": len(fills),
        "total_liters": total_liters,
        "total_cost": total_cost,
        "total_km": total_km,
        "km_per_liter": km_per_liter,
        "cost_per_km": cost_per_km,
    }


def _check_efficiency_drop(db: Session, vehicle_id: int) -> None:
    """Create a 'fuel' warning alert when the latest km/L drops >20% vs prior average."""
    from app.models.alert import Alert
    from app.services import alert_service as alerts

    fills = (
        db.query(FuelLog)
        .filter(FuelLog.vehicle_id == vehicle_id)
        .order_by(asc(FuelLog.odometer_km), asc(FuelLog.id))
        .all()
    )
    intervals = []
    for prev, curr in zip(fills, fills[1:]):
        km = float(curr.odometer_km or 0) - float(prev.odometer_km or 0)
        if km <= 0 or not curr.liters or curr.liters <= 0:
            continue
        intervals.append(km / float(curr.liters))
    if len(intervals) < 2:
        return
    latest = intervals[-1]
    prior_avg = sum(intervals[:-1]) / len(intervals[:-1])
    if prior_avg <= 0:
        return
    if latest < 0.8 * prior_avg:
        if not alerts.recent_alert_exists(db, vehicle_id, ["fuel"], minutes=5):
            db.add(Alert(
                vehicle_id=vehicle_id,
                type="fuel",
                severity="warning",
                message=(
                    f"Fuel efficiency drop: latest {latest:.1f} km/L is more than "
                    f"20% below the prior average {prior_avg:.1f} km/L "
                    f"(vehicle {vehicle_id})"
                ),
            ))
            db.commit()
