# Release Readiness Report

Date: 2026-03-05

## Current State (Phase 0)

- **Stack:** Python 3.13+, FastAPI backend, Next.js frontend, Rust/PyO3 native extension, Docker Compose.
- **Entrypoints:** root `Makefile`, `scripts/ci/run.sh`, `scripts/ci/jobs/*`, `.github/workflows/*`.
- **Primary flows:**
  1. local bootstrap (`make env`, `make install`, `make dev`)
  2. PR gate (`make ci-fast` / `CI • Fast PR Gate`)
  3. full release parity (`make ci`)
- **Main risks reviewed:** install footprint, CI runtime determinism, secret hygiene, docs/ADR drift, compose cold-start behavior.

## Changes Implemented in This Takeover Pass

### P0 fixes

1. **Default install is now safe and predictable**
   - `make install` now uses baseline dependencies only.
   - Added explicit heavy opt-in targets: `make install-full`, `make install-ml`, `make install-ml-apple`.
   - Root `pyproject.toml` no longer forces `morphio-core[whisper-mlx]` by default.

2. **Production secret enforcement hardened**
   - Backend config now rejects placeholder/sentinel secret values in production:
     - `__GENERATE_SECURE_VALUE__`
     - `__CHANGE_ME__`
     - default `dev_*` values
   - Added regression tests in `morphio-io/backend/tests/unit/test_config_production_secrets.py`.

3. **Fast PR gate architecture tightened**
   - `.github/workflows/ci-cd.yml` moved to three focused parallel jobs:
     - backend
     - frontend
     - guardrails
   - Removed unnecessary Rust/apt setup from fast gate.
   - Per-job timeout tightened to 15 minutes.

4. **Secret scanning guardrail added to CI/local gate**
   - Added `scripts/ci/jobs/secrets-scan.sh` (gitleaks-based).
   - Added `.gitleaks.toml` with constrained allowlist.
   - Guardrails now enforce working-tree secret scan.

5. **Cold-start Docker compose reliability improved**
   - `morphio-io/docker-compose.yml` frontend now builds locally instead of requiring GHCR image auth.

6. **Documentation/ADR contract consistency improved**
   - ADR 0003 marked superseded by ADR 0006.
   - Updated onboarding/CI/validation docs to reflect new install model and gate behavior.

### P1 hardening

7. **Updater workflow token scope reduced**
   - `.github/workflows/updater.yml` now uses `github.token` with explicit minimal permissions.

8. **Final public polish pass**
   - Stripe webhook ingress now rejects missing `Stripe-Signature` before Stripe verification runs.
   - Added route-level regression coverage in `morphio-io/backend/tests/integration/test_billing_webhook.py`.
   - Removed direct browser console logging from conversation refresh failures.
   - Updated OpenAPI generator config to `postProcess: ["biome:format"]` to remove the deprecated config warning while keeping generated output aligned with repository formatting.
   - Updated secret scanning to prefer a local `gitleaks` binary, fall back to Docker only when available, and otherwise auto-download the pinned release via `gh`.
   - Tightened the root Docker build context ignore rules so local uploads, logs, and media artifacts cannot break Docker smoke builds.

## Evidence (What Was Verified)

- Code-level regression tests added for production secret guards.
- CI gate scripts updated to enforce secrets scan in guardrails.
- Fast gate workflow split and timeout constraints applied in code.
- Compose default path validated structurally through preflight integration in guardrails.

### Verification receipts (2026-03-05 final cutoff)

- `make update` ✅ completed; Python/Node lock resolution reported no newer direct stable versions to apply.
- Latest-stable registry checks ✅ completed for Python/Node/Rust direct tooling/dependencies (e.g., `ty`, `ruff`, `fastapi`, `next`, `react`, `@biomejs/biome`, `pyo3`).
- `make ci-fast` ✅ passed (backend/frontend/guardrails + working-tree secret scan).
- `make ci` ✅ passed end-to-end (native/core/backend/frontend/openapi/docker-build/docker-smoke/guardrails).
- `bash scripts/ci/jobs/secrets-scan.sh --history` ✅ passed (`100 commits scanned`, `no leaks found`).
- Runtime UI smoke ✅ passed on `http://localhost:3005` (`/`, `/login`, invalid-login error feedback, `/dashboard` redirect behavior) via live browser validation.
- Targeted regression checks ✅ passed for Stripe webhook request validation and frontend client regeneration/type-check after the final polish pass.

## Remaining Risks / Follow-ups

1. **CI runtime target should continue to be monitored on hosted runners**
   - Collect periodic warm-cache samples for `CI • Fast PR Gate` and keep target ≤10 minutes.

2. **Branch protection should require all fast-gate jobs**
   - Require backend, frontend, and guardrails checks for merge.

## Local Reproduction Commands

```bash
make env
make install
make ci-fast
make ci
```

Heavy and release checks:

```bash
bash scripts/ci/jobs/docker-full-smoke.sh
bash scripts/ci/jobs/secrets-scan.sh --history
```

## CI Matrix Summary

- **PR required:** `.github/workflows/ci-cd.yml` (backend + frontend + guardrails/secrets scan)
- **Nightly/manual heavy:** `.github/workflows/docker-full-smoke.yml`
- **Local release parity:** `make ci` (full script pipeline)
