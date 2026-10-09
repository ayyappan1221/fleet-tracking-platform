from app.models.user import User
from app.models.otp import EmailOTP
from app.models.vehicle import Vehicle
from app.models.route import Route, RouteStop
from app.models.location import Location
from app.models.alert import Alert
from app.models.geofence import Geofence
from app.models.maintenance import Maintenance

from app.models.fuel import FuelLog
from app.models.idle import IdleEvent
from app.models.inspection import Inspection

__all__ = [
    "User", "Vehicle", "Route", "RouteStop",
    "Location", "Alert", "Geofence", "Maintenance",
    "FuelLog", "IdleEvent", "Inspection",
]
