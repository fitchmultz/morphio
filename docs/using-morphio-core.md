# Using morphio-core in Your Projects

morphio-core is a standalone Python library for audio processing, LLM orchestration, and security utilities. This guide shows how to use it in your own projects.

## Installation

### Via Git Dependency (Recommended)

Add to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "morphio-core[all]",
    # ... your other dependencies
]

[tool.uv.sources]
morphio-core = { git = "https://github.com/fitchmultz/morphio-all", subdirectory = "morphio-core" }
```

Then install:

```bash
uv sync
```

### Optional Dependencies

morphio-core uses optional dependencies to minimize the base install:

| Extra | Includes | Use Case |
|-------|----------|----------|
| `llm` | OpenAI, Anthropic, Gemini SDKs | LLM routing |
| `video` | yt-dlp | YouTube downloading |
| `whisper-mlx` | mlx-whisper | Transcription on Apple Silicon |
| `whisper-cuda` | faster-whisper | Transcription on NVIDIA GPUs |
| `all` | Everything above | Full functionality |

Install specific extras:

```toml
dependencies = ["morphio-core[llm,video]"]
```

## Quick Examples

### Audio Transcription

```python
from morphio_core.audio import Transcriber

# Auto-detects hardware (MLX on Apple Silicon, CUDA on NVIDIA)
transcriber = Transcriber(model_name="small", word_timestamps=True)
result = transcriber.transcribe("audio.mp3")

print(result.text)
for word in result.words:
    print(f"{word.word} [{word.start:.2f}s - {word.end:.2f}s]")
```

### LLM Router

```python
from morphio_core.llm import LLMRouter
from morphio_core.llm.types import LLMConfig, ProviderConfig, Message

config = LLMConfig(
    openai=ProviderConfig(api_key="sk-...", default_model="gpt-4o"),
    anthropic=ProviderConfig(api_key="sk-ant-...", default_model="claude-sonnet-4-20250514"),
    gemini=ProviderConfig(api_key="...", default_model="gemini-2.0-flash"),
    default_provider="openai",
)

router = LLMRouter(config)

messages = [Message(role="user", content="Hello!")]
result = await router.generate(messages)
print(result.content)
```

### Advanced Reasoning Parameters

The router supports provider-specific parameters via kwargs:

```python
# OpenAI reasoning models (o1, o3 series)
result = await router.generate(
    messages,
    provider="openai",
    model="o1-preview",
    reasoning_effort="high",  # "low", "medium", "high"
)

# Gemini thinking models
result = await router.generate(
    messages,
    provider="gemini",
    model="gemini-2.0-flash-thinking",
    thinking_level="medium",  # "minimal", "low", "medium", "high"
)

# Anthropic extended thinking (Claude 3.5+)
result = await router.generate(
    messages,
    provider="anthropic",
    model="claude-sonnet-4-20250514",
    extended_thinking=True,  # Enable deep reasoning mode
    thinking_budget=10000,   # Optional token budget for thinking
)

# Stream with advanced reasoning
async for event in router.stream(
    messages,
    provider="gemini",
    thinking_level="high",
):
    if event.type == "delta":
        print(event.text, end="")
```

Unknown kwargs are safely ignored, so you can pass parameters without checking provider support:

```python
# Works for any provider - unsupported params are ignored
result = await router.generate(
    messages,
    reasoning_effort="high",  # Ignored if not OpenAI reasoning model
    thinking_level="medium",  # Ignored if not Gemini
)
```

### Token Usage Tracking

Access token usage from generation results:

```python
result = await router.generate(messages)
print(f"Prompt tokens: {result.usage.prompt_tokens}")
print(f"Completion tokens: {result.usage.completion_tokens}")
print(f"Total: {result.usage.total_tokens}")

# Extended usage with provider/model metadata
token_usage = result.get_token_usage()
print(f"Provider: {token_usage.provider}, Model: {token_usage.model}")
print(f"Input: {token_usage.input_tokens}, Output: {token_usage.output_tokens}")
```

### URL Validation (SSRF Protection)

```python
from morphio_core.security import URLValidator
from morphio_core.security.types import URLValidatorConfig

config = URLValidatorConfig(
    allowed_schemes=["https"],
    blocked_hosts=["internal.company.com"],
    allow_private_ips=False,  # Blocks 10.x.x.x, 192.168.x.x, etc.
)

validator = URLValidator(config)

try:
    validator.validate("https://example.com/api")  # OK
    validator.validate("http://localhost:8080")     # Raises SSRFBlockedError
except SSRFBlockedError as e:
    print(f"Blocked: {e}")
```

### YouTube Video Download

```python
from morphio_core.video import YouTubeDownloader
from morphio_core.video.types import DownloadConfig

config = DownloadConfig(
    output_dir="/tmp/videos",
    format="bestaudio",
    audio_only=True,
)

downloader = YouTubeDownloader(config)
result = downloader.download("https://youtube.com/watch?v=...")

print(f"Downloaded: {result.file_path}")
print(f"Title: {result.title}")
print(f"Duration: {result.duration}s")
```

### Content Anonymization

```python
from morphio_core.security import Anonymizer

anonymizer = Anonymizer()

text = "Contact me at john@example.com or 555-123-4567"
cleaned = anonymizer.anonymize(text)
# "Contact me at [EMAIL] or [PHONE]"

# Detects: EMAIL, PHONE, CREDIT_CARD, SSN, IP_ADDRESS
```

## Exception Handling

morphio-core uses library-specific exceptions (no HTTP status codes):

```python
from morphio_core.exceptions import (
    MorphioCoreError,      # Base for all errors
    AudioChunkingError,    # Audio processing failures
    TranscriptionError,    # Whisper/transcription failures
    LLMProviderError,      # LLM API failures
    SSRFBlockedError,      # URL validation blocks
    DownloadError,         # Video download failures
    UnsupportedURLError,   # Invalid video URLs
)

try:
    result = transcriber.transcribe("audio.mp3")
except TranscriptionError as e:
    # Handle transcription failure
    print(f"Transcription failed: {e}")
```

## Design Principles

morphio-core follows these principles:

1. **No global state** - All configuration via explicit config objects
2. **No HTTP concerns** - Library exceptions only, no status codes
3. **Protocol-first** - Interfaces for testability
4. **Optional dependencies** - Install only what you need
5. **SDK injection** - Pass mock clients for testing

## Testing with morphio-core

```python
from unittest.mock import Mock
from morphio_core.llm import LLMRouter

# Inject mock SDK clients
mock_openai = Mock()
mock_openai.chat.completions.create.return_value = Mock(
    choices=[Mock(message=Mock(content="Mocked response"))]
)

router = LLMRouter(config, openai_client=mock_openai)
```

## Pinning to a Specific Version

For stability, pin to a specific commit:

```toml
[tool.uv.sources]
morphio-core = { git = "https://github.com/fitchmultz/morphio-all", rev = "abc123", subdirectory = "morphio-core" }
```

Or use a tag (when available):

```toml
morphio-core = { git = "https://github.com/fitchmultz/morphio-all", tag = "v0.1.0", subdirectory = "morphio-core" }
```
