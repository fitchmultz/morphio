"""Base protocol for LLM providers."""

from collections.abc import AsyncIterator
from typing import Protocol, runtime_checkable

from ..types import GenerationResult, Message, StreamEvent


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM provider implementations.

    Each provider must implement both synchronous and streaming generation.
    Configuration (API keys, model names, etc.) is passed at construction time.
    """

    @property
    def provider_name(self) -> str:
        """Return the provider name (e.g., 'openai', 'anthropic', 'gemini')."""
        ...

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> GenerationResult:
        """Generate a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override

        Returns:
            GenerationResult with content and usage info
        """
        ...

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override

        Yields:
            StreamDelta for content chunks, StreamDone at end
        """
        ...
        # This is a protocol method signature - yield is for type hint only
        yield  # type: ignore[misc]
