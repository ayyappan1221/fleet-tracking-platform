"""OTP request/verify payloads."""

from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class OTPRequest(BaseModel):
    email: EmailStr
    purpose: Literal['signup_verify', 'login_otp']


class OTPVerify(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=12)
    purpose: Literal['signup_verify', 'login_otp']
