from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import List, Optional

from sqlalchemy import (
    String,
    ForeignKey,
    Numeric,
    Integer,
    DateTime,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Route(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    driver_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    start_location: Mapped[Optional[str]] = mapped_column(String(255))
    end_location: Mapped[Optional[str]] = mapped_column(String(255))
    distance_km: Mapped[Decimal] = mapped_column(Numeric(8, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="planned")

    vehicle = relationship("Vehicle", back_populates="routes")
    driver = relationship("User", backref="assigned_routes")
    stops = relationship("RouteStop", back_populates="route", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Route id={self.id} status={self.status}>"


class RouteStop(Base):
    __tablename__ = "route_stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer)
    latitude: Mapped[Optional[float]] = mapped_column()
    longitude: Mapped[Optional[float]] = mapped_column()
    address: Mapped[Optional[str]] = mapped_column(String(255))
    planned_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    actual_arrival: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="pending")

    route = relationship("Route", back_populates="stops")

    def __repr__(self):
        return f"<RouteStop route_id={self.route_id} seq={self.sequence}>"
