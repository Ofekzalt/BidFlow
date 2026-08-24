import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from auth.constants import (
    ERROR_PASSWORD_TOO_SHORT,
    PASSWORD_MIN_LENGTH,
    TOKEN_TYPE,
)


class AuthRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email", mode="before")
    @classmethod
    def lowercase_email(cls, v: str) -> str:
        return v.lower()

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < PASSWORD_MIN_LENGTH:
            raise ValueError(
                ERROR_PASSWORD_TOO_SHORT.format(min_length=PASSWORD_MIN_LENGTH)
            )
        return v


class RegisterResponse(BaseModel):
    id: uuid.UUID
    email: str
    created_at: datetime


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = TOKEN_TYPE
