> **📁 ARCHIVED** on 2025-12-23 — This plan has been completed. See [docs/status.md](../docs/status.md) for current project status and [docs/plans/phase-11-completion.md](../docs/plans/phase-11-completion.md) for completion details.

# Morphio-IO Final Cleanup & LLM Provider Enhancement

## Status: PHASE 11 - CONSOLIDATION

The basic migration (Phases 1-10) is complete. This plan addresses:
1. Consolidating advanced LLM features into morphio-core
2. Removing backward compatibility layers
3. Adding adapter tests and documentation

---

## Executive Summary

| Metric | Status | Details |
|--------|--------|---------|
| **Migration Completeness** | 100% | All phases 1-10 complete |
| **Architecture Compliance** | 95% | One documented exception |
| **Test Coverage** | Passing | 133 core + 79 io tests |
| **Linting** | All checks passed | `ruff check .` clean |
| **Lines Removed** | ~500+ | Duplicated code eliminated |

---

## Current Architecture

```
morphio-io/backend/
├── app/
│   ├── adapters/                    # ONLY place that imports morphio-core
│   │   ├── audio.py                 # Chunking + transcription (324 lines)
│   │   ├── llm.py                   # LLM routing (168 lines)
│   │   ├── speaker_alignment.py     # Speaker diarization (163 lines)
│   │   ├── media.py                 # FFmpeg utilities (116 lines)
│   │   ├── video.py                 # YouTube/yt-dlp (101 lines)
│   │   ├── url_validation.py        # SSRF protection (54 lines)
│   │   └── anonymizer.py            # PII removal (13 lines)
│   │
│   ├── services/                    # Uses adapters, NOT morphio-core directly
│   │   └── generation/core.py       # EXCEPTION: Direct SDK for advanced features
│   │
│   └── utils/                       # Backward compatibility re-exports
│       ├── youtube_utils.py         # Re-exports from adapters/video.py
│       └── anonymizer.py            # Re-exports from adapters/anonymizer.py
│
└── morphio-core (path dependency)
    └── src/morphio_core/
        ├── audio/      # Chunking, transcription, speaker alignment
        ├── llm/        # Multi-provider router
        ├── media/      # FFmpeg utilities
        ├── security/   # SSRF protection, anonymizer
        └── video/      # YouTube URL parsing, downloads
```

---

## Verification Results

### Architecture Compliance Audit

| Check | Result | Evidence |
|-------|--------|----------|
| morphio-core imports ONLY in adapters | ✅ | `grep "from morphio_core"` returns only adapter files |
| No direct morphio-core imports in services | ✅ | Services use adapters exclusively |
| No direct morphio-core imports in routes | ✅ | Routes use services/adapters |
| Exception translation in all adapters | ✅ | All translate to ApplicationException |
| Backward compatibility maintained | ✅ | Utils re-export from adapters |

### Exception Translation Mapping

| morphio-core Exception | → | HTTP Status | Adapter |
|------------------------|---|-------------|---------|
| `AudioChunkingError` | → | 500 | audio.py |
| `TranscriptionError` | → | 500 | audio.py |
| `LLMProviderError` | → | 500 | llm.py |
| `FFmpegError` | → | 500 | media.py |
| `SSRFBlockedError` | → | 400 | url_validation.py |
| `DownloadError` | → | 500 | video.py |
| `UnsupportedURLError` | → | 400 | video.py |

### Test Results

```bash
# morphio-core: 133 tests passing
cd morphio-core && uv run pytest -v
# Result: 133 passed

# morphio-io: 79 tests passing
cd morphio-io/backend && uv run pytest
# Result: 79 passed

# Linting: All checks passed
cd morphio-io/backend && uv run ruff check .
# Result: All checks passed!
```

---

---

## Phase 11: LLM Provider Enhancement & Cleanup

### Problem Statement

`services/generation/core.py` currently uses **direct SDK imports** for advanced features:

| Feature | SDK | Current Location |
|---------|-----|------------------|
| `thinking_level` | `google.genai.types` | generation/core.py:76-99 |
| `reasoning_effort` | OpenAI API | generation/core.py:61-73 |
| Model aliases | Both | generation/core.py:12-29 |

**Why these SHOULD be in morphio-core:**
- morphio-core's LLMRouter already abstracts providers
- Advanced features are provider-agnostic concepts (reasoning intensity)
- Keeps all LLM logic in one place for reuse
- Reduces morphio-io's SDK dependencies

---

### 11.1 Extend morphio-core LLM Providers

#### Task A: Add `thinking_level` to Gemini Provider

**File**: `morphio-core/src/morphio_core/llm/providers/gemini.py`

**Current**:
```python
config = types.GenerateContentConfig(
    temperature=temperature,
    max_output_tokens=max_tokens,
)
```

