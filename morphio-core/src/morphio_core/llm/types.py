"""
LLM types and configuration models.

All config uses Pydantic with explicit fields - no global settings.
"""

from collections.abc import Callable
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr

# Type alias for provider factory functions
# A factory takes a ProviderConfig and returns an LLMProvider-compatible instance
# Uses Any for return type to avoid circular import with providers.base
ProviderFactory = Callable[["ProviderConfig"], Any]

# Advanced reasoning parameter types
# These are passed through router kwargs to providers

ThinkingLevel = Literal["minimal", "low", "medium", "high"]
"""Gemini thinking level for advanced reasoning models."""

ReasoningEffort = Literal["low", "medium", "high"]
"""OpenAI reasoning effort for o1/o3 models."""

# Valid value sets for validation
VALID_THINKING_LEVELS: frozenset[str] = frozenset({"minimal", "low", "medium", "high"})
VALID_REASONING_EFFORTS: frozenset[str] = frozenset({"low", "medium", "high"})


def validate_thinking_level(value: str | None) -> str | None:
    """Validate and normalize thinking_level value.

    Args:
        value: Thinking level to validate (case-insensitive)

    Returns:
        Normalized lowercase value or None if input is None

    Raises:
        ValueError: If value is not a valid thinking level
    """
    if value is None:
        return None
    normalized = value.lower()
    if normalized not in VALID_THINKING_LEVELS:
        valid_options = ", ".join(sorted(VALID_THINKING_LEVELS))
        raise ValueError(f"Invalid thinking_level '{value}'. Valid values: {valid_options}")
    return normalized


def validate_reasoning_effort(value: str | None) -> str | None:
    """Validate and normalize reasoning_effort value.

    Args:
        value: Reasoning effort to validate (case-insensitive)

    Returns:
        Normalized lowercase value or None if input is None

    Raises:
        ValueError: If value is not a valid reasoning effort
    """
    if value is None:
        return None
    normalized = value.lower()
    if normalized not in VALID_REASONING_EFFORTS:
        valid_options = ", ".join(sorted(VALID_REASONING_EFFORTS))
        raise ValueError(f"Invalid reasoning_effort '{value}'. Valid values: {valid_options}")
    return normalized


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

    @property
    def total_tokens(self) -> int:
        """Total tokens used (prompt + completion)."""
        return self.prompt_tokens + self.completion_tokens


class TokenUsage(BaseModel):
    """Extended token usage with cost tracking for monetization.

    This is the full usage model for tracking across the application layer.
    Includes provider/model metadata and optional cost estimation.
    """

    model_config = ConfigDict(frozen=True)

    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    provider: str | None = None
    model: str | None = None
    cost_usd: Decimal | None = None  # Optional - populated by cost estimation layer

    @classmethod
    def from_usage(
        cls,
        usage: "Usage | None",
        *,
        provider: str | None = None,
        model: str | None = None,
    ) -> "TokenUsage":
        """Create TokenUsage from a basic Usage object.

        Args:
            usage: Basic usage from provider response
            provider: Provider name (e.g., "openai", "anthropic")
            model: Model identifier

        Returns:
            TokenUsage with extended metadata
        """
        if usage is None:
            return cls(provider=provider, model=model)
        return cls(
            input_tokens=usage.prompt_tokens,
            output_tokens=usage.completion_tokens,
            total_tokens=usage.total_tokens,
            provider=provider,
            model=model,
        )


class GenerationResult(BaseModel):
    """Response from any LLM provider."""

    model_config = ConfigDict(frozen=True)

    content: str
    model: str
    provider: str
    usage: Usage | None = None
    raw: Any | None = Field(default=None, repr=False, exclude=True)  # Debug only

    def get_token_usage(self) -> TokenUsage:
        """Get extended token usage with provider/model metadata.

        Returns:
            TokenUsage with full metadata for tracking/billing
        """
        return TokenUsage.from_usage(self.usage, provider=self.provider, model=self.model)


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
        def my_provider_factory(config: ProviderConfig) -> "LLMProvider":
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
