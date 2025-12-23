"""
LLM orchestration utilities.

Provides:
- Multi-provider LLM router (OpenAI, Anthropic, Gemini)
- Protocol-based provider abstraction
- Streaming support with typed events
- Markdown parsing utilities
"""

from .parsing import (
    extract_json_from_response,
    sanitize_markdown,
    strip_code_fences,
    truncate_for_context,
)
from .providers import (
    AnthropicProvider,
    GeminiProvider,
    LLMProvider,
    OpenAIProvider,
)
from .router import LLMRouter, create_router
from .types import (
    VALID_REASONING_EFFORTS,
    VALID_THINKING_LEVELS,
    GenerationResult,
    LLMConfig,
    Message,
    ProviderConfig,
    ProviderFactory,
    ReasoningEffort,
    StreamDelta,
    StreamDone,
    StreamEvent,
    ThinkingLevel,
    TokenUsage,
    Usage,
    validate_reasoning_effort,
    validate_thinking_level,
)

__all__ = [
    # Types
    "Message",
    "Usage",
    "TokenUsage",
    "GenerationResult",
    "StreamDelta",
    "StreamDone",
    "StreamEvent",
    "ProviderConfig",
    "ProviderFactory",
    "LLMConfig",
    # Advanced reasoning types
    "ThinkingLevel",
    "ReasoningEffort",
    "VALID_THINKING_LEVELS",
    "VALID_REASONING_EFFORTS",
    "validate_thinking_level",
    "validate_reasoning_effort",
    # Providers
    "LLMProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GeminiProvider",
    # Router
    "LLMRouter",
    "create_router",
    # Parsing utilities
    "sanitize_markdown",
    "strip_code_fences",
    "extract_json_from_response",
    "truncate_for_context",
]
