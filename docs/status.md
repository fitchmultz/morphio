# Morphio Project Status

> **Last Updated:** 2025-12-25

## Overview

Morphio is a monorepo containing three main projects:

| Project | Description | Status |
|---------|-------------|--------|
| **morphio-core** | Standalone library for audio/LLM/security utilities | Stable |
| **morphio-io** | Full-stack web application (FastAPI + Next.js) | Active Development |
| **morphio-native** | Native binaries and accelerators | Active Development |

## Current Versions & Ports

| Component | Version/Port |
|-----------|-------------|
| **Node.js** | ≥24.0.0 |
| **Next.js** | 16.1.1 |
| **Python** | ≥3.13 |
| **Backend API** | Port 8005 (dev), 8000 (prod) |
| **Frontend Dev** | Port 3005 |
| **Frontend Docker** | 3500 → 3000 |
| **Redis** | Host 6384 (container 6379) |

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

## Current Focus: Baseline Alignment ✅ Complete

Baseline alignment and wiring completed on 2025-12-25:

### Configuration + Wiring ✅
- [x] Align ports, versions, and env examples with backend config
- [x] Add admin export bearer auth + unified API base URL
- [x] Add API key management UI (create/revoke/list)
- [x] Align log upload limits with backend config + config endpoint

### Quality + Observability ✅
- [x] Add Prometheus request metrics middleware
- [x] Add backend tests for log config + upload size enforcement
- [x] Add frontend tests for API key flows

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

## Product Features (Phase 4) ✅ Complete

Completed on 2025-12-23:

### Admin Dashboard ✅
- [x] Export LLM usage reports (CSV) with date range filters
- [x] LLM usage summary by provider (requests, tokens, cost)

### User Billing ✅
- [x] Usage alerts when credits < 20% (warning) or < 5% (critical)
- [x] Stripe checkout integration for plan upgrades
- [x] Billing portal for subscription management

### Programmatic Access ✅
- [x] API key model with SHA256 hashing
- [x] API key CRUD endpoints (`POST/GET/DELETE /user/api-keys`)
- [x] Bearer token authentication for API keys

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
