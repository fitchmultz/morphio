"""Purpose: Define API schemas for content comments.
Responsibilities: Validate comment input and serialize comment responses.
Scope: Pydantic models for comment route payloads only.
Usage: Imported by content comment routes and services.
Invariants/Assumptions: Comment text is non-empty and bounded to 5,000 characters.
"""

from pydantic import BaseModel, ConfigDict, Field


class CommentBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class CommentCreate(CommentBase):
    parent_id: int | None = None


class CommentUpdate(CommentBase): ...


class CommentOut(CommentBase):
    id: int
    content_id: int
    user_id: int
    created_at: str
    updated_at: str | None
    parent_id: int | None
    author_display_name: str

    model_config = ConfigDict(from_attributes=True)
