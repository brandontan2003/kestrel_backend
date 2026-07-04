from pydantic import EmailStr, field_validator

from app.dto.base import BaseDTO


class RegisterRequest(BaseDTO):
    email: EmailStr
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def username_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Username cannot be blank")
        return v.strip()

    @field_validator("password")
    @classmethod
    def password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class LoginRequest(BaseDTO):
    email: EmailStr
    password: str


class AuthResponse(BaseDTO):
    access_token: str
    expires_in: int
    token_type: str = "bearer"


class TokenPair(BaseDTO):
    access_token: str
    refresh_token: str
