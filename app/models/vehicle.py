"""Vehicle model representing a single asset in the fleet."""
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import String, ForeignKey, Numeric, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Vehicle(Base):
    """A vehicle owned by a user, with current status and mileage."""
    __tablename__ = "vehicles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    fleet_id: Mapped[str] = mapped_column(String(50), nullable=True)
    license_plate: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    make: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(50), nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    vin: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="active", nullable=False)
    current_mileage: Mapped[Decimal] = mapped_column(
        Numeric(10, 2), default=0, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        default=lambda: datetime.now(timezone.utc),
    )

    owner = relationship("User", backref="vehicles")
    routes = relationship("Route", back_populates="vehicle", cascade="all, delete-orphan")

    def __repr__(self):
        """Human readable label for logs and debugging."""
        return f"<Vehicle {self.license_plate} ({self.make} {self.model})>"
