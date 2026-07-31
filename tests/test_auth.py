"""
Tests for user model.
"""
import pytest
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password, create_access_token, decode_access_token
from app.models.user import User
from app.schemas.user import UserCreate


def test_hash_and_verify_password():
    """Test that password hashing and verification work."""
    password = "Str0ngP@ss!"
    hashed = hash_password(password)

    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_create_and_read_user(db_session: Session):
    """Test creating a user and reading it back."""
    user = User(
        email="test@example.com",
        name="Test User",
        password_hash=hash_password("password123"),
        role="manager",
    )
    db_session.add(user)
    db_session.commit()

    fetched = db_session.query(User).filter(User.email == "test@example.com").first()
    assert fetched is not None
    assert fetched.name == "Test User"
    assert fetched.role == "manager"


def test_jwt_token_roundtrip():
    """Test creating a JWT and decoding it back."""
    data = {"sub": "1", "email": "test@example.com", "role": "manager"}
    token = create_access_token(data)

    assert token is not None

    decoded = decode_access_token(token)
    assert decoded["email"] == "test@example.com"
    assert decoded["role"] == "manager"
