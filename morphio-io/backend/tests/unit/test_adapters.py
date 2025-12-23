"""Tests for morphio-io adapters layer.

These tests verify that adapters correctly wrap morphio-core functionality
and handle model alias resolution, provider detection, and error translation.
"""

from app.adapters.llm import (
    MODEL_DISPLAY_INFO,
    MODEL_TOKEN_LIMITS,
    VALID_GENERATION_MODELS,
    convert_to_messages,
    get_model_token_limit,
    resolve_model_alias,
)


class TestModelAliasResolution:
    """Tests for model alias resolution."""

    def test_resolve_openai_base_model(self):
        """Test resolving base OpenAI model."""
        base, provider, kwargs = resolve_model_alias("gpt-5.2")
        assert base == "gpt-5.2"
        assert provider == "openai"
        assert kwargs == {}

    def test_resolve_openai_low_reasoning(self):
        """Test resolving OpenAI model with low reasoning."""
        base, provider, kwargs = resolve_model_alias("gpt-5.2-low")
        assert base == "gpt-5.2"
        assert provider == "openai"
        assert kwargs == {"reasoning_effort": "low"}

    def test_resolve_openai_medium_reasoning(self):
        """Test resolving OpenAI model with medium reasoning."""
        base, provider, kwargs = resolve_model_alias("gpt-5.2-medium")
        assert base == "gpt-5.2"
        assert provider == "openai"
        assert kwargs == {"reasoning_effort": "medium"}

    def test_resolve_openai_high_reasoning(self):
        """Test resolving OpenAI model with high reasoning."""
        base, provider, kwargs = resolve_model_alias("gpt-5.2-high")
        assert base == "gpt-5.2"
        assert provider == "openai"
        assert kwargs == {"reasoning_effort": "high"}

    def test_resolve_gemini_base_model(self):
        """Test resolving base Gemini model (defaults to high)."""
        base, provider, kwargs = resolve_model_alias("gemini-3-flash-preview")
        assert base == "gemini-3-flash-preview"
        assert provider == "gemini"
        assert kwargs == {"thinking_level": "high"}

    def test_resolve_gemini_medium_thinking(self):
        """Test resolving Gemini model with medium thinking."""
        base, provider, kwargs = resolve_model_alias("gemini-3-flash-preview-medium")
        assert base == "gemini-3-flash-preview"
        assert provider == "gemini"
        assert kwargs == {"thinking_level": "medium"}

    def test_resolve_gemini_low_thinking(self):
        """Test resolving Gemini model with low thinking."""
        base, provider, kwargs = resolve_model_alias("gemini-3-flash-preview-low")
        assert base == "gemini-3-flash-preview"
        assert provider == "gemini"
        assert kwargs == {"thinking_level": "low"}

    def test_resolve_gemini_minimal_thinking(self):
        """Test resolving Gemini model with minimal thinking."""
        base, provider, kwargs = resolve_model_alias("gemini-3-flash-preview-minimal")
        assert base == "gemini-3-flash-preview"
        assert provider == "gemini"
        assert kwargs == {"thinking_level": "minimal"}

    def test_resolve_gemini_pro_model(self):
        """Test resolving Gemini Pro model."""
        base, provider, kwargs = resolve_model_alias("gemini-3-pro-preview")
        assert base == "gemini-3-pro-preview"
        assert provider == "gemini"
        assert kwargs == {"thinking_level": "high"}

    def test_resolve_gemini_pro_low(self):
        """Test resolving Gemini Pro with low thinking."""
        base, provider, kwargs = resolve_model_alias("gemini-3-pro-preview-low")
        assert base == "gemini-3-pro-preview"
        assert provider == "gemini"
        assert kwargs == {"thinking_level": "low"}

    def test_resolve_claude_model(self):
        """Test resolving Claude model."""
        base, provider, kwargs = resolve_model_alias("claude-4.5-sonnet")
        assert base == "claude-4.5-sonnet"
        assert provider == "anthropic"
        assert kwargs == {}

    def test_resolve_unknown_defaults_to_openai(self):
        """Test that unknown models default to OpenAI provider."""
        base, provider, kwargs = resolve_model_alias("unknown-model")
        assert base == "unknown-model"
        assert provider == "openai"
        assert kwargs == {}


class TestModelTokenLimits:
    """Tests for model token limits."""

    def test_get_openai_token_limit(self):
        """Test getting OpenAI model token limit."""
        assert get_model_token_limit("gpt-5.2") == 128000

    def test_get_gemini_token_limit(self):
        """Test getting Gemini model token limit."""
        assert get_model_token_limit("gemini-3-flash-preview") == 65536

    def test_get_claude_token_limit(self):
        """Test getting Claude model token limit."""
        assert get_model_token_limit("claude-4.5-sonnet") == 16384

    def test_unknown_model_returns_default(self):
        """Test that unknown models return default limit."""
        assert get_model_token_limit("unknown-model") == 8192


class TestModelMetadata:
    """Tests for model metadata exports."""

    def test_valid_generation_models_not_empty(self):
        """Test that valid models list is not empty."""
        assert len(VALID_GENERATION_MODELS) > 0

    def test_valid_generation_models_matches_token_limits(self):
        """Test that valid models match token limits keys."""
        assert set(VALID_GENERATION_MODELS) == set(MODEL_TOKEN_LIMITS.keys())

    def test_model_display_info_has_required_keys(self):
        """Test that display info entries have required keys."""
        for info in MODEL_DISPLAY_INFO:
            assert "id" in info
            assert "label" in info

    def test_model_display_info_ids_are_valid(self):
        """Test that display info IDs are valid models."""
        for info in MODEL_DISPLAY_INFO:
            assert info["id"] in VALID_GENERATION_MODELS


class TestConvertToMessages:
    """Tests for message conversion."""

    def test_convert_single_message(self):
        """Test converting a single message."""
        messages = [{"role": "user", "content": "Hello"}]
        result = convert_to_messages(messages)
        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].content == "Hello"

    def test_convert_multiple_messages(self):
        """Test converting multiple messages."""
        messages = [
            {"role": "system", "content": "You are helpful"},
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Hello!"},
        ]
        result = convert_to_messages(messages)
        assert len(result) == 3
        assert result[0].role == "system"
        assert result[1].role == "user"
        assert result[2].role == "assistant"

    def test_convert_with_missing_role(self):
        """Test that missing role defaults to user."""
        messages = [{"content": "Hello"}]
        result = convert_to_messages(messages)
        assert result[0].role == "user"

    def test_convert_with_missing_content(self):
        """Test that missing content defaults to empty string."""
        messages = [{"role": "user"}]
        result = convert_to_messages(messages)
        assert result[0].content == ""

    def test_convert_empty_list(self):
        """Test converting empty list."""
        result = convert_to_messages([])
        assert result == []