**Target**:
```python
async def generate(
    self,
    messages: list[Message],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    thinking_level: str | None = None,  # NEW: "minimal", "low", "medium", "high"
) -> GenerationResult:
    ...
    config_params = {
        "temperature": temperature,
        "max_output_tokens": max_tokens,
    }
    if thinking_level:
        from google.genai import types
        config_params["thinking_config"] = types.ThinkingConfig(
            thinking_level=thinking_level
        )
    config = types.GenerateContentConfig(**config_params)
```

**Acceptance Criteria**:
- [ ] `thinking_level` parameter added to `generate()` and `stream()`
- [ ] Validates thinking_level is valid string
- [ ] Gemini Pro models only support HIGH/LOW (log warning for others)
- [ ] Tests added for thinking_level functionality

---

#### Task B: Add `reasoning_effort` to OpenAI Provider

**File**: `morphio-core/src/morphio_core/llm/providers/openai.py`

**Target**:
```python
async def generate(
    self,
    messages: list[Message],
    *,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    reasoning_effort: str | None = None,  # NEW: "low", "medium", "high"
) -> GenerationResult:
    ...
    if reasoning_effort:
        api_params["reasoning_effort"] = reasoning_effort
```

**Acceptance Criteria**:
- [ ] `reasoning_effort` parameter added to `generate()` and `stream()`
- [ ] Only applied to o1/o3 series models (validate or pass through)
- [ ] Tests added for reasoning_effort functionality

---

#### Task C: Update LLMRouter for Provider-Specific Kwargs

**File**: `morphio-core/src/morphio_core/llm/router.py`

**Target**:
```python
async def generate(
    self,
    messages: list[Message],
    *,
    provider: ProviderName | None = None,
    model: str | None = None,
    max_tokens: int | None = None,
    temperature: float | None = None,
    **provider_kwargs,  # NEW: Pass through to provider
) -> GenerationResult:
    llm = self._resolve_provider(provider)
    return await llm.generate(
        messages,
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        **provider_kwargs,
    )
```

**Acceptance Criteria**:
- [ ] Router passes through `**provider_kwargs`
- [ ] Each provider ignores unknown kwargs gracefully
- [ ] Tests verify kwargs reach providers

---

#### Task D: Optional Model Alias Resolution

**Decision Point**: Should model aliases like `gpt-5.1-low` be resolved in:
1. **morphio-core router** - Centralized, reusable
2. **morphio-io adapter** - Application-specific, more flexible

**Recommendation**: Keep aliases in **morphio-io adapter** for now:
- Aliases are morphio-io's UI concept
- Different applications may have different alias schemes
- Core library should accept any model string

---

### 11.2 Migrate generation/core.py to Use Adapter

After extending morphio-core providers:

**File**: `morphio-io/backend/app/adapters/llm.py`

**Add**:
```python
async def generate_with_reasoning(
    messages: list[dict[str, str]],
    *,
    model: str,
    thinking_level: str | None = None,  # For Gemini
    reasoning_effort: str | None = None,  # For OpenAI
    max_tokens: int | None = None,
    temperature: float | None = None,
) -> str:
    """Generate with advanced reasoning features via morphio-core."""
    router = get_llm_router()

    # Resolve model aliases (application-specific)
    base_model, provider_kwargs = _resolve_model_alias(model, thinking_level, reasoning_effort)

    try:
        result = await router.generate(
            [Message(**m) for m in messages],
            model=base_model,
            max_tokens=max_tokens,
            temperature=temperature,
            **provider_kwargs,
        )
        return result.content
    except LLMProviderError as e:
        raise ApplicationException(str(e), status_code=500)
```

**Then refactor**: `services/generation/core.py` to use `adapters/llm.py`

**Acceptance Criteria**:
- [ ] All direct SDK imports removed from generation/core.py
- [ ] Uses adapter for ALL LLM calls
- [ ] Existing behavior preserved (all tests pass)
- [ ] ~200+ lines removed from generation/core.py

---

### 11.3 Remove Backward Compatibility Layers

**Files to DELETE**:
- `morphio-io/backend/app/utils/youtube_utils.py`
- `morphio-io/backend/app/utils/anonymizer.py`

**Before deleting**: Update all imports to use adapters directly.

**Find usages**:
```bash
grep -r "from app.utils.youtube_utils" morphio-io/backend/
grep -r "from app.utils.anonymizer" morphio-io/backend/
```

**Acceptance Criteria**:
- [ ] No imports from `utils/youtube_utils.py` anywhere
- [ ] No imports from `utils/anonymizer.py` anywhere
- [ ] Files deleted
- [ ] All tests pass

---

### 11.4 Create Adapter Test Suite

**Directory**: `morphio-io/backend/tests/unit/adapters/`

**Files**:
```
tests/unit/adapters/
├── __init__.py
├── conftest.py           # Shared fixtures
├── test_audio.py
├── test_llm.py
├── test_video.py
├── test_url_validation.py
├── test_speaker_alignment.py
├── test_media.py
└── test_anonymizer.py
```

