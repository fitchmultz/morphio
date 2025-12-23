# Morphio Architecture

This document explains how morphio-io and morphio-core are structured and how they interact.

## Project Relationship

```
morphio-all/                    # Monorepo root
├── morphio-core/               # Standalone Python library
│   └── src/morphio_core/
│       ├── audio/              # Chunking, transcription, alignment
│       ├── llm/                # Multi-provider router
│       ├── security/           # URL validation, anonymization
│       ├── video/              # YouTube utilities
│       └── media/              # FFmpeg utilities
│
└── morphio-io/                 # Full-stack web application
    ├── backend/
    │   └── app/
    │       ├── adapters/       # Thin wrappers around morphio-core
    │       ├── services/       # Application services using adapters
    │       ├── routes/         # FastAPI endpoints
    │       └── schemas/        # Pydantic models
    └── frontend/               # Next.js application
```

## The Adapter Pattern

morphio-io uses thin **adapters** to wrap morphio-core functionality. This pattern:

1. **Translates exceptions** - Converts library exceptions to HTTP-appropriate responses
2. **Bridges configuration** - Maps application settings to library config objects
3. **Maintains backward compatibility** - Old import paths still work via re-exports

### How Adapters Work

```
User Request → FastAPI Route → Service → Adapter → morphio-core
                                   ↑          ↓
                                   └── Exception Translation
```

**Example: URL Validation Adapter**

```python
# morphio-io/backend/app/adapters/url_validation.py

from morphio_core.exceptions import SSRFBlockedError
from morphio_core.security import URLValidator
from ..utils.error_handlers import ApplicationException

def validate_url(url: str) -> None:
    try:
        _get_validator().validate(url)
    except SSRFBlockedError as e:
        raise ApplicationException(str(e), status_code=400)
```

The adapter:
- Imports from `morphio_core.security`
- Catches `SSRFBlockedError` (library exception)
- Raises `ApplicationException` (HTTP exception with status code)

### Adapter Inventory

| Adapter | morphio-core Module | Purpose |
|---------|---------------------|---------|
| `url_validation.py` | `security.URLValidator` | SSRF protection |
| `video.py` | `video.YouTubeDownloader` | Video downloading |
| `audio.py` | `audio.chunking`, `audio.transcription` | Audio processing |
| `llm.py` | `llm.LLMRouter` | LLM orchestration with model aliases |
| `speaker_alignment.py` | `audio.speaker_alignment` | Speaker diarization |
| `media.py` | `media.FFmpegWrapper` | Media conversion |
| `anonymizer.py` | `security.Anonymizer` | PII removal |

## Provider SDK Boundary

**Critical Rule:** Only morphio-core may import provider SDKs (OpenAI, Anthropic, Google GenAI).

```
✓ Good: morphio-core imports openai SDK
✓ Good: morphio-io imports from morphio_core.llm
✗ Bad:  morphio-io imports openai directly
✗ Bad:  morphio-io imports google.genai directly
```

### Advanced Reasoning Parameters

Provider-specific parameters flow through the adapter → router → provider chain:

```
morphio-io adapter                          morphio-core router                      Provider
┌──────────────────────┐                   ┌──────────────────┐                    ┌──────────────┐
│ generate_completion( │                   │ router.generate( │                    │ provider.    │
│   model="gpt-5.1-high",  ──resolve────>  │   model="gpt-5.1", ──pass_through──> │   generate(  │
│   ...                │     alias         │   reasoning_effort="high",           │     ...      │
│ )                    │                   │   **kwargs                           │     reasoning_effort="high")
└──────────────────────┘                   └──────────────────┘                    └──────────────┘
```

**Supported Parameters:**

| Provider | Parameter | Models | Values |
|----------|-----------|--------|--------|
| OpenAI | `reasoning_effort` | o1, o3 series | `"low"`, `"medium"`, `"high"` |
| Gemini | `thinking_level` | All (Pro: limited) | `"minimal"`, `"low"`, `"medium"`, `"high"` |
| Anthropic | (none yet) | - | - |

