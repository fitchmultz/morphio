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
    GenerationResult,
    LLMConfig,
    Message,
    ProviderConfig,
    ProviderFactory,
    StreamDelta,
    StreamDone,
    StreamEvent,
    Usage,
)

__all__ = [
    # Types
    "Message",
    "Usage",
    "GenerationResult",
    "StreamDelta",
    "StreamDone",
    "StreamEvent",
    "ProviderConfig",
    "ProviderFactory",
    "LLMConfig",
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
