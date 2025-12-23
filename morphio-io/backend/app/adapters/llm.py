"""
LLM adapter - provides configured LLM router and utilities.

This adapter wraps morphio-core's LLMRouter and provides:
- Configuration from application settings
- Exception translation to ApplicationException
- Model alias resolution (e.g., "gpt-5.2-high" -> base model + reasoning_effort)
- Provider-specific parameter handling (thinking_level, reasoning_effort)
"""

import logging
from typing import Any, Literal

from morphio_core.exceptions import LLMProviderError
from morphio_core.llm import LLMRouter
from morphio_core.llm.types import GenerationResult, LLMConfig, Message, ProviderConfig, TokenUsage

from ..config import settings
from ..utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)

ProviderName = Literal["openai", "anthropic", "gemini"]


class GenerationWithUsage(TokenUsage):
    """Generation result with token usage for tracking/billing.

    Inherits token tracking fields from TokenUsage and adds content.
    Use this when you need to track token consumption for monetization.
    """

    content: str


# Model token limits for output
MODEL_TOKEN_LIMITS = {
    # OpenAI models (accept reasoning_effort: low/medium/high)
    "gpt-5.2": 128000,
    "gpt-5.2-low": 128000,
    "gpt-5.2-medium": 128000,
    "gpt-5.2-high": 128000,
    "gpt-5.2-codex": 128000,
    "gpt-5.2-codex-low": 128000,
    "gpt-5.2-codex-medium": 128000,
    "gpt-5.2-codex-high": 128000,
    # Anthropic models (no thinking/reasoning support)
    "claude-4.5-opus": 16384,
    "claude-4.5-sonnet": 16384,
    "claude-4.5-haiku": 16384,
    # Gemini 3 Flash variants (accept thinking_level)
    "gemini-3-flash-preview": 65536,
    "gemini-3-flash-preview-medium": 65536,
    "gemini-3-flash-preview-low": 65536,
    "gemini-3-flash-preview-minimal": 65536,
    # Gemini 3 Pro variants (accept thinking_level)
    "gemini-3-pro-preview": 65536,
    "gemini-3-pro-preview-low": 65536,
}

# Valid models for content generation (set for O(1) membership testing)
VALID_GENERATION_MODELS = set(MODEL_TOKEN_LIMITS.keys())

# Display labels for UI
MODEL_DISPLAY_INFO = [
    # Gemini models
    {"id": "gemini-3-flash-preview", "label": "Gemini 3 Flash (High)"},
    {"id": "gemini-3-flash-preview-medium", "label": "Gemini 3 Flash (Medium)"},
    {"id": "gemini-3-flash-preview-low", "label": "Gemini 3 Flash (Low)"},
    {"id": "gemini-3-flash-preview-minimal", "label": "Gemini 3 Flash (Minimal)"},
    {"id": "gemini-3-pro-preview", "label": "Gemini 3 Pro (High)"},
    {"id": "gemini-3-pro-preview-low", "label": "Gemini 3 Pro (Low)"},
    # OpenAI models
    {"id": "gpt-5.2", "label": "GPT-5.2"},
    {"id": "gpt-5.2-high", "label": "GPT-5.2 (High Reasoning)"},
    {"id": "gpt-5.2-medium", "label": "GPT-5.2 (Medium Reasoning)"},
    {"id": "gpt-5.2-low", "label": "GPT-5.2 (Low Reasoning)"},
    {"id": "gpt-5.2-codex", "label": "GPT-5.2 Codex"},
    {"id": "gpt-5.2-codex-high", "label": "GPT-5.2 Codex (High Reasoning)"},
    {"id": "gpt-5.2-codex-medium", "label": "GPT-5.2 Codex (Medium Reasoning)"},
    {"id": "gpt-5.2-codex-low", "label": "GPT-5.2 Codex (Low Reasoning)"},
    # Anthropic models
    {"id": "claude-4.5-opus", "label": "Claude 4.5 Opus"},
    {"id": "claude-4.5-sonnet", "label": "Claude 4.5 Sonnet"},
    {"id": "claude-4.5-haiku", "label": "Claude 4.5 Haiku"},
]


