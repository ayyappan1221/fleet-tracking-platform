from app.schemas.user import UserBase, UserCreate, UserRead, TokenResponse, TokenData
from app.schemas.vehicle import (
    VehicleBase,
    VehicleCreate,
    VehicleUpdate,
    VehicleRead,
    VehicleListResponse,
)
from app.schemas.route import (
    RouteBase,
    RouteCreate,
    RouteStart,
    RouteRead,
    RouteStopBase,
    RouteStopCreate,
    RouteStopRead,
    RouteListResponse,
)
from app.schemas.location import (
    LocationCreate,
    LocationRead,
    LocationListResponse,
)
from app.schemas.alert import (
    AlertCreate,
    AlertRead,
    AlertListResponse,
)
from app.schemas.geofence import (
    GeofenceCreate,
    GeofenceUpdate,
    GeofenceRead,
    GeofenceListResponse,
)
from app.schemas.maintenance import (
    MaintenanceCreate,
    MaintenanceUpdate,
    MaintenanceRead,
    MaintenanceListResponse,
)
from app.schemas.dashboard import DashboardSummary
from app.schemas.common import ApiResponse

__all__ = [
    "UserBase", "UserCreate", "UserRead", "TokenResponse", "TokenData",
    "VehicleBase", "VehicleCreate", "VehicleUpdate", "VehicleRead", "VehicleListResponse",
    "RouteBase", "RouteCreate", "RouteStart", "RouteRead",
    "RouteStopBase", "RouteStopCreate", "RouteStopRead", "RouteListResponse",
    "LocationCreate", "LocationRead", "LocationListResponse",
    "AlertCreate", "AlertRead", "AlertListResponse",
    "GeofenceCreate", "GeofenceUpdate", "GeofenceRead", "GeofenceListResponse",
    "MaintenanceCreate", "MaintenanceUpdate", "MaintenanceRead", "MaintenanceListResponse",
    "DashboardSummary",
    "ApiResponse",
]
