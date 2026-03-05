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

## Evidence (What Was Verified)

- Code-level regression tests added for production secret guards.
- CI gate scripts updated to enforce secrets scan in guardrails.
- Fast gate workflow split and timeout constraints applied in code.
- Compose default path validated structurally through preflight integration in guardrails.

### Verification receipts (2026-03-05)

- `make install` ✅ passed (baseline install completed; heavy ML stack packages removed from default env).
- `make ci-fast` ✅ passed (backend/frontend/guardrails + working-tree secret scan).
- `bash scripts/ci/jobs/secrets-scan.sh --history` ✅ passed (`96 commits scanned`, `no leaks found`).
- `make ci` ⚠️ all substantive stages passed; final `git diff --exit-code` cleanliness check failed because the working tree already contains unrelated pre-existing modifications in this branch context.

## Remaining Risks / Follow-ups

1. **History-wide secret scan still required before public flip**
   - Run: `bash scripts/ci/jobs/secrets-scan.sh --history`
   - If findings exist, rotate and rewrite history before public release.

2. **CI runtime target needs observation on hosted runners**
   - Collect 3–5 run samples for `CI • Fast PR Gate` and confirm warm-cache ≤10 minutes.

3. **Branch protection must require all fast-gate jobs**
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
