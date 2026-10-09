"""Authentication endpoints: register, email OTP, password login, OTP login."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.authorization import PRIVILEGED_ROLES
from app.core.config import settings
from app.core.database import get_db
from app.core.responses import api_success
from app.core.security import hash_password, verify_password, create_access_token
from app.models.user import User
from app.schemas.common import ApiResponse
from app.schemas.otp import OTPRequest, OTPVerify
from app.schemas.user import UserCreate, UserRead, TokenResponse
from app.services import otp_service
from app.services.otp_service import PURPOSE_LOGIN, PURPOSE_SIGNUP

router = APIRouter(
    prefix='/auth',
    tags=['authentication'],
)


def _dev_otp_payload(code: str, delivered: bool) -> dict:
    if settings.APP_ENV == 'production':
        return {}
    return {'dev_otp': code, 'delivered_via_email': delivered}


def _token_payload(user: User) -> dict:
    access_token = create_access_token(
        data={'sub': str(user.id), 'email': user.email, 'role': user.role},
    )
    return {
        'access_token': access_token,
        'token_type': 'bearer',
        'expires_in': settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    }


@router.post('/register', response_model=ApiResponse[dict], status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Create a new user account.

    Privileged roles (manager/admin/...) cannot be self-assigned via this
    public endpoint, except for the very first user (manager bootstrap).

    The account starts unverified: a 6-digit code is emailed (or returned as
    `dev_otp` outside production) and the account must be activated with
    POST /auth/verify-signup before any login succeeds.
    """
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Email already registered',
        )

    requested_role = (user_data.role or 'driver').strip().lower()
    if requested_role in PRIVILEGED_ROLES:
        # Legitimate manager bootstrap: only when no users exist yet.
        if db.query(User).count() > 0:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Cannot self-assign privileged role',
            )

    user = User(
        email=user_data.email,
        name=user_data.name,
        password_hash=hash_password(user_data.password),
        role=requested_role,
        email_verified=False,
    )
    db.add(user)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Could not register user',
        )
    db.refresh(user)

    try:
        _, code, delivered = otp_service.issue_otp(db, user.email, PURPOSE_SIGNUP)
    except ValueError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Verification code already sent. Wait a minute before retrying.',
        )
    payload = api_success(
        {
            **UserRead.model_validate(user).model_dump(),
            **_dev_otp_payload(code, delivered),
        },
        'User registered. Verify the emailed code to activate.',
    )
    return payload


@router.post('/request-otp', response_model=ApiResponse[dict])
def request_otp(body: OTPRequest, db: Session = Depends(get_db)):
    """Send a 6-digit code for signup verification or passwordless login."""
    email = str(body.email)
    if body.purpose == PURPOSE_LOGIN:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail='No account for this email',
            )
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Account is disabled',
            )
    try:
        _, code, delivered = otp_service.issue_otp(db, email, body.purpose)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail='Code already sent. Wait a minute before retrying.',
        )
    payload = api_success({'email': email}, 'Verification code sent')
    payload['data'].update(_dev_otp_payload(code, delivered))
    return payload


def _otp_error(status_detail: str) -> HTTPException:
    mapping = {
        'missing': (status.HTTP_404_NOT_FOUND, 'No active code. Request a new one.'),
        'expired': (status.HTTP_410_GONE, 'Code expired. Request a new one.'),
        'locked': (
            status.HTTP_429_TOO_MANY_REQUESTS,
            'Too many wrong attempts. Request a new code.',
        ),
        'mismatch': (status.HTTP_400_BAD_REQUEST, 'Incorrect code.'),
    }
    code, message = mapping.get(status_detail, (status.HTTP_400_BAD_REQUEST, 'Invalid code.'))
    return HTTPException(status_code=code, detail=message)


@router.post('/verify-signup', response_model=ApiResponse[UserRead])
def verify_signup(body: OTPVerify, db: Session = Depends(get_db)):
    """Activate a freshly registered account with its emailed code."""
    if body.purpose != PURPOSE_SIGNUP:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Use a signup verification code here',
        )
    try:
        otp_service.check_otp(db, str(body.email), body.code, PURPOSE_SIGNUP)
    except ValueError as exc:
        raise _otp_error(str(exc))
    user = db.query(User).filter(User.email == str(body.email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No account for this email',
        )
    user.email_verified = True
    db.commit()
    db.refresh(user)
    return api_success(user, 'Email verified. You can now log in.')


@router.post('/login', response_model=ApiResponse[TokenResponse])
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Authenticate with email + password. Requires a verified email."""
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
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Email not verified. Enter the code sent at signup.',
        )

    return api_success(_token_payload(user), 'Login successful')


@router.post('/login/otp', response_model=ApiResponse[TokenResponse])
def login_with_otp(body: OTPVerify, db: Session = Depends(get_db)):
    """Passwordless login with an emailed code (request via POST /auth/request-otp)."""
    if body.purpose != PURPOSE_LOGIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail='Use a login code here',
        )
    try:
        otp_service.check_otp(db, str(body.email), body.code, PURPOSE_LOGIN)
    except ValueError as exc:
        raise _otp_error(str(exc))
    user = db.query(User).filter(User.email == str(body.email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail='No account for this email',
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Account is disabled',
        )
    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Email not verified. Complete signup verification first.',
        )
    return api_success(_token_payload(user), 'Login successful')
