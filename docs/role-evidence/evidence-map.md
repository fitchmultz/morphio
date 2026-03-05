# Evidence Map

## Production workflow design
- Two-tier CI model documented and enforced (`docs/ci-strategy.md`, `.github/workflows/ci-cd.yml`, `.github/workflows/docker-full-smoke.yml`).
- Full local parity gate centralized at `make ci` (`scripts/ci/run.sh`).

## Reliability and correctness
- Regression tests for production secret policy (`test_config_production_secrets.py`).
- Deterministic fast checks via pinned sync/install (`--frozen`, `pnpm --frozen-lockfile`).

## Safety and security
- Guardrails include env layout audit, adapter boundaries, and secret scanning (`guardrails.sh`, `secrets-scan.sh`, `.gitleaks.toml`).
- Production config rejects default/placeholder signing secrets.

## Developer productivity
- Baseline install path reduced to safe defaults (`make install`).
- Heavy surfaces moved to explicit opt-in targets (`make install-full`, `make install-ml*`).
- Reviewer checklist added for rapid skepticism-driven validation.
