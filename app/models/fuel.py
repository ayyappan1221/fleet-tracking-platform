"""FuelLog model for fuel fill tracking."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FuelLog(Base):
    """A fuel fill-up record linked to a vehicle."""

    __tablename__ = "fuel_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    liters: Mapped[float] = mapped_column(Float, nullable=False)
    cost: Mapped[float] = mapped_column(Float, default=0, nullable=False)
    odometer_km: Mapped[float] = mapped_column(Float, nullable=False)
    filled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    vehicle = relationship("Vehicle")

    def __repr__(self):
        """Human readable label for logs and debugging."""
        return f"<FuelLog id={self.id} vehicle_id={self.vehicle_id} liters={self.liters}>"
