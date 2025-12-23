"""
Adapters for morphio-core integration.

Adapters are thin wrappers that bridge morphio-core library functionality
with the morphio-io web application. They provide:

1. Exception Translation
   - morphio-core exceptions → ApplicationException (with HTTP status codes)
   - Clean separation between library and HTTP concerns

2. Configuration Bridging
   - Application settings → morphio-core explicit config objects
   - Environment-aware configuration

3. Model Alias Resolution (LLM adapter)
   - User-friendly model IDs → base models + provider kwargs
   - e.g., "gpt-5.1-high" → model="gpt-5.1", reasoning_effort="high"

Available Adapters:
- llm: LLM router with model alias resolution and provider-specific features
- video: YouTube URL parsing and video download
- url_validation: SSRF protection for external URLs
- anonymizer: Content anonymization for sensitive data

Usage Pattern:
    # Import from adapter, not morphio-core directly
    from app.adapters.llm import generate_completion
    from app.adapters.video import download_video_via_ytdlp

    # Adapters handle settings injection and exception translation
    result = await generate_completion(messages, model="gpt-5.1-high")
"""

from .llm import (
    MODEL_DISPLAY_INFO,
    MODEL_TOKEN_LIMITS,
    VALID_GENERATION_MODELS,
    generate_completion,
    get_llm_router,
    resolve_model_alias,
    simple_completion,
)
from .video import (
    download_video_via_ytdlp,
    get_yt_video_id,
    is_supported_video_url,
)
from .url_validation import validate_url
from .anonymizer import anonymize_content, deanonymize_content

__all__ = [
    # LLM
    "generate_completion",
    "simple_completion",
    "get_llm_router",
    "resolve_model_alias",
    "MODEL_TOKEN_LIMITS",
    "MODEL_DISPLAY_INFO",
    "VALID_GENERATION_MODELS",
    # Video
    "download_video_via_ytdlp",
    "get_yt_video_id",
    "is_supported_video_url",
    # URL Validation
    "validate_url",
    # Anonymizer
    "anonymize_content",
    "deanonymize_content",
]
