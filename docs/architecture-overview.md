# Architecture Overview

This document is a concise reviewer-oriented summary of the Morphio monorepo architecture.

## System Goals

- Keep reusable media/LLM/security logic independent from web transport concerns.
- Preserve strict boundaries so provider SDK churn does not leak into application layers.
- Support production-oriented operations with deterministic local and CI gates.

## Monorepo Components

### 1) `morphio-core` (Python library)

Reusable domain logic and provider integrations:
- `audio/` – transcription/chunking/alignment
- `llm/` – provider router and generation contracts
- `security/` – URL validation, anonymization, SSRF protections
- `video/` and `media/` – downloader/media helpers

### 2) `morphio-io` (application)

Full-stack operator-facing product:
- `backend/` – FastAPI API, persistence, orchestration
- `frontend/` – Next.js operator UI
- `backend/app/adapters/` – boundary layer that wraps `morphio-core`

### 3) `morphio-native` (Rust extension)

Performance-sensitive primitives exposed to Python via PyO3.

## Control and Data Flow

Primary request path:

1. Frontend submits request to backend route.
2. Backend route calls service layer.
3. Service delegates heavy media/LLM/security work to adapter.
4. Adapter calls `morphio-core` and translates library exceptions into application exceptions.
5. Service persists results and returns response to route/front-end.

Operational flow:

- Local full gate: `make ci` → `scripts/ci/run.sh` (doctor, native build, core checks, backend checks, frontend checks, OpenAPI drift, Docker build/smoke, guardrails).
- PR fast gate: `.github/workflows/ci-cd.yml` (backend checks + frontend checks + guardrails).
- Heavy smoke gate: `.github/workflows/docker-full-smoke.yml` (nightly + manual).

## Architectural Guardrails

- Provider SDK imports are restricted to `morphio-core` (`scripts/audit_imports.sh`).
- `morphio-core` calls in `morphio-io` are restricted to adapter boundary (`scripts/audit_morphio_core_boundary.sh`).
- Environment contract is validated against backend config (`morphio-io/scripts/audit_env_template.py`).
- Env layout guardrail enforces only root `/.env` and `/.env.example` (`scripts/audit_env_layout.sh`).

## Key Decisions and Trade-offs

### Adapter boundary between app and library

**Decision:** keep HTTP/application concerns in `morphio-io`, reusable domain logic in `morphio-core`.

**Trade-off:** adds one indirection layer, but greatly improves reuse, testability, and blast-radius control.

### Full local gate plus fast PR gate

**Decision:** keep `make ci` as full local release gate while running a fast deterministic GitHub PR gate for visibility.

**Trade-off:** two gate tiers to maintain, but substantially lower PR latency and better reviewer trust.

### Rust extension as hard dependency for performance paths

**Decision:** retain `morphio-native` as first-class workspace member.

**Trade-off:** higher toolchain complexity, but stable performance characteristics and explicit build verification.

## Reliability and Production Readiness Hooks

- Deterministic check scripts under `scripts/ci/jobs/`.
- Docker compose smoke validation for integration confidence.
- Security-oriented configuration checks (production key requirements, secrets-file support).
- Auditable docs and ADR history under `docs/`.
