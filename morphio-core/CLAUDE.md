# morphio-core Development Guidelines

Standalone Python library for audio processing, LLM orchestration, video utilities, and security.

## Pre-Commit Requirements

```bash
uv run pytest           # All 133 tests must pass
uv run ruff check .     # Lint must pass
uv run ruff format .    # Format code
```

## Project Structure

```
src/morphio_core/
    __init__.py         # Public API exports
    exceptions.py       # Library-specific exceptions (no HTTP codes)

    security/           # SSRF protection, content anonymization
        url_validator.py
        anonymizer.py
        types.py

    audio/              # Audio chunking, transcription, alignment
        chunking.py
        transcription.py
        alignment.py
        types.py

    llm/                # Multi-provider LLM router
        router.py
        providers/      # OpenAI, Anthropic, Gemini
        parsing.py
        types.py

    video/              # YouTube URL parsing, downloading
        url_utils.py
        download.py
        types.py

    media/              # FFmpeg utilities
        ffmpeg.py

tests/                  # 133 tests covering all modules
```

## Build and Test Commands

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_security.py -v

# Run single test
uv run pytest tests/test_video.py::TestDetectPlatform::test_youtube_standard -v

# Lint
uv run ruff check .

# Format
uv run ruff format .

# Type check (optional, uses ty)
uv run ty check
```

## Code Style Guidelines

- Python 3.13+ with type hints
- snake_case for functions/variables, PascalCase for classes
- Use Ruff for linting and formatting
- Asyncio patterns for async code
- Line length: 100 characters

## Design Principles

### No Global Settings
All functions accept explicit configuration objects:
```python
# Good - explicit config
validator = URLValidator(config=URLValidatorConfig(allow_private=False))

# Bad - global settings
validator = URLValidator()  # reads from global settings
```

### Library Exceptions Only
Raise library-specific exceptions, NOT HTTP exceptions:
```python
# Good - library exception
raise SSRFBlockedError("Private IP detected")

# Bad - HTTP exception
raise HTTPException(status_code=400, detail="Private IP")
```

Consuming applications (like morphio-io) translate these to HTTP errors.

### Protocol-First Interfaces
Use protocols for testability:
```python
class LLMProvider(Protocol):
    async def complete(self, prompt: str) -> str: ...
```

### SDK Client Injection
Allow injecting SDK clients for testing:
```python
# Production
router = create_router(config)

# Testing
mock_client = MockOpenAIClient()
router = create_router(config, openai_client=mock_client)
```

## Module Quick Reference

### Security
```python
from morphio_core.security import URLValidator, Anonymizer

validator = URLValidator()
validator.validate("https://api.example.com")  # Raises SSRFBlockedError if blocked

anonymizer = Anonymizer()
safe = anonymizer.anonymize("Email: john@test.com")  # "Email: [EMAIL_1]"
original = anonymizer.deanonymize(safe)
```

### Audio
```python
from morphio_core.audio import chunk_audio, ChunkingConfig, Transcriber

chunks = list(chunk_audio(audio_path, ChunkingConfig(chunk_duration=300)))

transcriber = Transcriber(...)
result = await transcriber.transcribe(audio_path)
```

### LLM
```python
from morphio_core.llm import create_router, LLMConfig

router = create_router(LLMConfig(providers=[...]))
response = await router.complete("Hello")
```

### Video
```python
from morphio_core.video import detect_platform, extract_youtube_id, download_video_audio

platform = detect_platform("https://youtube.com/watch?v=xxx")  # VideoPlatform.YOUTUBE
video_id = extract_youtube_id("https://youtube.com/watch?v=abc123")  # "abc123"
path = await download_video_audio(url, output_dir)
```

### Media (FFmpeg)
```python
from morphio_core.media import probe_duration, convert_to_audio

duration = await probe_duration(video_path)
await convert_to_audio(input_path, output_path)
```

## Testing Guidelines

- All new features need tests
- Use pytest with asyncio support (`asyncio_mode = "auto"`)
- Mock external services (LLM APIs, yt-dlp, FFmpeg)
- Test both success and error cases

## Relationship to morphio-io

This library is used by morphio-io via path dependency:
```toml
# morphio-io/backend/pyproject.toml
morphio-core = { path = "../../morphio-core", editable = true }
```

morphio-io uses thin adapters (`app/adapters/`) that:
1. Import from morphio-core
2. Translate library exceptions to ApplicationException
3. Keep HTTP concerns out of the library
