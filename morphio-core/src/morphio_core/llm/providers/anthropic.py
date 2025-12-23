"""Anthropic provider implementation."""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import SecretStr

from ...exceptions import LLMProviderError, OptionalDependencyError
from ..types import GenerationResult, Message, StreamDelta, StreamDone, StreamEvent, Usage


class AnthropicProvider:
    """Anthropic LLM provider (Claude models).

    Uses the anthropic SDK for API calls. Supports both sync and streaming.

    Example:
        provider = AnthropicProvider(
            api_key=SecretStr("sk-ant-..."),
            default_model="claude-sonnet-4-20250514",
        )
        result = await provider.generate([Message(role="user", content="Hello")])
    """

    def __init__(
        self,
        *,
        api_key: SecretStr,
        default_model: str = "claude-sonnet-4-20250514",
        default_max_tokens: int = 4096,
        default_temperature: float = 1.0,
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._default_model = default_model
        self._default_max_tokens = default_max_tokens
        self._default_temperature = default_temperature
        self._timeout = timeout
        self._client: Any = None

    def _ensure_client(self) -> Any:
        """Lazily initialize the Anthropic client."""
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic  # type: ignore[import-not-found]

                self._client = AsyncAnthropic(
                    api_key=self._api_key.get_secret_value(),
                    timeout=self._timeout,
                )
            except ImportError as e:
                raise OptionalDependencyError(
                    package="Anthropic SDK",
                    extra="llm-anthropic",
                    pip_package="anthropic",
                ) from e
        return self._client

    @property
    def provider_name(self) -> str:
        return "anthropic"

    def _convert_messages(self, messages: list[Message]) -> tuple[list[dict[str, str]], str | None]:
        """Convert messages to Anthropic format.

        Extracts system messages and converts the rest to Anthropic's format.

        Returns:
            Tuple of (messages, system_prompt)
        """
        system_parts: list[str] = []
        anthropic_messages: list[dict[str, str]] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            else:
                anthropic_messages.append({"role": msg.role, "content": msg.content})

        system_prompt = "\n\n".join(system_parts) if system_parts else None
        return anthropic_messages, system_prompt

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,  # Accept and ignore unknown kwargs for provider compatibility
    ) -> GenerationResult:
        """Generate a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            **kwargs: Ignored (for provider compatibility)

        Returns:
            GenerationResult with content and usage info
        """
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        anthropic_messages, system_prompt = self._convert_messages(messages)

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            response = await client.messages.create(**kwargs)

            # Extract text from content blocks
            content = ""
            for block in response.content:
                if hasattr(block, "text"):
                    content += block.text

            usage = Usage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
            )

            return GenerationResult(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                raw=response,
            )
        except Exception as e:
            raise LLMProviderError(f"Anthropic generation failed: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **kwargs: Any,  # Accept and ignore unknown kwargs for provider compatibility
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            **kwargs: Ignored (for provider compatibility)

        Yields:
            StreamDelta for content chunks, StreamDone at end
        """
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        anthropic_messages, system_prompt = self._convert_messages(messages)

        try:
            kwargs: dict[str, Any] = {
                "model": model,
                "messages": anthropic_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
            if system_prompt:
                kwargs["system"] = system_prompt

            async with client.messages.stream(**kwargs) as stream:
                async for text in stream.text_stream:
                    yield StreamDelta(text=text)

                # Get final message for usage
                final_message = await stream.get_final_message()
                yield StreamDone(
                    usage=Usage(
                        prompt_tokens=final_message.usage.input_tokens,
                        completion_tokens=final_message.usage.output_tokens,
                    )
                )

        except Exception as e:
            raise LLMProviderError(f"Anthropic streaming failed: {e}") from e
