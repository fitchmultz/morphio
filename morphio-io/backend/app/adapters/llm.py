"""
LLM adapter - provides configured LLM router and utilities.

This adapter wraps morphio-core's LLMRouter and provides:
- Configuration from application settings
- Exception translation to ApplicationException
- Simple completion helpers

Note: Advanced features like Gemini thinking levels and OpenAI reasoning
effort are handled directly in generation/core.py since morphio-core
doesn't support these provider-specific features.
"""

import logging
from typing import List, Literal, Tuple

from morphio_core.exceptions import LLMProviderError
from morphio_core.llm import LLMRouter
from morphio_core.llm.types import GenerationResult, LLMConfig, Message, ProviderConfig

from ..config import settings
from ..utils.error_handlers import ApplicationException

logger = logging.getLogger(__name__)

ProviderName = Literal["openai", "anthropic", "gemini"]


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


async def simple_completion(
    messages: List[dict],
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float | None = None,
) -> Tuple[str, str]:
    """
    Simple completion without provider-specific features.

    For basic completions that don't need thinking levels or reasoning effort.
    Uses morphio-core's LLMRouter for clean provider abstraction.

    Args:
        messages: List of message dicts with 'role' and 'content' keys
        model: Optional model override (uses default from settings if None)
        max_tokens: Maximum tokens in response
        temperature: Optional temperature override

    Returns:
        Tuple of (content, model_used)

    Raises:
        ApplicationException: If generation fails
    """
    try:
        router = get_llm_router()

        # Convert dict messages to Message objects
        typed_messages = [
            Message(role=msg.get("role", "user"), content=msg.get("content", ""))
            for msg in messages
        ]

        # Determine provider from model if specified
        provider: ProviderName | None = None
        if model:
            if model.startswith("claude"):
                provider = "anthropic"
            elif model.startswith("gemini"):
                provider = "gemini"
            elif model.startswith("gpt"):
                provider = "openai"

        result = await router.generate(
            typed_messages,
            provider=provider,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature or settings.CONTENT_TEMPERATURE,
        )

        return result.content, result.model

    except LLMProviderError as e:
        logger.error(f"LLM provider error: {e}")
        raise ApplicationException(
            message=f"LLM generation failed: {str(e)}",
            status_code=500,
        ) from e


def convert_to_messages(messages: List[dict]) -> List[Message]:
    """Convert dict messages to typed Message objects."""
    return [
        Message(role=msg.get("role", "user"), content=msg.get("content", ""))
        for msg in messages
    ]


__all__ = [
    "get_llm_router",
    "simple_completion",
    "convert_to_messages",
    "LLMRouter",
    "Message",
    "GenerationResult",
]
