from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator


class UserBase(BaseModel):
    email: EmailStr
    name: str

    @field_validator('name')
    @classmethod
    def name_must_have_value(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class UserCreate(UserBase):
    password: str
    role: str = 'driver'

    @field_validator('role')
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = {'manager', 'driver', 'mechanic'}
        if v not in allowed:
            raise ValueError(f'Role must be one of {allowed}')
        return v


class UserRead(UserBase):
    id: int
    role: str
    is_active: bool
    created_at: datetime

    model_config = {'from_attributes': True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = 'bearer'
    expires_in: int


class TokenData(BaseModel):
    email: Optional[str] = None
    role: Optional[str] = None
