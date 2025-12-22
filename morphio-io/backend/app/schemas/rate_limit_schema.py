from pydantic import BaseModel, ConfigDict, Field


class RateLimitConfig(BaseModel):
    limit: str = Field(..., description="Rate limit string (e.g., '5/minute')")
    key_func: str = Field(
        default="get_remote_address",
        description="Function to use as the rate limit key",
    )

    model_config = ConfigDict()
