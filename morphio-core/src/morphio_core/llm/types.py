"""
LLM types and configuration models.

All config uses Pydantic with explicit fields - no global settings.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

# Type alias for provider factory functions
# A factory takes a ProviderConfig and returns an LLMProvider-compatible instance
# Uses Any for return type to avoid circular import with providers.base
ProviderFactory = Callable[["ProviderConfig"], Any]


class Message(BaseModel):
    """Universal message format."""

    model_config = ConfigDict(frozen=True)

    role: Literal["system", "user", "assistant"]
    content: str


class Usage(BaseModel):
    """Token usage information."""

    model_config = ConfigDict(frozen=True)

    prompt_tokens: int = 0
    completion_tokens: int = 0


class GenerationResult(BaseModel):
    """Response from any LLM provider."""

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    provider: str
    usage: Usage | None = None
    raw: Any | None = Field(default=None, repr=False, exclude=True)  # Debug only


# Streaming event types - use dataclasses for hot path performance
# (Pydantic construction per token can be expensive for long outputs)


@dataclass(frozen=True, slots=True)
class StreamDelta:
    """A chunk of streamed content."""

    text: str
    type: str = "delta"


@dataclass(frozen=True, slots=True)
class StreamDone:
    """End of stream marker with usage."""

    usage: Usage | None = None
    type: str = "done"


# Type alias for stream events
StreamEvent = StreamDelta | StreamDone


class ProviderConfig(BaseModel):
    """Configuration for a single provider."""

    api_key: SecretStr  # Secure handling of API keys
    default_model: str  # Opaque string - library doesn't validate model names
    default_max_tokens: int = Field(default=4096, gt=0)
    default_temperature: float = Field(default=1.0, ge=0.0, le=2.0)
    timeout: float = Field(default=30.0, gt=0)
    max_retries: int = Field(default=3, ge=0)


class LLMConfig(BaseModel):
    """Configuration for the LLM router - NO GLOBAL SETTINGS.

    Built-in providers (openai, anthropic, gemini) are configured via their
    respective fields. Custom providers can be added via custom_providers.

    Example with custom provider:
        def my_provider_factory(config: ProviderConfig) -> LLMProvider:
            return MyCustomProvider(api_key=config.api_key, ...)

        config = LLMConfig(
            custom_providers={"my-provider": my_provider_factory},
            custom_configs={"my-provider": ProviderConfig(api_key=..., default_model="...")},
            default_provider="my-provider",
        )
    """

    # Built-in provider configs
    openai: ProviderConfig | None = None
    anthropic: ProviderConfig | None = None
    gemini: ProviderConfig | None = None

    # Custom provider support
    custom_providers: dict[str, "ProviderFactory"] = Field(default_factory=dict)
    custom_configs: dict[str, ProviderConfig] = Field(default_factory=dict)

    # Default can be any string (built-in or custom)
    default_provider: str = "openai"

    model_config = ConfigDict(arbitrary_types_allowed=True)
