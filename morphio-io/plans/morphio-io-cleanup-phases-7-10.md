> **📁 ARCHIVED** on 2025-12-23 — This plan has been completed. See [docs/status.md](../../docs/status.md) for current project status and [docs/plans/phase-11-completion.md](../../docs/plans/phase-11-completion.md) for completion details.

# Morphio-IO Cleanup: Phases 7-10

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

## Phase 8: Audio Services Migration ✅ COMPLETE

Replace audio processing with morphio-core implementations.

### 8.1 Audio Chunking ✅
- [x] Created `app/adapters/audio.py` with chunking wrappers
- [x] Wrapped `chunk_audio()`, `segment_audio_fast()`, `cleanup_chunks()`
- [x] Translates `AudioChunkingError` → `ApplicationException`
- [x] Converted `app/services/audio/chunking.py` to re-export stub

**Result**: 217 lines → 22 lines

### 8.2 Audio Transcription ✅
- [x] Extended `app/adapters/audio.py` with transcription wrappers
- [x] Wrapped `Transcriber` class via `transcribe_local()` and `transcribe_with_word_timestamps()`
- [x] Kept morphio-io specific logic:
  - Caching (`cache_utils`)
  - Semaphore management (`_TRANSCRIBE_SEM`)
  - Remote ML worker fallback
- [x] Translates `TranscriptionError` → `ApplicationException`
- [x] All 29 unit tests pass

**Result**: 388 lines → ~100 lines (kept caching/semaphore logic)

---

## Phase 9: LLM Integration ✅ COMPLETE

LLM adapter created. Generation core retains advanced provider features.

### 9.1 Create LLM Adapter ✅
- [x] Created `app/adapters/llm.py`
- [x] Provides `get_llm_router()` configured from settings
- [x] Provides `simple_completion()` for basic completions
- [x] Translates `LLMProviderError` → `ApplicationException`

**Target**: `morphio_core.llm.LLMRouter`

### 9.2 Refactor Generation Core ✅ (Partial)
- [x] Created LLM adapter for simple completions
- [x] Generation core retains advanced provider features not supported by morphio-core:
  - Gemini thinking levels (ThinkingConfig)
  - OpenAI reasoning effort parameters
  - Model aliases (gpt-5.1-low, gemini-3-flash-preview-medium)
- [x] All linting passes

**Note**: Full refactor deferred since morphio-core's LLMRouter doesn't support thinking levels or reasoning effort.

### 9.3 Verify All Generation Endpoints ✅
- [x] All imports work correctly
- [x] Linting passes
- [x] Unit tests pass

---

## Phase 10: Monorepo Cleanup ✅ COMPLETE

Organized morphio-all as a proper monorepo.

### 10.1 Root Makefile ✅
- [x] Created root `Makefile` with unified commands:
  - `make dev` - Start morphio-io dev environment
  - `make test` - Run all tests (morphio-core + morphio-io)
  - `make lint` - Lint everything
  - `make ci` - Full CI gate
- [x] Delegates to child Makefiles/commands

### 10.2 Update Root README ✅
- [x] Rewrote `README.md` to describe monorepo structure
- [x] Documented relationship between morphio-core and morphio-io
- [x] Added quick start for both projects
- [x] Removed outdated standalone app description

### 10.3 Verify Docker Configuration ✅
- [x] Checked `morphio-io/docker-compose.yml` - uses container names, not paths
- [x] No hardcoded paths that would break from new location

### 10.4 Clean Up Artifacts ✅
- [x] Updated root `.gitignore` with comprehensive patterns
- [x] Verified no orphaned config files
- [x] Archive directory properly ignored

### 10.5 Workspace Configuration
- [x] Keeping projects independent (current approach works well)
- [x] morphio-io uses path dependency to morphio-core

---

## Acceptance Criteria

- [x] All morphio-io tests pass (29 unit tests)
- [x] Adapters wrap morphio-core functionality
- [x] `uv run ruff check .` passes
- [x] Adapters handle all exception translation
- [x] ~600+ lines removed from morphio-io (chunking, transcription, speaker alignment)

---

## Final Results

| Phase | Status | Lines Changed |
|-------|--------|---------------|
| 7 | ✅ Complete | ~388 lines → ~82 lines |
| 8 | ✅ Complete | ~605 lines → ~122 lines |
| 9 | ✅ Complete | Created adapter, kept advanced features |
| 10 | ✅ Complete | Monorepo organized |

**Total lines removed**: ~500+ lines of duplicated code replaced with thin adapters.

**Key adapters created**:
- `app/adapters/audio.py` - Chunking and transcription
- `app/adapters/llm.py` - LLM router configuration
- `app/adapters/speaker_alignment.py` - Speaker alignment (from Phase 7)
- `app/adapters/media.py` - FFmpeg utilities (from Phase 7)
- `app/adapters/anonymizer.py` - Content anonymization (from Phase 7)
