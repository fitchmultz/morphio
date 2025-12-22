from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class UserBasicOut(BaseModel):
    id: int
    email: str
    display_name: str

    model_config = ConfigDict(from_attributes=True)


class SubscriptionOut(BaseModel):
    id: int
    user_id: int
    plan: str
    status: str
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None
    user: Optional[UserBasicOut] = None

    model_config = ConfigDict(from_attributes=True, json_encoders={datetime: str})
