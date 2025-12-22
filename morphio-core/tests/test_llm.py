"""Tests for LLM module."""

import pytest
from pydantic import SecretStr

from morphio_core.exceptions import LLMProviderError
from morphio_core.llm import (
    GenerationResult,
    LLMConfig,
    LLMRouter,
    Message,
    ProviderConfig,
    StreamDelta,
    StreamDone,
    Usage,
    create_router,
    extract_json_from_response,
    sanitize_markdown,
    strip_code_fences,
    truncate_for_context,
)


class TestMessage:
    """Tests for Message model."""

    def test_message_creation(self):
        """Test creating a message."""
        msg = Message(role="user", content="Hello")
        assert msg.role == "user"
        assert msg.content == "Hello"

    def test_message_roles(self):
        """Test all valid roles."""
        for role in ["system", "user", "assistant"]:
            msg = Message(role=role, content="test")  # type: ignore[arg-type]
            assert msg.role == role

    def test_message_immutable(self):
        """Test that Message is immutable."""
        from pydantic import ValidationError

        msg = Message(role="user", content="Hello")
        with pytest.raises((ValidationError, TypeError)):
            msg.content = "World"  # type: ignore[misc]


class TestUsage:
    """Tests for Usage model."""

    def test_usage_creation(self):
        """Test creating usage info."""
        usage = Usage(prompt_tokens=100, completion_tokens=50)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50

    def test_usage_defaults(self):
        """Test default values."""
        usage = Usage()
        assert usage.prompt_tokens == 0
        assert usage.completion_tokens == 0


class TestGenerationResult:
    """Tests for GenerationResult model."""

    def test_result_creation(self):
        """Test creating a generation result."""
        result = GenerationResult(
            content="Hello world",
            model="gpt-4o",
            provider="openai",
        )
        assert result.content == "Hello world"
        assert result.model == "gpt-4o"
        assert result.provider == "openai"
        assert result.usage is None
        assert result.raw is None

    def test_result_with_usage(self):
        """Test result with usage info."""
        usage = Usage(prompt_tokens=100, completion_tokens=50)
        result = GenerationResult(
            content="test",
            model="gpt-4o",
            provider="openai",
            usage=usage,
        )
        assert result.usage is not None
        assert result.usage.prompt_tokens == 100


class TestStreamEvents:
    """Tests for streaming event types."""

    def test_stream_delta(self):
        """Test StreamDelta creation."""
        delta = StreamDelta(text="Hello")
        assert delta.text == "Hello"
        assert delta.type == "delta"

    def test_stream_done(self):
        """Test StreamDone creation."""
        done = StreamDone()
        assert done.type == "done"
        assert done.usage is None

    def test_stream_done_with_usage(self):
        """Test StreamDone with usage."""
        usage = Usage(prompt_tokens=100, completion_tokens=50)
        done = StreamDone(usage=usage)
        assert done.usage is not None
        assert done.usage.prompt_tokens == 100


class TestProviderConfig:
    """Tests for ProviderConfig model."""

    def test_provider_config_creation(self):
        """Test creating provider config."""
        config = ProviderConfig(
            api_key=SecretStr("sk-test"),
            default_model="gpt-4o",
        )
        assert config.api_key.get_secret_value() == "sk-test"
        assert config.default_model == "gpt-4o"
        assert config.default_max_tokens == 4096
        assert config.default_temperature == 1.0
        assert config.timeout == 30.0
        assert config.max_retries == 3

    def test_provider_config_custom_values(self):
        """Test custom configuration values."""
        config = ProviderConfig(
            api_key=SecretStr("sk-test"),
            default_model="gpt-4o",
            default_max_tokens=8192,
            default_temperature=0.7,
            timeout=60.0,
            max_retries=5,
        )
        assert config.default_max_tokens == 8192
        assert config.default_temperature == 0.7
        assert config.timeout == 60.0
        assert config.max_retries == 5


class TestLLMConfig:
    """Tests for LLMConfig model."""

    def test_empty_config(self):
        """Test config with no providers."""
        config = LLMConfig()
        assert config.openai is None
        assert config.anthropic is None
        assert config.gemini is None
        assert config.default_provider == "openai"

    def test_single_provider_config(self):
        """Test config with single provider."""
        openai_config = ProviderConfig(
            api_key=SecretStr("sk-test"),
            default_model="gpt-4o",
        )
        config = LLMConfig(openai=openai_config)
        assert config.openai is not None
        assert config.anthropic is None

    def test_multi_provider_config(self):
        """Test config with multiple providers."""
        config = LLMConfig(
            openai=ProviderConfig(
                api_key=SecretStr("sk-openai"),
                default_model="gpt-4o",
            ),
            anthropic=ProviderConfig(
                api_key=SecretStr("sk-anthropic"),
                default_model="claude-sonnet-4-20250514",
            ),
            default_provider="anthropic",
        )
        assert config.openai is not None
        assert config.anthropic is not None
        assert config.default_provider == "anthropic"


