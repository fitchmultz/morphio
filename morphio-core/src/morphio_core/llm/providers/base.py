"""Purpose: Define the shared protocol for morphio-core LLM providers.
Responsibilities: Specify generate/stream contracts and accepted provider kwargs.
Scope: Protocol typing for router/provider interoperability.
Usage: Implemented by concrete provider classes and consumed by router abstractions.
Invariants/Assumptions: Providers must support both full-response and streaming workflows.
"""

from collections.abc import AsyncIterator
from typing import Any, Protocol, runtime_checkable

from ..types import GenerationResult, Message, StreamEvent


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for LLM provider implementations.

    Each provider must implement both synchronous and streaming generation.
    Configuration (API keys, model names, etc.) is passed at construction time.

    Provider-specific parameters can be passed via **kwargs:
    - thinking_level: For Gemini models ("high", "medium", "low", "minimal")
    - reasoning_effort: For OpenAI o1/o3 models ("low", "medium", "high")

    Providers should accept and gracefully ignore unknown kwargs for compatibility.
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
        **kwargs: Any,
    ) -> GenerationResult:
        """Generate a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            **kwargs: Provider-specific arguments (e.g., thinking_level, reasoning_effort)

        Returns:
            GenerationResult with content and usage info
        """
        ...

    def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            **kwargs: Provider-specific arguments (e.g., thinking_level, reasoning_effort)

        Yields:
            StreamDelta for content chunks, StreamDone at end
        """
        ...
