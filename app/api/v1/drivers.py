"""Driver self-service endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.common import ApiResponse
from app.services import behavior_service as behavior_svc

router = APIRouter(prefix="/drivers", tags=["drivers"])


@router.get("/me/score", response_model=ApiResponse)
def get_my_score(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = behavior_svc.compute_driver_score(db, current_user.id)
    return api_success(result, "Driver score computed")
