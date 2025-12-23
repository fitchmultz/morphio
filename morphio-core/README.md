# morphio-core

Reusable Python library for audio processing, LLM orchestration, and security utilities.

## Installation

```bash
# Install with all features
uv add morphio-core[all]

# Install specific features
uv add morphio-core[llm]          # LLM providers only
uv add morphio-core[video]        # Video downloading
uv add morphio-core[whisper-mlx]  # Apple Silicon transcription
uv add morphio-core[whisper-cuda] # NVIDIA GPU transcription
uv add morphio-core[cli]          # Command-line interface
```

## Features

- **Audio Processing**: Chunking, transcription (MLX/faster-whisper), speaker alignment
- **LLM Routing**: Multi-provider support (OpenAI, Anthropic, Gemini) with streaming
- **Security**: URL validation with SSRF protection, content anonymization
- **Video**: YouTube URL parsing, video downloading via yt-dlp
- **CLI**: Command-line tools for standalone usage

## Quick Start

### LLM Router

```python
from morphio_core.llm import create_router, Message

# Create router with multiple providers
router = create_router(
    openai_api_key="sk-...",
    anthropic_api_key="sk-ant-...",
    default_provider="openai",
)

# Generate completion
result = await router.generate([
    Message(role="user", content="Hello!")
])
print(result.content)

# Stream responses
async for event in router.stream([Message(role="user", content="Hello!")]):
    if event.type == "delta":
        print(event.text, end="")
```

### Custom LLM Provider

```python
from morphio_core.llm import LLMConfig, LLMRouter, ProviderConfig
from pydantic import SecretStr

# Define your custom provider factory
def my_provider_factory(config: ProviderConfig):
    return MyCustomProvider(api_key=config.api_key, model=config.default_model)

# Register it
config = LLMConfig(
    custom_providers={"my-llm": my_provider_factory},
    custom_configs={"my-llm": ProviderConfig(
        api_key=SecretStr("..."),
        default_model="my-model",
    )},
    default_provider="my-llm",
)
router = LLMRouter(config)
```

### Audio Transcription

```python
from morphio_core.audio import transcribe_audio, TranscriptionConfig

# Transcribe with auto-detected backend
result = transcribe_audio("audio.mp3")
print(f"Text: {result.text}")
print(f"Backend: {result.backend_used} ({result.device_used})")

# With specific configuration
config = TranscriptionConfig(
    model="large-v3",
    language="en",
    word_timestamps=True,
)
result = transcribe_audio("audio.mp3", config=config)
```

### Audio Chunking

```python
from morphio_core.audio import chunk_audio, ChunkingConfig

# Chunk long audio for processing
result = await chunk_audio(
    "long_audio.mp3",
    "/tmp/chunks",
    config=ChunkingConfig(
        segment_duration=300,  # 5 minutes
        overlap_ms=1000,       # 1 second overlap
    ),
)

for chunk in result.chunks:
    print(f"Chunk: {chunk.chunk_path} ({chunk.start_time}-{chunk.end_time}s)")
```

### URL Validation (SSRF Protection)

```python
from morphio_core.security import URLValidator, URLValidatorConfig

# Default: blocks private IPs, localhost, etc.
validator = URLValidator()
validator.validate("https://api.example.com")  # OK
validator.validate("http://192.168.1.1")       # Raises SSRFBlockedError

# Custom configuration
config = URLValidatorConfig(
    allow_private_ips=True,  # For internal services
    blocked_hosts=["evil.com"],
)
validator = URLValidator(config)
```

### Content Anonymization

```python
from morphio_core.security import Anonymizer

anonymizer = Anonymizer()

# Anonymize sensitive content
text = "Contact John at john@example.com or 555-123-4567"
safe = anonymizer.anonymize(text)
# "Contact John at [EMAIL_1] or [PHONE_1]"

# Restore original content
original = anonymizer.deanonymize(safe)
```

### FFmpeg Utilities

```python
from morphio_core.media import FFmpegConfig, probe_duration, convert_to_audio
from pathlib import Path

# Auto-detect FFmpeg (default)
duration = await probe_duration(Path("video.mp4"))
await convert_to_audio(Path("video.mp4"), Path("audio.mp3"))

# Custom FFmpeg path (containers, non-standard installs)
config = FFmpegConfig(
    ffmpeg_path="/opt/ffmpeg/bin/ffmpeg",
    ffprobe_path="/opt/ffmpeg/bin/ffprobe",
)
duration = await probe_duration(Path("video.mp4"), config=config)
```

### Video Downloading

```python
from morphio_core.video import download_video_audio, DownloadConfig

# Download audio from video URL
result = await download_video_audio(
    "https://youtube.com/watch?v=...",
    "/tmp/downloads",
)
print(f"Downloaded: {result.output_path}")

# With custom configuration
config = DownloadConfig(format_spec="bestaudio[ext=m4a]")
result = await download_video_audio(url, output_dir, config=config)
```

## CLI Usage

```bash
# Install CLI dependencies
uv add morphio-core[cli]

# Show system info and available backends
morphio info

# Validate URL for SSRF
morphio validate-url https://api.example.com

# Transcribe audio (requires whisper backend)
morphio transcribe audio.mp3 --model base --output result.json
```

## Design Principles

- **No global settings**: All configuration is explicit via config objects
- **Library exceptions only**: No HTTP status codes - consuming apps handle mapping
- **Protocol-first interfaces**: Easy to mock and test
- **SDK client injection**: Testable without real API calls

## Requirements

- Python 3.11+
- FFmpeg (for audio/video processing)

## License

MIT
