"""LLM router for multi-provider support."""

from collections.abc import AsyncIterator
from typing import Any

from pydantic import SecretStr

from ..exceptions import LLMProviderError
from .providers.anthropic import AnthropicProvider
from .providers.base import LLMProvider
from .providers.gemini import GeminiProvider
from .providers.openai import OpenAIProvider
from .types import GenerationResult, LLMConfig, Message, ProviderConfig, StreamEvent

# Built-in provider names (custom providers can use any string)
BUILTIN_PROVIDERS = {"openai", "anthropic", "gemini"}


class LLMRouter:
    """Router for multiple LLM providers.

    Manages provider instances and routes requests to the appropriate provider.
    Supports explicit provider selection or automatic routing based on config.

    Example:
        # Configure with multiple providers
        config = LLMConfig(
            openai=ProviderConfig(api_key=SecretStr("sk-..."), default_model="gpt-4o"),
            anthropic=ProviderConfig(api_key=SecretStr("sk-ant-..."), default_model="claude-sonnet-4-20250514"),
            default_provider="openai",
        )
        router = LLMRouter(config)

        # Generate with default provider
        result = await router.generate([Message(role="user", content="Hello")])

        # Generate with specific provider
        result = await router.generate(
            [Message(role="user", content="Hello")],
            provider="anthropic",
        )

        # Stream responses
        async for event in router.stream([Message(role="user", content="Hello")]):
            if event.type == "delta":
                print(event.text, end="")
    """

    def __init__(self, config: LLMConfig) -> None:
        self._config = config
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, name: str) -> LLMProvider:
        """Get or create a provider instance.

        Supports both built-in providers (openai, anthropic, gemini) and
        custom providers registered via LLMConfig.custom_providers.
        """
        if name in self._providers:
            return self._providers[name]

        # Check for custom provider first
        if name in self._config.custom_providers:
            factory = self._config.custom_providers[name]
            custom_config = self._config.custom_configs.get(name)
            if custom_config is None:
                raise LLMProviderError(
                    f"Custom provider '{name}' registered but no config in custom_configs"
                )
            provider = factory(custom_config)
            self._providers[name] = provider
            return provider

        # Built-in providers
        provider_config: ProviderConfig | None = getattr(self._config, name, None)
        if provider_config is None:
            raise LLMProviderError(f"Provider '{name}' is not configured")

        provider: LLMProvider
        if name == "openai":
            provider = OpenAIProvider(
                api_key=provider_config.api_key,
                default_model=provider_config.default_model,
                default_max_tokens=provider_config.default_max_tokens,
                default_temperature=provider_config.default_temperature,
                timeout=provider_config.timeout,
            )
        elif name == "anthropic":
            provider = AnthropicProvider(
                api_key=provider_config.api_key,
                default_model=provider_config.default_model,
                default_max_tokens=provider_config.default_max_tokens,
                default_temperature=provider_config.default_temperature,
                timeout=provider_config.timeout,
            )
        elif name == "gemini":
            provider = GeminiProvider(
                api_key=provider_config.api_key,
                default_model=provider_config.default_model,
                default_max_tokens=provider_config.default_max_tokens,
                default_temperature=provider_config.default_temperature,
                timeout=provider_config.timeout,
            )
        else:
            raise LLMProviderError(f"Unknown provider: {name}")

        self._providers[name] = provider
        return provider

    def _resolve_provider(self, provider: str | None) -> LLMProvider:
        """Resolve which provider to use."""
        name = provider or self._config.default_provider
        return self._get_provider(name)

    @property
    def available_providers(self) -> list[str]:
        """List configured provider names (built-in and custom)."""
        providers = [
            provider for provider in BUILTIN_PROVIDERS if getattr(self._config, provider, None)
        ]
        providers.extend(self._config.custom_providers.keys())
        return providers

    async def generate(
        self,
        messages: list[Message],
        *,
        provider: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **provider_kwargs: Any,
    ) -> GenerationResult:
        """Generate a completion from messages.

        Args:
            messages: Conversation messages
            provider: Provider to use (uses default if None)
            model: Model override
            max_tokens: Max tokens override
            temperature: Temperature override
            **provider_kwargs: Provider-specific arguments passed through to provider.
                Examples:
                - thinking_level: For Gemini models ("high", "medium", "low", "minimal")
                - reasoning_effort: For OpenAI o1/o3 models ("low", "medium", "high")

        Returns:
            GenerationResult with content and usage info
        """
        llm = self._resolve_provider(provider)
        return await llm.generate(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **provider_kwargs,
        )

    async def stream(
        self,
        messages: list[Message],
        *,
        provider: str | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        temperature: float | None = None,
        **provider_kwargs: Any,
    ) -> AsyncIterator[StreamEvent]:
        """Stream a completion from messages.

        Args:
            messages: Conversation messages
            provider: Provider to use (uses default if None)
            model: Model override
            max_tokens: Max tokens override
            temperature: Temperature override
            **provider_kwargs: Provider-specific arguments passed through to provider.
                Examples:
                - thinking_level: For Gemini models ("high", "medium", "low", "minimal")
                - reasoning_effort: For OpenAI o1/o3 models ("low", "medium", "high")

        Yields:
            StreamDelta for content chunks, StreamDone at end
        """
        llm = self._resolve_provider(provider)
        async for event in llm.stream(
            messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature,
            **provider_kwargs,
        ):
            yield event


def create_router(
    *,
    openai_api_key: str | SecretStr | None = None,
    openai_model: str = "gpt-4o",
    anthropic_api_key: str | SecretStr | None = None,
    anthropic_model: str = "claude-sonnet-4-20250514",
    gemini_api_key: str | SecretStr | None = None,
    gemini_model: str = "gemini-2.0-flash",
    default_provider: str = "openai",
) -> LLMRouter:
    """Create an LLM router with simple configuration.

    Convenience function for creating a router without building LLMConfig manually.

    Args:
        openai_api_key: OpenAI API key (optional)
        openai_model: Default OpenAI model
        anthropic_api_key: Anthropic API key (optional)
        anthropic_model: Default Anthropic model
        gemini_api_key: Gemini API key (optional)
        gemini_model: Default Gemini model
        default_provider: Default provider to use

    Returns:
        Configured LLMRouter

    Example:
        router = create_router(
            openai_api_key="sk-...",
            anthropic_api_key="sk-ant-...",
            default_provider="anthropic",
        )
    """
    openai_config = None
    if openai_api_key:
        key = openai_api_key if isinstance(openai_api_key, SecretStr) else SecretStr(openai_api_key)
        openai_config = ProviderConfig(api_key=key, default_model=openai_model)

    anthropic_config = None
    if anthropic_api_key:
        key = (
            anthropic_api_key
            if isinstance(anthropic_api_key, SecretStr)
            else SecretStr(anthropic_api_key)
        )
        anthropic_config = ProviderConfig(api_key=key, default_model=anthropic_model)

    gemini_config = None
    if gemini_api_key:
        key = gemini_api_key if isinstance(gemini_api_key, SecretStr) else SecretStr(gemini_api_key)
        gemini_config = ProviderConfig(api_key=key, default_model=gemini_model)

    config = LLMConfig(
        openai=openai_config,
        anthropic=anthropic_config,
        gemini=gemini_config,
        default_provider=default_provider,
    )

    return LLMRouter(config)
