from pydantic import BaseModel, ConfigDict, Field


class CommentBase(BaseModel):
    text: str = Field(..., min_length=1, max_length=5000)


class CommentCreate(CommentBase):
    parent_id: int | None = None


class CommentUpdate(CommentBase):
    pass


class CommentOut(CommentBase):
    id: int
    content_id: int
    user_id: int
    created_at: str
    updated_at: str | None
    parent_id: int | None
    author_display_name: str

    model_config = ConfigDict(from_attributes=True)
