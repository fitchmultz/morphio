"""OpenAI provider implementation."""

import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from pydantic import SecretStr

from ...exceptions import LLMProviderError
from ..types import GenerationResult, Message, StreamDelta, StreamDone, StreamEvent, Usage

logger = logging.getLogger(__name__)

# Valid reasoning effort levels for OpenAI reasoning models (o1, o3 series)
ReasoningEffort = Literal["low", "medium", "high"]
VALID_REASONING_EFFORTS = {"low", "medium", "high"}


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

    @staticmethod
    def _apply_reasoning_effort(
        api_params: dict[str, Any], reasoning_effort: str | None
    ) -> None:
        """Validate and apply reasoning_effort to API params.

        Args:
            api_params: Dictionary to modify in place
            reasoning_effort: Optional reasoning effort level

        Raises:
            LLMProviderError: If reasoning_effort is invalid
        """
        if reasoning_effort:
            effort = reasoning_effort.lower()
            if effort not in VALID_REASONING_EFFORTS:
                raise LLMProviderError(
                    f"Invalid reasoning_effort '{reasoning_effort}'. "
                    f"Valid values: {VALID_REASONING_EFFORTS}"
                )
            api_params["reasoning_effort"] = effort

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        reasoning_effort: str | None = None,
        **kwargs: Any,  # Accept and ignore unknown kwargs
    ) -> GenerationResult:
        """Generate a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            reasoning_effort: Reasoning effort for o1/o3 models ("low", "medium", "high")
            **kwargs: Ignored (for provider compatibility)

        Returns:
            GenerationResult with content and usage info
        """
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        # Convert to OpenAI message format
        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        # Build API params
        api_params: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
        }

        self._apply_reasoning_effort(api_params, reasoning_effort)

        try:
            response = await client.chat.completions.create(**api_params)

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
        reasoning_effort: str | None = None,
        **kwargs: Any,  # Accept and ignore unknown kwargs
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            reasoning_effort: Reasoning effort for o1/o3 models ("low", "medium", "high")
            **kwargs: Ignored (for provider compatibility)

        Yields:
            StreamDelta for content chunks, StreamDone at end
        """
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        openai_messages = [{"role": m.role, "content": m.content} for m in messages]

        # Build API params
        api_params: dict[str, Any] = {
            "model": model,
            "messages": openai_messages,
            "max_completion_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        self._apply_reasoning_effort(api_params, reasoning_effort)

        try:
            stream = await client.chat.completions.create(**api_params)

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
