from typing import List

from pydantic import BaseModel, Field
from pydantic.config import ConfigDict


class TagBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=50)


class TagCreate(TagBase):
    pass


class TagUpdate(TagBase):
    pass


class TagInDB(TagBase):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TagOut(TagInDB):
    pass


class ContentTagsUpdate(BaseModel):
    content_id: int
    tag_ids: List[int]


class TagWithContentCount(TagOut):
    content_count: int


class PopularTags(BaseModel):
    tags: List[TagWithContentCount]
