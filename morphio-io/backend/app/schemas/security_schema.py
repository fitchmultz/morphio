from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TokenPayload(BaseModel):
    sub: str = Field(..., description="Subject (user identifier)")
    exp: datetime = Field(..., description="Expiration time")
    iat: datetime = Field(..., description="Issued at time")
    type: str = Field(..., description="Token type (access or refresh)")
    jti: str | None = Field(None, description="JWT ID")
    family: str | None = Field(None, description="Refresh token family identifier")


class PasswordComplexity(BaseModel):
    min_length: int = Field(8, description="Minimum password length")
    require_upper: bool = Field(True, description="Require uppercase letter")
    require_lower: bool = Field(True, description="Require lowercase letter")
    require_digit: bool = Field(True, description="Require digit")
    require_special: bool = Field(True, description="Require special character")
    special_chars: str = Field('!@#$%^&*(),.?":{}|<>', description="Allowed special characters")

    model_config = ConfigDict()