class TestLLMRouter:
    """Tests for LLMRouter class."""

    def test_router_available_providers(self):
        """Test listing available providers."""
        config = LLMConfig(
            openai=ProviderConfig(
                api_key=SecretStr("sk-test"),
                default_model="gpt-4o",
            ),
        )
        router = LLMRouter(config)
        assert "openai" in router.available_providers
        assert "anthropic" not in router.available_providers

    def test_router_unconfigured_provider_error(self):
        """Test error when using unconfigured provider."""
        config = LLMConfig()  # No providers configured
        router = LLMRouter(config)

        with pytest.raises(LLMProviderError, match="not configured"):
            router._get_provider("openai")

    def test_create_router_simple(self):
        """Test create_router convenience function."""
        router = create_router(
            openai_api_key="sk-test",
            openai_model="gpt-4o",
        )
        assert "openai" in router.available_providers

    def test_create_router_multiple_providers(self):
        """Test create_router with multiple providers."""
        router = create_router(
            openai_api_key="sk-openai",
            anthropic_api_key="sk-anthropic",
            default_provider="anthropic",
        )
        assert "openai" in router.available_providers
        assert "anthropic" in router.available_providers


class TestSanitizeMarkdown:
    """Tests for sanitize_markdown function."""

    def test_properly_closed_code_block(self):
        """Test that properly closed code blocks are unchanged."""
        content = "```python\nprint('hello')\n```"
        result = sanitize_markdown(content)
        assert result == content

    def test_unclosed_code_block(self):
        """Test that unclosed code blocks get closed."""
        content = "```python\nprint('hello')"
        result = sanitize_markdown(content)
        assert result.endswith("```")

    def test_stray_backticks_escaped(self):
        """Test that stray backticks are escaped."""
        content = "Use `print` to output"
        # Single backticks that aren't code spans should be escaped
        result = sanitize_markdown(content)
        assert result == r"Use \`print\` to output"

    def test_complex_markdown(self):
        """Test with complex markdown content."""
        content = """# Header

```python
def foo():
    pass
```

Some text with `inline` code.
"""
        result = sanitize_markdown(content)
        # Should not break valid markdown
        assert "```python" in result
        assert "```\n" in result


class TestStripCodeFences:
    """Tests for strip_code_fences function."""

    def test_strip_json_fence(self):
        """Test stripping JSON code fence."""
        content = '```json\n{"key": "value"}\n```'
        result = strip_code_fences(content)
        assert result == '{"key": "value"}'

    def test_strip_fence_with_language(self):
        """Test stripping fence with language tag."""
        content = "```python\nprint('hello')\n```"
        result = strip_code_fences(content)
        assert result == "print('hello')"

    def test_no_fence(self):
        """Test content without fences."""
        content = '{"key": "value"}'
        result = strip_code_fences(content)
        assert result == content

    def test_preserve_inner_fences(self):
        """Test that only outer fence is stripped."""
        content = "```markdown\n# Title\n```python\ncode\n```\n```"
        result = strip_code_fences(content)
        # Inner fence should remain
        assert "```python" in result


class TestExtractJsonFromResponse:
    """Tests for extract_json_from_response function."""

    def test_extract_fenced_json(self):
        """Test extracting JSON from fenced block."""
        content = """Here's the result:
```json
{"name": "test"}
```
Let me know if you need changes."""
        result = extract_json_from_response(content)
        assert result == '{"name": "test"}'

    def test_extract_unfenced_json(self):
        """Test extracting unfenced JSON object."""
        content = 'The answer is {"value": 42} which is correct.'
        result = extract_json_from_response(content)
        assert result == '{"value": 42}'

    def test_extract_json_array(self):
        """Test extracting JSON array."""
        content = "Results: [1, 2, 3]"
        result = extract_json_from_response(content)
        assert result == "[1, 2, 3]"

    def test_no_json_returns_original(self):
        """Test that non-JSON content returns as-is."""
        content = "Just some plain text"
        result = extract_json_from_response(content)
        assert result == content


class TestTruncateForContext:
    """Tests for truncate_for_context function."""

    def test_short_content_unchanged(self):
        """Test that short content is not truncated."""
        content = "Hello world"
        result = truncate_for_context(content, 100)
        assert result == content

    def test_truncate_at_word_boundary(self):
        """Test truncation at word boundary."""
        content = "This is a long piece of content that needs truncating"
        result = truncate_for_context(content, 30)
        assert result.endswith("...[truncated]")
        assert len(result) <= 30

    def test_custom_suffix(self):
        """Test with custom truncation suffix."""
        content = "A" * 100
        result = truncate_for_context(content, 20, suffix="...")
        assert result.endswith("...")

    def test_exact_length(self):
        """Test content exactly at limit."""
        content = "A" * 50
        result = truncate_for_context(content, 50)
        assert result == content


class TestExceptions:
    """Tests for LLM-related exceptions."""

    def test_llm_provider_error(self):
        """Test LLMProviderError can be raised."""
        with pytest.raises(LLMProviderError):
            raise LLMProviderError("Provider not available")

    def test_exception_hierarchy(self):
        """Test exception hierarchy."""
        from morphio_core.exceptions import LLMError

        assert issubclass(LLMProviderError, LLMError)
