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

from ..services.security import is_password_complex
from ..utils.enums import UserRole


class UserBase(BaseModel):
    email: EmailStr
    display_name: str = Field(..., min_length=1, max_length=50)
    role: UserRole = UserRole.USER


class UserCreate(UserBase):
    password: str = Field(..., description="Password must be at least 8 characters long")

    @field_validator("password")
    def validate_password_complexity(cls, v):
        if not is_password_complex(v):
            raise ValueError(
                "Password must contain at least one uppercase letter, one lowercase "
                "letter, one digit, and one special character"
            )
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


class UserPasswordChange(BaseModel):
    current_password: str
    new_password: str = Field(..., min_length=8)
