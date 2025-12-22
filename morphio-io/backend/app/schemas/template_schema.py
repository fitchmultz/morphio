from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict

from .auth_schema import UserOut


class TemplateBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    template_content: str = Field(..., min_length=1)
    is_default: bool = False


class TemplateCreate(TemplateBase):
    user_id: Optional[int] = None


class TemplateUpdate(BaseModel):
    name: Optional[str] = None
    template_content: Optional[str] = None


class TemplateInDB(TemplateBase):
    id: int
    user_id: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime] = None
    usage_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class TemplateOut(BaseModel):
    id: int
    name: str
    template_content: str
    user_id: Optional[int] = None
    is_default: bool
    created_at: datetime
    updated_at: Optional[datetime] = None
    usage_count: int = 0
    user: Optional[UserOut] = None

    model_config = ConfigDict(from_attributes=True)
