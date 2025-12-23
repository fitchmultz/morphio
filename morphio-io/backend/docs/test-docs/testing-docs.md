# Testing Documentation

## Overview

The backend uses pytest with async support for testing.

## Test Structure

```
tests/
├── unit/           # Unit tests
│   ├── adapters/   # Adapter tests
│   ├── test_adapters.py
│   ├── test_diarization.py
│   └── test_speaker_alignment.py
├── functional/     # Functional tests
│   ├── test_audio_service.py
│   ├── test_authentication.py
│   └── test_caching.py
├── integration/    # Integration tests
│   ├── test_content_conversation.py
│   ├── test_security_csrf.py
│   └── test_worker_ml_and_crawler.py
├── performance/    # Performance benchmarks
│   └── benchmark_whisper.py
├── conftest.py     # Shared fixtures
└── __init__.py
```

## Running Tests

```bash
# From morphio-io/backend or monorepo root
cd morphio-io/backend

# Run all tests
uv run pytest

# Run with verbose output
uv run pytest -v

# Run specific test file
uv run pytest tests/unit/test_adapters.py

# Run tests matching pattern
uv run pytest -k "test_authentication"

# Run with coverage
uv run pytest --cov=app --cov-report=html
```

## From Monorepo Root

```bash
# Run all tests (core + io)
make test

# Run only backend tests
make test-io
```

## Key Fixtures (`conftest.py`)

```python
@pytest.fixture
async def db_session():
    # Async database session for tests

@pytest.fixture
async def test_client():
    # FastAPI TestClient

@pytest.fixture
async def authenticated_client():
    # TestClient with auth headers
```

## Test Categories

### Unit Tests

Test individual functions and classes in isolation:
- Adapters (morphio-core wrappers)
- Utility functions
- Schema validation

### Functional Tests

Test feature workflows:
- Audio/video processing
- Authentication flow
- Caching behavior

### Integration Tests

Test component interactions:
- Database + API
- CSRF protection
- Worker services

### Performance Tests

Benchmark critical paths:
- Whisper transcription
- Large file handling

## Environment

Tests use:
- SQLite in-memory database
- Mocked external services
- Test fixtures for user/content data

## Related Files

- `tests/conftest.py` - Shared fixtures
- `pytest.ini` or `pyproject.toml` - pytest config
- `morphio-io/Makefile` - Test commands