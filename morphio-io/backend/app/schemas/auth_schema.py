from datetime import datetime
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
)

from ..utils.enums import ResponseStatus, UserRole
from ..utils.error_handlers import ApplicationException


class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=50)
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str = Field(..., description="Password must be at least 8 characters long")

    @field_validator("password")
    def validate_password_complexity(cls, v):
        # Import here to avoid circular imports
        from ..services.security import is_password_complex

        try:
            is_password_complex(v)
        except ApplicationException as e:
            raise ValueError(e.message)
        return v

    @field_validator("display_name")
    def validate_display_name(cls, v):
        if "<script>" in v.lower():
            raise ValueError("Display name contains invalid characters")
        return v


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    display_name: Optional[str] = Field(None, min_length=1, max_length=50)
    role: Optional[UserRole] = None


class UserInDB(UserBase):
    id: int
    hashed_password: str
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

    model_config = ConfigDict(from_attributes=True)


class UserOut(UserBase):
    id: int
    created_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool
    content_count: int = 0

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("created_at", "last_login")
    def serialize_datetime(self, dt: datetime, _info):
        if dt:
            return dt.isoformat()
        return None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)


class Token(BaseModel):
    access_token: str
    refresh_token: str
    user: UserOut

    model_config = ConfigDict(from_attributes=True)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class SignupRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    display_name: str = Field(..., min_length=1, max_length=50)

    @field_validator("password")
    def validate_password_complexity(cls, v):
        # Import here to avoid circular imports
        from ..services.security import is_password_complex

        try:
            is_password_complex(v)
        except ApplicationException as e:
            raise ValueError(e.message)
        return v


class SigninRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class PasswordComplexity(BaseModel):
    min_length: int = 8
    require_upper: bool = True
    require_lower: bool = True
    require_digit: bool = True
    require_special: bool = True
    special_chars: str = "!@#$%^&*()-_=+{};:,<.>"


# API Response wrapper models - these match the actual response structure
class AuthTokenPayload(BaseModel):
    """Payload for auth token responses (login, register, refresh)."""

    access_token: str
    refresh_token: str = ""  # Not returned in JSON, set via cookie
    user: "UserOut"

    model_config = ConfigDict(from_attributes=True)


class AuthTokenResponse(BaseModel):
    """Wrapped response for auth token endpoints."""

    status: ResponseStatus
    message: str
    data: Optional[AuthTokenPayload] = None
    timestamp: Optional[datetime] = None

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat() if dt else None


class CsrfTokenPayload(BaseModel):
    """Payload for CSRF token response."""

    csrf_token: str


class CsrfTokenResponse(BaseModel):
    """Wrapped response for CSRF token endpoint."""

    status: ResponseStatus
    message: str
    data: Optional[CsrfTokenPayload] = None
    timestamp: Optional[datetime] = None

    @field_serializer("timestamp")
    def serialize_datetime(self, dt: datetime, _info):
        return dt.isoformat() if dt else None
