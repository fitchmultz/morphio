"""Purpose: Define API schemas for content tags.
Responsibilities: Validate tag mutations and serialize tag response shapes.
Scope: Pydantic models for tag route payloads only.
Usage: Imported by content tag routes and services.
Invariants/Assumptions: Tag names are non-empty and bounded to 50 characters.
"""

from pydantic import BaseModel, ConfigDict, Field


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TagCreate(TagBase): ...


class TagUpdate(TagBase): ...


class TagInDB(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TagOut(TagInDB): ...


class ContentTagsUpdate(BaseModel):
    content_id: int
    tag_ids: list[int]


class TagWithContentCount(TagOut):
    content_count: int


class PopularTags(BaseModel):
    tags: list[TagWithContentCount]
