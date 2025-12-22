"""
Security type definitions.
"""

from pydantic import BaseModel, Field


class URLValidatorConfig(BaseModel):
    """Configuration for URL validation."""

    allowed_schemes: set[str] = Field(default_factory=lambda: {"http", "https"})
    block_loopback: bool = True
    block_private: bool = True
    block_link_local: bool = True
    block_reserved: bool = True
    block_multicast: bool = True
    custom_blocked_cidrs: list[str] = Field(default_factory=list)
    custom_allowed_cidrs: list[str] = Field(default_factory=list)
    # For DNS rebinding protection, fail closed on resolution errors
    block_on_resolution_error: bool = True