def resolve_model_alias(chosen_model: str) -> tuple[str, ProviderName, dict[str, Any]]:
    """
    Resolve a model alias to base model, provider, and provider-specific kwargs.

    Model aliases encode provider-specific features:
    - "gpt-5.2-high" -> base="gpt-5.2", provider="openai", kwargs={"reasoning_effort": "high"}
    - "gpt-5.2-codex-medium" -> base="gpt-5.2-codex", kwargs={"reasoning_effort": "medium"}
    - "gemini-3-flash-preview-medium" -> base="gemini-3-flash-preview", kwargs={"thinking_level": "medium"}
    - "claude-4.5-sonnet" -> base="claude-4.5-sonnet", provider="anthropic", kwargs={}

    Args:
        chosen_model: Model ID (possibly with embedded parameters)

    Returns:
        Tuple of (base_model, provider, provider_kwargs)
    """
    provider_kwargs: dict[str, Any] = {}

    # OpenAI models with optional reasoning effort suffix
    if chosen_model.startswith("gpt-"):
        provider: ProviderName = "openai"
        base_model = chosen_model
        parts = chosen_model.split("-")
        # Check if the last part is a reasoning effort level
        if len(parts) > 1 and parts[-1] in {"low", "medium", "high"}:
            provider_kwargs["reasoning_effort"] = parts[-1]
            base_model = "-".join(parts[:-1])
        return base_model, provider, provider_kwargs

    # Gemini models with thinking level
    if chosen_model.startswith("gemini"):
        provider = "gemini"
        # Default to high, then check for level suffixes
        base_model = chosen_model
        provider_kwargs["thinking_level"] = "high"
        for level in ("minimal", "medium", "low"):
            suffix = f"-{level}"
            if chosen_model.endswith(suffix):
                base_model = chosen_model.removesuffix(suffix)
                provider_kwargs["thinking_level"] = level
                break
        return base_model, provider, provider_kwargs

    # Claude models
    if chosen_model.startswith("claude"):
        return chosen_model, "anthropic", provider_kwargs

    # Default to OpenAI
    return chosen_model, "openai", provider_kwargs


def get_model_token_limit(model: str) -> int:
    """Get the output token limit for a model."""
    return MODEL_TOKEN_LIMITS.get(model, 8192)


def get_llm_router() -> LLMRouter:
    """
    Create an LLMRouter configured from application settings.

    Uses API keys from settings to configure available providers.
    Default provider is determined by CONTENT_MODEL setting.

    Returns:
        Configured LLMRouter instance

    Raises:
        ApplicationException: If no API keys are configured
    """
    # Determine default provider from default model
    default_model = settings.CONTENT_MODEL
    if default_model.startswith("claude"):
        default_provider: ProviderName = "anthropic"
    elif default_model.startswith("gemini"):
        default_provider = "gemini"
    else:
        default_provider = "openai"

    # Build config from settings
    openai_config = None
    if settings.OPENAI_API_KEY.get_secret_value():
        openai_config = ProviderConfig(
            api_key=settings.OPENAI_API_KEY,
            default_model="gpt-4o",
            default_temperature=settings.CONTENT_TEMPERATURE,
        )

    anthropic_config = None
    if settings.ANTHROPIC_API_KEY.get_secret_value():
        anthropic_config = ProviderConfig(
            api_key=settings.ANTHROPIC_API_KEY,
            default_model="claude-sonnet-4-20250514",
            default_temperature=settings.CONTENT_TEMPERATURE,
        )

    gemini_config = None
    if settings.GEMINI_API_KEY.get_secret_value():
        gemini_config = ProviderConfig(
            api_key=settings.GEMINI_API_KEY,
            default_model="gemini-2.0-flash",
            default_temperature=settings.CONTENT_TEMPERATURE,
        )

    if not any([openai_config, anthropic_config, gemini_config]):
        raise ApplicationException(
            message="No LLM API keys configured",
            status_code=500,
        )

    config = LLMConfig(
        openai=openai_config,
        anthropic=anthropic_config,
        gemini=gemini_config,
        default_provider=default_provider,
    )

    return LLMRouter(config)


