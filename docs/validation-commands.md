# Validation Commands

Use this checklist to validate the repository from a fresh clone and to reproduce CI-equivalent gates locally.

## 1) Fresh setup

```bash
make env
make install
bash scripts/install-git-hooks.sh
```

## 2) Fast PR-equivalent gate (required in GitHub PR CI)

```bash
make ci-fast
```

This runs:
- `scripts/ci/jobs/backend-checks.sh`
- `scripts/ci/jobs/frontend-checks.sh`
- `scripts/ci/jobs/guardrails.sh`

Target runtime: ≤10 minutes wall-clock on warm caches (per-job timeout ceiling: 15 minutes).

## 3) Full local release gate

```bash
make ci
```

This runs `scripts/ci/run.sh`:
1. doctor checks
2. native build
3. morphio-core checks
4. backend checks
5. frontend checks
6. OpenAPI drift check
7. Docker build
8. Docker smoke
9. guardrails

Expected runtime: ~15–35 minutes.

## 4) Heavy smoke validation (optional/nightly parity)

```bash
bash scripts/ci/jobs/docker-full-smoke.sh
```

Expected runtime: ~10–25 minutes.

## 5) Secret scanning (release readiness)

```bash
bash scripts/ci/jobs/secrets-scan.sh --history
```

## 6) Targeted inner-loop commands

```bash
bash scripts/ci/jobs/backend-checks.sh
bash scripts/ci/jobs/frontend-checks.sh
bash scripts/ci/jobs/guardrails.sh
```

Use these when iterating quickly before running full `make ci`.

## 7) Success criteria

Validation is complete when:
- `make ci-fast` passes with zero failures.
- `make ci` passes with zero failures.
- No uncommitted drift is introduced by generation/format checks.
