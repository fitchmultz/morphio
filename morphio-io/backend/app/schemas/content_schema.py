from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth_schema import UserOut
from .template_schema import TemplateOut


class ContentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    is_published: bool = False


class ContentCreate(BaseModel):
    title: str
    content: str
    user_id: Optional[int] = None
    template_id: Optional[int] = None
    tags: List[str] = []


class ContentUpdate(BaseModel):
    id: Optional[int] = None
    title: Optional[str] = Field(None, min_length=1, max_length=200)
    content: Optional[str] = Field(None, min_length=1)
    is_published: Optional[bool] = None
    tags: Optional[List[str]] = None


class ContentInDB(ContentBase):
    id: int
    user_id: int
    template_id: Optional[int] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    view_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ContentOut(ContentInDB):
    tags: List[str]
    user: UserOut
    template: Optional[TemplateOut] = None

    model_config = ConfigDict(from_attributes=True)

    @field_validator("title", mode="before")
    @classmethod
    def enforce_nonempty_title(cls, value: str) -> str:
        """Convert empty or whitespace-only titles to 'Untitled'."""
        if not value or not value.strip():
            return "Untitled"
        return value


class ContentGenerationResult(BaseModel):
    content_id: int = Field(..., json_schema_extra={"description": "ID of the generated content"})
    title: str = Field(..., json_schema_extra={"description": "Title of the generated content"})
    content: str = Field(..., json_schema_extra={"description": "Generated content text"})
    user_id: int = Field(
        ...,
        json_schema_extra={"description": "ID of the user who generated the content"},
    )
    template_id: int = Field(
        ..., json_schema_extra={"description": "ID of the template used for generation"}
    )


class ContentTitleUpdate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