async def _generate_core(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> tuple[GenerationResult, str]:
    """
    Core generation logic shared by all completion functions.

    Handles model resolution, alias expansion, token limits, and router invocation.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model to use (supports aliases like "gpt-5.2-high")
        max_tokens: Maximum tokens in response (uses model default if None)
        temperature: Temperature override

    Returns:
        Tuple of (GenerationResult, chosen_model)

    Raises:
        ApplicationException: If generation fails
    """
    try:
        router = get_llm_router()

        # Validate model after applying default
        chosen_model = model or settings.CONTENT_MODEL
        if chosen_model not in VALID_GENERATION_MODELS:
            raise ApplicationException(
                message=f"Invalid model '{chosen_model}'. Valid models: {', '.join(sorted(VALID_GENERATION_MODELS))}",
                status_code=400,
            )

        # Resolve alias to base model and provider kwargs
        base_model, provider, provider_kwargs = resolve_model_alias(chosen_model)

        # Get token limit for model
        token_limit = get_model_token_limit(chosen_model)
        effective_max_tokens = (
            min(max_tokens, token_limit) if max_tokens is not None else token_limit
        )

        # Convert dict messages to Message objects
        typed_messages = convert_to_messages(messages)

        result = await router.generate(
            typed_messages,
            provider=provider,
            model=base_model,
            max_tokens=effective_max_tokens,
            temperature=temperature or settings.CONTENT_TEMPERATURE,
            **provider_kwargs,
        )

        return result, chosen_model

    except LLMProviderError as e:
        logger.error(f"LLM provider error: {e}")
        raise ApplicationException(
            message=f"LLM generation failed: {str(e)}",
            status_code=500,
        ) from e


async def generate_completion(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> tuple[str, str]:
    """
    Generate a completion with full provider-specific feature support.

    Resolves model aliases to base models and provider kwargs, then uses
    morphio-core's LLMRouter with the appropriate parameters.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model to use (supports aliases like "gpt-5.2-high", "gemini-3-flash-preview-medium")
        max_tokens: Maximum tokens in response (uses model default if None)
        temperature: Temperature override

    Returns:
        Tuple of (content, model_used)

    Raises:
        ApplicationException: If generation fails
    """
    result, chosen_model = await _generate_core(messages, model, max_tokens, temperature)
    return result.content, chosen_model


async def simple_completion(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> tuple[str, str]:
    """
    Simple completion (alias for generate_completion for backward compatibility).

    See generate_completion for full documentation.
    """
    return await generate_completion(
        messages=messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
    )


async def generate_completion_with_usage(
    messages: list[dict],
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> GenerationWithUsage:
    """
    Generate a completion and return token usage for tracking/billing.

    This function is preferred when you need to:
    - Track token consumption for monetization
    - Log usage for analytics
    - Implement credit-based access control

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Model to use (supports aliases like "gpt-5.2-high")
        max_tokens: Maximum tokens in response (uses model default if None)
        temperature: Temperature override

    Returns:
        GenerationWithUsage with content and token counts

    Raises:
        ApplicationException: If generation fails
    """
    result, chosen_model = await _generate_core(messages, model, max_tokens, temperature)
    usage = result.get_token_usage()

    # Construct directly, overriding model with user-facing alias
    return GenerationWithUsage(
        content=result.content,
        model=chosen_model,
        **usage.model_dump(exclude={"model"}),
    )


def convert_to_messages(messages: list[dict]) -> list[Message]:
    """Convert dict messages to typed Message objects."""
    return [
        Message(role=msg.get("role", "user"), content=msg.get("content", "")) for msg in messages
    ]


__all__ = [
    # Core functions
    "get_llm_router",
    "generate_completion",
    "generate_completion_with_usage",
    "simple_completion",
    "convert_to_messages",
    # Response types
    "GenerationWithUsage",
    # Model resolution
    "resolve_model_alias",
    "get_model_token_limit",
    # Model metadata
    "MODEL_TOKEN_LIMITS",
    "VALID_GENERATION_MODELS",
    "MODEL_DISPLAY_INFO",
    # Re-exports from morphio-core
    "LLMRouter",
    "Message",
    "GenerationResult",
    "TokenUsage",
]
