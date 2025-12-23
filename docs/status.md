# Morphio Project Status

> **Last Updated:** 2025-12-23

## Overview

Morphio is a monorepo containing two main projects:

| Project | Description | Status |
|---------|-------------|--------|
| **morphio-core** | Standalone library for audio/LLM/security utilities | Stable |
| **morphio-io** | Full-stack web application (FastAPI + Next.js) | Active Development |

## Current Versions & Ports

| Component | Version/Port |
|-----------|-------------|
| **Node.js** | ≥24.0.0 |
| **Next.js** | 16.1.1 |
| **Python** | ≥3.13 |
| **Backend API** | Port 8000 |
| **Frontend Dev** | Port 3005 |
| **Frontend Docker** | 3500 → 3000 |

## Quick Start

```bash
# From monorepo root
make install      # Install all dependencies
make dev          # Start backend + frontend
make check        # Run all checks (required before commits)
make test         # Run all tests
```

## Completed Work

### Phases 1-14 ✅ Complete

All core development phases have been completed as of 2025-12-23. See [phase-11-completion.md](./plans/phase-11-completion.md) for detailed breakdown.

**Core Infrastructure:**
- Provider kwargs + Advanced Reasoning in morphio-core (Phases 1-4)
- morphio-io LLM Adapter with model alias resolution (Phase 5)
- Adapter contract + tests with clean separation (Phases 6-7)
- Monorepo dependency alignment to Python ≥3.13 (Phase 8)

**Documentation:**
- Architecture documentation with provider SDK boundary (Phase 9)
- Advanced reasoning examples and usage guides (Phase 9)
- Technical risk documentation (Phase 10)

**Usage & Billing:**
- LLM usage tracking end-to-end (Phase 11)
- Subscription/credits gating with fail-fast behavior (Phase 12)

**User Experience:**
- Processing progress with detailed stages (Phase 13)
  - QUEUED → DOWNLOADING → CHUNKING → TRANSCRIBING → DIARIZING → GENERATING → SAVING

**Security:**
- Production security headers middleware (Phase 14)
- Rate limiting with Redis backend (Phase 14)

## Current Focus: Normalization ✅ Complete

Repository normalization completed on 2025-12-23:

### Configuration Parity ✅
- [x] Align env examples across stack/backend/frontend
- [x] Standardize Redis connection behavior (URL with `/0`)
- [x] Document canonical configuration contract (`docs/configuration.md`)

### Documentation Completeness ✅
- [x] Fill empty backend docs with real content
- [x] Create canonical status page (this file)
- [x] Update version/port references

### Architecture Enforcement ✅
- [x] Enforce provider SDK boundary at repo level (`scripts/audit_imports.sh`)
- [x] Remove SDK imports from config.py

### UI Wiring ✅
- [x] Surface job stage progress in frontend
- [x] Add `/user/credits` endpoint
- [x] Add usage/credits panel to Profile

## Related Documentation

- [Configuration Guide](./configuration.md) - Environment variables and setup
- [Architecture](./architecture.md) - How morphio-io uses morphio-core via adapters
- [Using morphio-core](./using-morphio-core.md) - Library usage examples
- [Roadmap](./roadmap.md) - What's next

## Archived Plans

Historical plans have been archived with banners pointing here:
- `plans/morphio-io-final-cleanup-verification.md`
- `morphio-io/plans/extract-morphio-core-library.md`
- `morphio-io/plans/morphio-io-cleanup-phases-7-10.md`
