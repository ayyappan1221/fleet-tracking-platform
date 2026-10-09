"""IdleEvent model for vehicle idle tracking."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class IdleEvent(Base):
    """An idle episode detected for a vehicle."""

    __tablename__ = "idle_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    minutes: Mapped[float] = mapped_column(Float, default=0, nullable=False)

    vehicle = relationship("Vehicle")

    def __repr__(self):
        """Human readable label for logs and debugging."""
        return f"<IdleEvent id={self.id} vehicle_id={self.vehicle_id} minutes={self.minutes}>"
