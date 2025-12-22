"""Google Gemini provider implementation."""

import logging
from collections.abc import AsyncIterator
from typing import Any, Literal

from pydantic import SecretStr

from ...exceptions import LLMProviderError
from ..types import GenerationResult, Message, StreamDelta, StreamDone, StreamEvent, Usage

logger = logging.getLogger(__name__)

# Valid thinking levels for Gemini models
ThinkingLevel = Literal["high", "medium", "low", "minimal"]
VALID_THINKING_LEVELS = {"high", "medium", "low", "minimal"}
PRO_THINKING_LEVELS = {"high", "low"}  # Pro models only support these


class GeminiProvider:
    """Google Gemini LLM provider.

    Uses the google-genai SDK for API calls. Supports both sync and streaming.

    Example:
        provider = GeminiProvider(
            api_key=SecretStr("..."),
            default_model="gemini-2.0-flash",
        )
        result = await provider.generate([Message(role="user", content="Hello")])
    """

    def __init__(
        self,
        *,
        api_key: SecretStr,
        default_model: str = "gemini-2.0-flash",
        default_max_tokens: int = 8192,
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
        """Lazily initialize the Gemini client."""
        if self._client is None:
            try:
                from google import genai  # type: ignore[import-not-found]

                self._client = genai.Client(api_key=self._api_key.get_secret_value())
            except ImportError as e:
                raise LLMProviderError("google-genai package not installed") from e
        return self._client

    @property
    def provider_name(self) -> str:
        return "gemini"

    def _convert_messages(self, messages: list[Message]) -> tuple[list[dict[str, Any]], str | None]:
        """Convert messages to Gemini format.

        Extracts system messages and converts the rest to Gemini's format.

        Returns:
            Tuple of (contents, system_instruction)
        """
        from google.genai import types  # type: ignore[import-not-found]

        system_parts: list[str] = []
        contents: list[dict[str, Any]] = []

        for msg in messages:
            if msg.role == "system":
                system_parts.append(msg.content)
            elif msg.role == "assistant":
                contents.append(
                    types.Content(role="model", parts=[types.Part.from_text(text=msg.content)])
                )
            else:
                contents.append(
                    types.Content(role="user", parts=[types.Part.from_text(text=msg.content)])
                )

        system_instruction = "\n\n".join(system_parts) if system_parts else None
        return contents, system_instruction

    def _build_config(
        self,
        *,
        temperature: float,
        max_tokens: int,
        system_instruction: str | None,
        thinking_level: str | None,
        model: str,
    ) -> Any:
        """Build Gemini config with optional thinking level.

        Args:
            temperature: Generation temperature
            max_tokens: Maximum output tokens
            system_instruction: System prompt
            thinking_level: Thinking level ("high", "medium", "low", "minimal")
            model: Model name for validation

        Returns:
            GenerateContentConfig
        """
        from google.genai import types  # type: ignore[import-not-found]

        config_params: dict[str, Any] = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
        }

        if system_instruction:
            config_params["system_instruction"] = system_instruction

        if thinking_level:
            level = thinking_level.lower()
            if level not in VALID_THINKING_LEVELS:
                logger.warning(
                    f"Invalid thinking_level '{thinking_level}', ignoring. "
                    f"Valid values: {VALID_THINKING_LEVELS}"
                )
            else:
                # Check Pro model restrictions
                if "pro" in model.lower() and level not in PRO_THINKING_LEVELS:
                    logger.warning(
                        f"Gemini Pro models only support {PRO_THINKING_LEVELS}, "
                        f"got '{level}'. Defaulting to 'high'."
                    )
                    level = "high"

                config_params["thinking_config"] = types.ThinkingConfig(
                    thinking_level=level.upper()
                )

        return types.GenerateContentConfig(**config_params)

    async def generate(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking_level: str | None = None,
        **kwargs: Any,  # Accept and ignore unknown kwargs
    ) -> GenerationResult:
        """Generate a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            thinking_level: Thinking level for Gemini models ("high", "medium", "low", "minimal")
            **kwargs: Ignored (for provider compatibility)

        Returns:
            GenerationResult with content and usage info
        """
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        contents, system_instruction = self._convert_messages(messages)

        try:
            config = self._build_config(
                temperature=temperature,
                max_tokens=max_tokens,
                system_instruction=system_instruction,
                thinking_level=thinking_level,
                model=model,
            )

            response = await client.aio.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            content = response.text or ""

            # Extract usage if available
            usage = None
            if hasattr(response, "usage_metadata") and response.usage_metadata:
                usage = Usage(
                    prompt_tokens=response.usage_metadata.prompt_token_count or 0,
                    completion_tokens=response.usage_metadata.candidates_token_count or 0,
                )

            return GenerationResult(
                content=content,
                model=model,
                provider=self.provider_name,
                usage=usage,
                raw=response,
            )
        except Exception as e:
            raise LLMProviderError(f"Gemini generation failed: {e}") from e

    async def stream(
        self,
        messages: list[Message],
        *,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        thinking_level: str | None = None,
        **kwargs: Any,  # Accept and ignore unknown kwargs
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages.

        Args:
            messages: Conversation messages
            model: Model override (uses provider default if None)
            max_tokens: Max tokens override
            temperature: Temperature override
            thinking_level: Thinking level for Gemini models ("high", "medium", "low", "minimal")
            **kwargs: Ignored (for provider compatibility)

        Yields:
            StreamDelta for content chunks, StreamDone at end
        """
        client = self._ensure_client()

        model = model or self._default_model
        max_tokens = max_tokens or self._default_max_tokens
        temperature = temperature if temperature is not None else self._default_temperature

        contents, system_instruction = self._convert_messages(messages)

        try:
            config = self._build_config(
                temperature=temperature,
                max_tokens=max_tokens,
                system_instruction=system_instruction,
                thinking_level=thinking_level,
                model=model,
            )

            stream = await client.aio.models.generate_content_stream(
                model=model,
                contents=contents,
                config=config,
            )

            total_prompt_tokens = 0
            total_completion_tokens = 0

            async for chunk in stream:
                if chunk.text:
                    yield StreamDelta(text=chunk.text)

                # Accumulate usage
                if hasattr(chunk, "usage_metadata") and chunk.usage_metadata:
                    if chunk.usage_metadata.prompt_token_count:
                        total_prompt_tokens = chunk.usage_metadata.prompt_token_count
                    if chunk.usage_metadata.candidates_token_count:
                        total_completion_tokens = chunk.usage_metadata.candidates_token_count

            yield StreamDone(
                usage=Usage(
                    prompt_tokens=total_prompt_tokens,
                    completion_tokens=total_completion_tokens,
                )
                if total_prompt_tokens or total_completion_tokens
                else None
            )

        except Exception as e:
            raise LLMProviderError(f"Gemini streaming failed: {e}") from e
