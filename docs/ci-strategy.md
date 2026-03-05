# CI Strategy

This repository uses a two-tier CI model to keep PR feedback fast while preserving deeper coverage through scheduled/manual heavy checks.

## PR Required Gate (Fast)

Workflow: `.github/workflows/ci-cd.yml` (`CI • Fast PR Gate`)

Runs on:
- `pull_request` to `main`
- `push` to `main`
- `workflow_dispatch`

Checks (parallel jobs):
- `scripts/ci/jobs/backend-checks.sh`
- `scripts/ci/jobs/frontend-checks.sh`
- `scripts/ci/jobs/guardrails.sh` (includes working-tree secrets scan)

Design goals:
- deterministic and non-interactive
- no external secret dependency
- bounded wall-clock runtime via parallel jobs
- cancel-in-progress enabled to reduce runner waste

Runtime budget:
- target warm-cache wall time: ≤10 minutes
- configured timeout per job: 15 minutes (fail-fast ceiling)

## Heavy Coverage (Nightly / Manual)

Workflow: `.github/workflows/docker-full-smoke.yml` (`Docker • Full Stack Smoke`)

Runs on:
- nightly schedule (`30 6 * * *`)
- `workflow_dispatch`

Checks:
- `scripts/ci/jobs/docker-full-smoke.sh` (full compose stack smoke)

Expected runtime: ~10–25 minutes.

## Local Release Gate

Command: `make ci`

Runs full `scripts/ci/run.sh` sequence:
- doctor
- native build
- morphio-core checks
- backend checks
- frontend checks
- OpenAPI drift
- Docker build
- Docker smoke
- guardrails

Expected runtime: ~15–35 minutes.

## Resource Controls

- Fast gate uses three focused jobs (backend/frontend/guardrails) to reduce wall time.
- Workflow concurrency cancels stale runs on the same branch.
- Heavy full-stack smoke is shifted out of PR gating to nightly/manual.
- Guardrails include secrets scanning via `scripts/ci/jobs/secrets-scan.sh`.
