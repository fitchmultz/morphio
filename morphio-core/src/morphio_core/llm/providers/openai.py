"""OpenAI provider implementation."""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import SecretStr

from ...exceptions import LLMProviderError
from ..types import GenerationResult, Message, StreamDelta, StreamDone, StreamEvent, Usage


class OpenAIProvider:
    """OpenAI LLM provider.

    Uses the openai SDK for API calls. Supports both sync and streaming.

    Example:
        provider = OpenAIProvider(
            api_key=SecretStr("sk-..."),
            default_model="gpt-4o",
        )
        result = await provider.generate([Message(role="user", content="Hello")])
    """

    def __init__(
        self,
        *,
        api_key: SecretStr,
        default_model: str = "gpt-4o",
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
        """Lazily initialize the OpenAI client."""
        if self._client is None:
            try:
                from openai import AsyncOpenAI  # type: ignore[import-not-found]

                self._client = AsyncOpenAI(
                    api_key=self._api_key.get_secret_value(),
                    timeout=self._timeout,
                )
            except ImportError as e:
                raise LLMProviderError("openai package not installed") from e
        return self._client

    @property
    def provider_name(self) -> str:
        return "openai"

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> GenerationResult:
        """Generate a completion from messages."""
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        # Convert to OpenAI message format
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            response = await client.chat.completions.create(
                model=model,
                messages=openai_messages,
                max_completion_tokens=max_tokens,
                temperature=temperature,
            )

            content = response.choices[0].message.content or ""
            usage = None
            if response.usage:
                usage = Usage(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                )

            return GenerationResult(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                raw=response,
            )
        except Exception as e:
            raise LLMProviderError(f"OpenAI generation failed: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages."""
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        try:
            stream = await client.chat.completions.create(
                model=model,
                messages=openai_messages,
                max_completion_tokens=max_tokens,
                temperature=temperature,
                stream=True,
                stream_options={"include_usage": True},
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield StreamDelta(text=chunk.choices[0].delta.content)

                # Usage comes in the final chunk
                if chunk.usage:
                    yield StreamDone(
                        usage=Usage(
                            prompt_tokens=chunk.usage.prompt_tokens,
                            completion_tokens=chunk.usage.completion_tokens,
                        )
                    )
                    return

            # If no usage was returned, still signal completion
            yield StreamDone()

        except Exception as e:
            raise LLMProviderError(f"OpenAI streaming failed: {e}") from e
