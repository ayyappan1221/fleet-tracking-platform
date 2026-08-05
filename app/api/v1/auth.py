"""Authentication endpoints: register and login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.user import UserCreate, UserRead, TokenResponse

router = APIRouter(
    prefix='/auth',
    tags=['authentication'],
)


@router.post('/register', response_model=ApiResponse[UserRead], status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account."""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered',
        )

    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password),
        role=user_data.role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return api_success(user, 'User registered')


@router.post('/login', response_model=ApiResponse[TokenResponse])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate a user and return a JWT access token."""
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Incorrect email or password',
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is disabled',
        )

    access_token = create_access_token(
        data={'sub': str(user.id), 'email': user.email, 'role': user.role},
    )
    token = {
        'access_token': access_token,
        'token_type': 'bearer',
        'expires_in': settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }
    return api_success(token, 'Login successful')