"""
Geofence service layer - business logic for geographic boundary management.
"""
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.models.geofence import Geofence
from app.models.user import User
from app.schemas.geofence import GeofenceCreate, GeofenceUpdate


def parse_coordinates(raw: str) -> Dict[str, Any]:
    text = (raw or "").strip()
    if not text:
        return {"kind": "unknown"}
    try:
        data = json.loads(text)
        if isinstance(data, dict):
            if "polygon" in data:
                return {"kind": "polygon", "points": [(float(p[0]), float(p[1])) for p in data["polygon"]]}
            if "points" in data:
                return {"kind": "polygon", "points": [(float(p[0]), float(p[1])) for p in data["points"]]}
            if "bbox" in data:
                b = [float(x) for x in data["bbox"]]
                if len(b) == 4:
                    return {"kind": "bbox", "bbox": (b[0], b[1], b[2], b[3])}
            if "lat" in data and ("lng" in data or "lon" in data):
                lng = float(data.get("lng", data.get("lon")))
                return {"kind": "circle", "center": (float(data["lat"]), lng), "radius_km": float(data.get("radius_km", 1.0))}
        if isinstance(data, list):
            if len(data) == 4 and all(isinstance(x, (int, float)) for x in data):
                vals = [float(x) for x in data]
                return {"kind": "bbox", "bbox": (vals[0], vals[1], vals[2], vals[3])}
            pts = []
            for p in data:
                if isinstance(p, (list, tuple)) and len(p) >= 2:
                    pts.append((float(p[0]), float(p[1])))
                elif isinstance(p, dict) and "lat" in p:
                    pts.append((float(p["lat"]), float(p.get("lng", p.get("lon", 0)))))
            if len(pts) >= 3:
                return {"kind": "polygon", "points": pts}
            if len(pts) in (1, 2):
                return {"kind": "bbox", "bbox": (min(p[0] for p in pts) - 0.01, min(p[1] for p in pts) - 0.01, max(p[0] for p in pts) + 0.01, max(p[1] for p in pts) + 0.01)}
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        pass
    m = re.search(r"\(\((.*)\)\)", text)
    if m:
        try:
            pts = []
            for pair in m.group(1).split(","):
                parts = pair.strip().split()
                if len(parts) >= 2:
                    pts.append((float(parts[0]), float(parts[1])))
            if len(pts) >= 3:
                return {"kind": "polygon", "points": pts}
        except ValueError:
            pass
    nums = re.findall(r"-?\d+(?:\.\d+)?", text)
    if len(nums) >= 4:
        try:
            vals = [float(n) for n in nums[:4]]
            lat_vals = [vals[0], vals[2]]
            lng_vals = [vals[1], vals[3]]
            return {"kind": "bbox", "bbox": (min(lat_vals), min(lng_vals), max(lat_vals), max(lng_vals))}
        except ValueError:
            pass
    return {"kind": "unknown"}


def _point_in_polygon(lat: float, lng: float, points: List[Tuple[float, float]]) -> bool:
    inside = False
    n = len(points)
    j = n - 1
    for i in range(n):
        yi, xi = points[i][0], points[i][1]
        yj, xj = points[j][0], points[j][1]
        if ((yi > lat) != (yj > lat)) and (lng < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi):
            inside = not inside
        j = i
    return inside


def is_inside(lat: float, lng: float, parsed: Dict[str, Any]) -> bool:
    kind = parsed.get("kind")
    if kind == "polygon":
        return _point_in_polygon(lat, lng, parsed["points"])
    if kind == "bbox":
        min_lat, min_lng, max_lat, max_lng = parsed["bbox"]
        return min_lat <= lat <= max_lat and min_lng <= lng <= max_lng
    if kind == "circle":
        from app.services.route_service import _haversine_km
        center = parsed["center"]
        return _haversine_km(lat, lng, center[0], center[1]) <= parsed.get("radius_km", 1.0)
    return True


def is_breach(geofence_type: str, inside: bool) -> bool:
    if (geofence_type or "inclusion").lower() == "exclusion":
        return inside
    return not inside


def get_geofence_by_id(db: Session, geofence_id: int) -> Optional[Geofence]:
    """Look up a single geofence by its ID."""
    return db.query(Geofence).filter(Geofence.id == geofence_id).first()


def list_geofences(
    db: Session,
    owner_id: Optional[int] = None,
    skip: int = 0,
    limit: int = 50,
) -> Tuple[List[Geofence], int]:
    """
    Get a paginated list of geofences.
    If owner_id is provided, only returns geofences owned by that user.
    """
    query = db.query(Geofence)
    if owner_id:
        query = query.filter(Geofence.owner_id == owner_id)

    total = query.count()
    geofences = query.offset(skip).limit(limit).all()
    return geofences, total


def create_geofence(db: Session, owner_id: int, data: GeofenceCreate) -> Geofence:
    """
    Create a new geofence boundary.
    The owner_id should come from the authenticated user.
    """
    owner = db.query(User).filter(User.id == owner_id).first()
    if not owner:
        raise ValueError("Owner user not found")

    geofence = Geofence(
        owner_id=owner_id,
        name=data.name,
        type=data.type,
        coordinates=data.coordinates,
        is_active=True,
    )
    db.add(geofence)
    db.commit()
    db.refresh(geofence)
    return geofence


def update_geofence(
    db: Session, geofence_id: int, data: GeofenceUpdate
) -> Optional[Geofence]:
    """
    Update geofence details. Only non-None fields are updated.
    """
    geofence = get_geofence_by_id(db, geofence_id)
    if not geofence:
        return None

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(geofence, field, value)

    db.commit()
    db.refresh(geofence)
    return geofence


def delete_geofence(db: Session, geofence_id: int) -> bool:
    """Remove a geofence. Returns True if deleted."""
    geofence = get_geofence_by_id(db, geofence_id)
    if not geofence:
        return False

    db.delete(geofence)
    db.commit()
    return True
