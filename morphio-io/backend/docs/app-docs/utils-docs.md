# Utilities Documentation

## Overview

Helper functions, enums, and decorators in `app/utils/`.

## Enums (`enums.py`)

### JobStatus

```python
class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

### ProcessingStage

Detailed stages for job progress tracking:

```python
class ProcessingStage(str, Enum):
    QUEUED = "queued"
    DOWNLOADING = "downloading"
    CHUNKING = "chunking"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    GENERATING = "generating"
    SAVING = "saving"
    COMPLETED = "completed"
    FAILED = "failed"
```

### UsageType

```python
class UsageType(str, Enum):
    VIDEO_PROCESSING = "VIDEO_PROCESSING"
    AUDIO_PROCESSING = "AUDIO_PROCESSING"
    WEB_SCRAPING = "WEB_SCRAPING"
    CONTENT_GENERATION = "CONTENT_GENERATION"
    LOG_PROCESSING = "LOG_PROCESSING"
    OTHER = "OTHER"
```

## Decorators (`decorators.py`)

### @rate_limit

```python
@rate_limit(limit="60/minute")
async def my_route():
    ...
```

Uses slowapi with Redis backend. Falls back to in-memory if Redis unavailable.

## Response Helpers (`response_utils.py`)

```python
def success_response(data, message="Success"):
    return {"status": "success", "message": message, "data": data}

def error_response(message, status_code=400):
    return {"status": "error", "message": message}
```

## Job Utilities (`job_utils.py`)

```python
def generate_job_id() -> str:
    return str(uuid.uuid4())
```

## Cache Utilities (`cache_utils.py`)

Redis caching helpers for job status and other temporary data.

## File Utilities (`file_utils.py`)

- Safe file handling
- Extension validation
- Temporary file management

## Logging (`logging_config.py`)

Structured logging setup with configurable levels.

## Related Files

- `app/utils/` - All utility modules
- `app/services/job/status.py` - Job status management
- `app/services/usage/tracking.py` - Usage tracking helpers
