# Morphio-IO Cleanup: Phases 7-9

> Continuation of [extract-morphio-core-library.md](./extract-morphio-core-library.md)
>
> Phases 1-6 extracted morphio-core as a standalone library. These phases complete the migration by removing duplicated code from morphio-io.

---

## Overview

**Problem**: morphio-io still contains ~1,333 lines of code that duplicates morphio-core functionality.

**Goal**: Replace duplicates with adapters that wrap morphio-core, removing ~1,000+ lines.

---

## Phase 7: Quick Wins ✅ COMPLETE

Simple migrations with minimal risk.

### 7.1 Speaker Alignment ✅
- [x] Created `app/adapters/speaker_alignment.py` wrapping morphio-core
- [x] Converted `app/services/audio/speaker_alignment.py` to re-export stub
- [x] All 20 speaker alignment tests pass

**Result**: 253 lines → 22 lines

### 7.2 URL Validation ✅
- [x] Updated `app/services/web/validation.py` to use url_validation adapter
- [x] Now uses morphio-core's comprehensive SSRF protection (checks ALL DNS records)

**Result**: 33 lines → 27 lines (but much more secure)

### 7.3 FFmpeg Utilities ✅
- [x] Created `app/adapters/media.py` with exception translation
- [x] Converted `app/services/video/conversion.py` to re-export stub

**Result**: 41 lines → 15 lines

### 7.4 Anonymizer ✅
- [x] Created `app/adapters/anonymizer.py`
- [x] Converted `app/utils/anonymizer.py` to re-export stub
- [x] Now handles: EMAIL, PHONE, CREDIT_CARD, SSN, IP_ADDRESS

**Result**: 61 lines → 18 lines (plus more PII coverage)

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
