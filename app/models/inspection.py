"""Inspection model for DVIR-lite vehicle inspections."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Inspection(Base):
    """A pre-trip/post-trip vehicle inspection record."""

    __tablename__ = "inspections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), nullable=False)
    inspector_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), default="pre_trip", nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    vehicle = relationship("Vehicle")
    inspector = relationship("User")

    def __repr__(self):
        """Human readable label for logs and debugging."""
        return f"<Inspection id={self.id} vehicle_id={self.vehicle_id} type={self.type} passed={self.passed}>"