**Model Alias Resolution (in morphio-io):**

```python
# User-facing model aliases encode parameters
"gpt-5.1-high"                → base="gpt-5.1", reasoning_effort="high"
"gemini-3-flash-preview-low"  → base="gemini-3-flash-preview", thinking_level="low"
"claude-4-sonnet"             → base="claude-4-sonnet" (no special params)
```

The LLM adapter resolves these aliases before calling morphio-core's router.

## Exception Translation

morphio-core uses library-specific exceptions without HTTP concerns:

```python
# morphio-core exceptions (no HTTP status codes)
class MorphioCoreError(Exception): ...
class AudioChunkingError(MorphioCoreError): ...
class TranscriptionError(MorphioCoreError): ...
class LLMProviderError(MorphioCoreError): ...
class SSRFBlockedError(MorphioCoreError): ...
```

Adapters translate these to HTTP-aware exceptions:

```python
# morphio-io translation pattern
try:
    result = transcriber.transcribe(file)
except TranscriptionError as e:
    raise ApplicationException(
        message=f"Transcription failed: {e}",
        status_code=500
    )
```

## Configuration Flow

```
Environment Variables → settings.py → Adapter → morphio-core Config Object
                                                        ↓
                                              Library Instance
```

**Example: LLM Router Configuration**

```python
# morphio-io/backend/app/adapters/llm.py

def get_llm_router() -> LLMRouter:
    # Read from application settings (env vars)
    openai_config = ProviderConfig(
        api_key=settings.OPENAI_API_KEY,
        default_model="gpt-4o",
    )

    # Create library config object
    config = LLMConfig(
        openai=openai_config,
        default_provider="openai",
    )

    # Return configured library instance
    return LLMRouter(config)
```

## Why This Architecture?

### Benefits

1. **Reusability** - morphio-core works in any Python project
2. **Testability** - Library has no HTTP dependencies, easy to unit test
3. **Separation of concerns** - Web concerns stay in morphio-io
4. **Clear boundaries** - Adapters are the only integration point

### Trade-offs

1. **Indirection** - One extra layer between routes and logic
2. **Maintenance** - Adapters need updating when library API changes
3. **Duplication** - Some type conversion between library and app schemas

## Adding New Functionality

### To morphio-core (library)

1. Add module under `src/morphio_core/`
2. Export in `__init__.py`
3. Add tests under `tests/`
4. Document in morphio-core README

### To morphio-io (application)

1. Create adapter in `app/adapters/`
2. Import morphio-core functionality
3. Add exception translation
4. Use adapter in services/routes

### Example: Adding a New Feature

```python
# 1. morphio-core: src/morphio_core/newfeature/__init__.py
class NewFeature:
    def __init__(self, config: NewFeatureConfig):
        self.config = config

    def process(self, data: str) -> str:
        # Pure library logic, no HTTP
        ...

# 2. morphio-io: app/adapters/newfeature.py
from morphio_core.newfeature import NewFeature, NewFeatureError
from ..config import settings

def process_data(data: str) -> str:
    try:
        feature = NewFeature(config=...)
        return feature.process(data)
    except NewFeatureError as e:
        raise ApplicationException(str(e), status_code=500)
```

## Testing Strategy

| Layer | Test Location | What to Test |
|-------|---------------|--------------|
| morphio-core | `morphio-core/tests/` | Pure logic, mock SDKs |
| Adapters | `morphio-io/backend/tests/unit/` | Exception translation |
| Services | `morphio-io/backend/tests/unit/` | Business logic |
| Routes | `morphio-io/backend/tests/functional/` | HTTP behavior |

```bash
# Run all tests
make test

# Run morphio-core tests only
cd morphio-core && uv run pytest

# Run morphio-io tests only
cd morphio-io && make test
```
