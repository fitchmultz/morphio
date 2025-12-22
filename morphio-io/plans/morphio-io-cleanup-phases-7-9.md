# Morphio-IO Cleanup: Phases 7-9

> Continuation of [extract-morphio-core-library.md](./extract-morphio-core-library.md)
>
> Phases 1-6 extracted morphio-core as a standalone library. These phases complete the migration by removing duplicated code from morphio-io.

---

## Overview

**Problem**: morphio-io still contains ~1,333 lines of code that duplicates morphio-core functionality.

**Goal**: Replace duplicates with adapters that wrap morphio-core, removing ~1,000+ lines.

---

## Phase 7: Quick Wins

Simple migrations with minimal risk.

### 7.1 Speaker Alignment
- [ ] Replace `app/services/audio/speaker_alignment.py` with morphio-core import
- [ ] Update imports in `app/services/audio/pipeline.py`
- [ ] Run tests

**Files**: `app/services/audio/speaker_alignment.py` (~100 lines)
**Target**: `morphio_core.audio.alignment`

### 7.2 URL Validation (Use Existing Adapter)
- [ ] Find services doing URL validation manually
- [ ] Update to import from `app/adapters/url_validation.py`
- [ ] Run tests

**Files**: Adapter already exists, just needs to be used

### 7.3 FFmpeg Utilities
- [ ] Create `app/adapters/media.py`
- [ ] Wrap `run_ffmpeg()`, `probe_duration()`, `convert_to_audio()`
- [ ] Update `app/services/video/conversion.py` to use adapter
- [ ] Run tests

**Files**: `app/services/video/conversion.py` (~40 lines)
**Target**: `morphio_core.media.ffmpeg`

### 7.4 Anonymizer
- [ ] Create `app/adapters/anonymizer.py`
- [ ] Wrap `Anonymizer` class with exception translation
- [ ] Update/remove `app/utils/anonymizer.py`
- [ ] Run tests

**Files**: `app/utils/anonymizer.py` (~60 lines)
**Target**: `morphio_core.security.anonymizer`

---

## Phase 8: Audio Services Migration

Replace audio processing with morphio-core implementations.

### 8.1 Audio Chunking
- [ ] Create `app/adapters/audio.py` (or extend existing)
- [ ] Wrap `chunk_audio()`, `segment_audio_fast()`, `cleanup_chunks()`
- [ ] Translate `AudioChunkingError` → `ApplicationException`
- [ ] Update `app/services/audio/chunking.py` to thin wrapper or delete
- [ ] Update imports in `app/services/audio/__init__.py`
- [ ] Run tests

**Files**: `app/services/audio/chunking.py` (~217 lines)
**Target**: `morphio_core.audio.chunking`

### 8.2 Audio Transcription
- [ ] Extend `app/adapters/audio.py` with transcription wrapper
- [ ] Wrap `Transcriber` class
- [ ] Keep morphio-io specific logic:
  - Caching (`cache_utils`)
  - Semaphore management (`_TRANSCRIBE_SEM`)
- [ ] Translate `TranscriptionError` → `ApplicationException`
- [ ] Update `app/services/audio/transcription.py` to use adapter
- [ ] Run tests

**Files**: `app/services/audio/transcription.py` (~388 lines → ~100 lines)
**Target**: `morphio_core.audio.transcription.Transcriber`

---

## Phase 9: LLM Integration

Major refactor of generation services.

### 9.1 Create LLM Adapter
- [ ] Create `app/adapters/llm.py`
- [ ] Instantiate `LLMRouter` from morphio-core
- [ ] Handle config loading from settings
- [ ] Translate LLM exceptions → `ApplicationException`

**Target**: `morphio_core.llm.LLMRouter`

### 9.2 Refactor Generation Core
- [ ] Update `app/services/generation/core.py` to use LLM adapter
- [ ] Remove inline provider logic (~350 lines):
  - `_resolve_openai_model()`
  - `_resolve_gemini_model()`
  - Provider selection if/else chains
  - Message format conversion per provider
- [ ] Keep morphio-io specific logic:
  - Rate limiting
  - Usage tracking
  - Request logging
- [ ] Run tests

**Files**: `app/services/generation/core.py` (~478 lines → ~150 lines)

### 9.3 Verify All Generation Endpoints
- [ ] Test `/api/generate` endpoints
- [ ] Test all model providers (OpenAI, Anthropic, Gemini)
- [ ] Verify streaming still works
- [ ] Run full test suite

---

## Acceptance Criteria

- [ ] All morphio-io tests pass
- [ ] No duplicate implementations remain (only adapters)
- [ ] `uv run ruff check .` passes
- [ ] Adapters handle all exception translation
- [ ] ~1,000+ lines removed from morphio-io

---

## Estimated Effort

| Phase | Effort | Lines Removed |
|-------|--------|---------------|
| 7 | 4-6 hrs | ~250 |
| 8 | 8-12 hrs | ~500 |
| 9 | 8-12 hrs | ~350 |
| **Total** | **20-30 hrs** | **~1,100** |
