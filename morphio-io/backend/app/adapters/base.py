"""
Base protocol and documentation for morphio-core adapters.

Adapters are the SINGLE integration point between morphio-io and morphio-core.
They enforce a clean architectural boundary by:

1. Being the ONLY place that imports from morphio-core
2. Translating morphio-core exceptions to ApplicationException
3. Bridging application settings to library config objects
4. Providing thin wrappers that preserve morphio-core's interface

Exception Translation Guide
===========================

| morphio-core Exception     | HTTP Status | Use Case                     |
|----------------------------|-------------|------------------------------|
| SSRFBlockedError           | 400         | URL blocked by SSRF rules    |
| UnsupportedURLError        | 400         | Invalid video URL format     |
| ValidationError (Pydantic) | 400         | Bad user input               |
| TranscriptionError         | 500         | Whisper transcription failed |
| AudioChunkingError         | 500         | FFmpeg chunking failed       |
| LLMProviderError           | 500         | Provider API error           |
| DownloadError              | 500         | Video download failed        |
| FFmpegError                | 500         | Media processing failed      |

Adapter Requirements
====================

All adapters MUST:

1. Import ONLY from morphio-core (no direct SDK imports)
   ```python
   # Good
   from morphio_core.llm import LLMRouter, Message

   # Bad - direct SDK in adapter
   from openai import AsyncOpenAI
   ```

2. Translate ALL morphio-core exceptions to ApplicationException
   ```python
   from morphio_core.exceptions import DownloadError
   from app.exceptions import ApplicationException

   try:
       result = await morphio_core_function()
   except DownloadError as e:
       raise ApplicationException(str(e), status_code=500)
   ```

3. Inject configuration from settings (no global imports in morphio-core)
   ```python
   from app.config import settings
   from morphio_core.llm import ProviderConfig

   config = ProviderConfig(
       api_key=settings.openai_api_key,
       default_model=settings.default_model,
   )
   ```

4. Provide stable APIs that services can depend on
   - Adapter function signatures should be stable
   - Internal morphio-core changes should not break services

Directory Structure
===================

app/adapters/
├── __init__.py         # Re-exports for convenience
├── base.py             # This file - documentation and protocols
├── llm.py              # LLM router + model alias resolution
├── audio.py            # Chunking + transcription
├── video.py            # YouTube URL parsing + downloads
├── url_validation.py   # SSRF protection
├── anonymizer.py       # PII removal
├── media.py            # FFmpeg utilities
└── speaker_alignment.py # Speaker diarization

Testing Adapters
================

Each adapter should have tests that verify:

1. Exception translation is correct
   ```python
   @pytest.mark.asyncio
   async def test_download_error_translates_to_500():
       with patch('morphio_core.video.download_video_audio') as mock:
           mock.side_effect = DownloadError("Network error")
           with pytest.raises(ApplicationException) as exc:
               await download_video_via_ytdlp(url, path)
           assert exc.value.status_code == 500
   ```

2. Configuration is properly injected
3. Return types match expected interfaces
"""

from typing import Protocol, TypeVar

T = TypeVar("T")


class MorphioAdapter(Protocol):
    """
    Protocol marker for morphio-core adapters.

    This is primarily for documentation purposes. Adapters don't need
    to explicitly implement this protocol, but should follow its principles.

    Principles:
    - Single responsibility: one adapter per morphio-core module
    - Exception translation: library errors → HTTP errors
    - Configuration injection: settings → explicit config objects
    - Thin wrappers: minimal logic, delegate to morphio-core
    """

    pass
