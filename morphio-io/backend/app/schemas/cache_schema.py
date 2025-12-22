from pydantic import BaseModel, ConfigDict, Field


class CacheConfig(BaseModel):
    expire: int = Field(default=300, description="Cache expiration time in seconds")
    key_prefix: str = Field(default="cache:", description="Prefix for cache keys")
    model_config = ConfigDict(
        json_schema_extra={"env": {"expire": "CACHE_EXPIRE", "key_prefix": "CACHE_KEY_PREFIX"}}
    )