**Test Patterns**:
```python
# tests/unit/adapters/test_video.py
import pytest
from unittest.mock import patch, AsyncMock
from app.adapters.video import download_video_via_ytdlp
from app.exceptions import ApplicationException
from morphio_core.exceptions import DownloadError

@pytest.mark.asyncio
async def test_download_error_translates_to_500():
    """Verify DownloadError from morphio-core maps to HTTP 500."""
    with patch('app.adapters.video.download_video_audio', new_callable=AsyncMock) as mock:
        mock.side_effect = DownloadError("Network failure")

        with pytest.raises(ApplicationException) as exc_info:
            await download_video_via_ytdlp("https://youtube.com/watch?v=test", "/tmp")

        assert exc_info.value.status_code == 500
        assert "Network failure" in str(exc_info.value)

@pytest.mark.asyncio
async def test_unsupported_url_translates_to_400():
    """Verify UnsupportedURLError maps to HTTP 400."""
    from morphio_core.exceptions import UnsupportedURLError

    with patch('app.adapters.video.download_video_audio', new_callable=AsyncMock) as mock:
        mock.side_effect = UnsupportedURLError("Not a valid video URL")

        with pytest.raises(ApplicationException) as exc_info:
            await download_video_via_ytdlp("https://invalid.com", "/tmp")

        assert exc_info.value.status_code == 400
```

**Acceptance Criteria**:
- [ ] Test file for each adapter
- [ ] Tests for ALL exception translations
- [ ] Tests for type conversion where applicable
- [ ] At least 20 new adapter tests

---

### 11.5 Create Adapter Protocol

**File**: `morphio-io/backend/app/adapters/base.py`

```python
"""
Base protocol for morphio-core adapters.

All adapters MUST:
1. Import from morphio-core ONLY (no direct SDK imports)
2. Translate morphio-core exceptions to ApplicationException
3. Provide thin wrappers that preserve morphio-core's interface

Exception Translation Guide:
| morphio-core Exception    | → HTTP Status | Notes                    |
|---------------------------|---------------|--------------------------|
| ValidationError variants  | 400           | Bad user input           |
| AuthenticationError       | 401           | Missing/invalid API key  |
| NotFoundError variants    | 404           | Resource not found       |
| RateLimitError           | 429           | Provider rate limited    |
| All other errors          | 500           | Server/internal error    |
"""
from typing import Protocol, TypeVar, Callable, Awaitable, Any

T = TypeVar("T")

class MorphioAdapter(Protocol):
    \"\"\"Protocol for morphio-core adapter compliance.

    Adapters are the ONLY place that imports from morphio-core.
    They translate library concerns to HTTP concerns.
    \"\"\"
    pass
```

**Acceptance Criteria**:
- [ ] `base.py` created with documentation
- [ ] Exception translation guide included
- [ ] Optional: Type annotations for common patterns

---

## Implementation Order

### Phase 11.1: morphio-core LLM Enhancements (Required)
1. Add `thinking_level` to Gemini provider
2. Add `reasoning_effort` to OpenAI provider
3. Update router to pass `**provider_kwargs`
4. Add tests for new features
5. Run `uv run pytest` in morphio-core (target: 140+ tests)

### Phase 11.2: morphio-io LLM Migration (Required)
1. Extend `adapters/llm.py` with model alias resolution
2. Refactor `services/generation/core.py` to use adapter
3. Remove direct SDK imports from generation/core.py
4. Run `make ci` (all tests must pass)

### Phase 11.3: Remove Backward Compat Layers (Required)
1. Find all usages of utils/youtube_utils.py and utils/anonymizer.py
2. Update imports to use adapters directly
3. Delete the compatibility files
4. Run `make ci`

### Phase 11.4: Testing & Documentation (Required)
1. Create adapter test suite (20+ tests)
2. Create adapter protocol base class
3. Update CLAUDE.md if needed

---

## Phase 11 Acceptance Criteria

- [ ] `thinking_level` support in morphio-core Gemini provider
- [ ] `reasoning_effort` support in morphio-core OpenAI provider
- [ ] Router passes `**provider_kwargs` to providers
- [ ] `services/generation/core.py` has NO direct SDK imports
- [ ] `utils/youtube_utils.py` deleted (imports updated)
- [ ] `utils/anonymizer.py` deleted (imports updated)
- [ ] 20+ adapter tests created
- [ ] `app/adapters/base.py` protocol created
- [ ] All morphio-core tests pass (140+ expected)
- [ ] All morphio-io tests pass
- [ ] `make ci` passes

---

## References

- Original extraction plan: `morphio-io/plans/extract-morphio-core-library.md`
- Cleanup phases 7-10: `morphio-io/plans/morphio-io-cleanup-phases-7-10.md`
- Shared documentation: `docs/using-morphio-core.md`
- Root CLAUDE.md: `CLAUDE.md` (monorepo guidelines)
