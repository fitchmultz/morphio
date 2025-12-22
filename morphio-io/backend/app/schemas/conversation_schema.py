from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ConversationMessageBase(BaseModel):
    role: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)


class ConversationMessageCreate(ConversationMessageBase):
    conversation_id: str


class ConversationMessageOut(ConversationMessageBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationRequest(BaseModel):
    message: str = Field(
        ..., min_length=1, max_length=5000, description="User message (max 5000 characters)"
    )
    conversation_id: Optional[str] = Field(
        default=None,
        description="Existing conversation to append to. If omitted, a new conversation is created.",
    )
    preserve_context: bool = Field(
        default=True,
        description=(
            "When false, a new conversation branch is created even if conversation_id is provided."
        ),
    )
    model: Optional[str] = Field(
        default=None,
        description="Optional override for the generation model.",
    )
    branch_from_id: Optional[str] = Field(
        default=None,
        description="Create a branched conversation that references this parent conversation ID.",
    )
    follow_up_type: Optional[str] = Field(
        default=None,
        description="Optional identifier for which quick action or suggestion was selected.",
    )


class ConversationResponse(BaseModel):
    conversation_id: str
    content_id: int
    updated_content: str
    model_used: str
    change_summary: List[str]
    notes: Optional[str] = None
    suggestions: List[str]
    messages: List[ConversationMessageOut]
    branch_parent_id: Optional[str] = None
    created_new_conversation: bool = False


class ConversationSummary(BaseModel):
    id: str
    content_id: int
    template_id: Optional[int] = None
    template_used: Optional[str] = None
    model: str
    parent_id: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    message_count: int

    model_config = ConfigDict(from_attributes=True)


class ConversationThreadOut(ConversationSummary):
    messages: List[ConversationMessageOut]

    model_config = ConfigDict(from_attributes=True)
