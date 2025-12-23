# morphio-core

Reusable Python library for audio processing, LLM orchestration, and security utilities.

## Installation

```bash
# Install with all features
uv add morphio-core[all]

# Install specific features
uv add morphio-core[llm]        # LLM providers only
uv add morphio-core[video]      # Video downloading
uv add morphio-core[whisper-mlx]  # Apple Silicon transcription
```

## Features

- **Audio Processing**: Chunking, transcription (MLX/faster-whisper), speaker alignment
- **LLM Routing**: Multi-provider support (OpenAI, Anthropic, Gemini) with streaming
- **Security**: URL validation with SSRF protection, content anonymization
- **Video**: YouTube URL parsing, video downloading via yt-dlp

## Quick Start

### URL Validation (SSRF Protection)

```python
from morphio_core.security import URLValidator

validator = URLValidator()
validator.validate("https://api.example.com/webhook")  # Raises if blocked
```

### Content Anonymization

```python
from morphio_core.security import Anonymizer

anonymizer = Anonymizer()
safe_text = anonymizer.anonymize("Contact: john@example.com")
# safe_text = "Contact: [EMAIL_1]"
```

### FFmpeg Utilities

```python
from morphio_core.media import probe_duration, convert_to_audio
from pathlib import Path

duration = await probe_duration(Path("video.mp4"))
await convert_to_audio(Path("video.mp4"), Path("audio.mp3"))
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
