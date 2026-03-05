# Demo Script (5–10 Minutes)

1. `make env && make install`
   - Show generated local secrets and baseline install path.
2. `make ci-fast`
   - Demonstrate backend/frontend/guardrails passing quickly.
3. Open `.github/workflows/ci-cd.yml`
   - Show parallel fast-gate jobs and timeout ceilings.
4. Open `morphio-io/backend/tests/unit/test_config_production_secrets.py`
   - Show concrete regression protection for production secrets.
5. `bash scripts/ci/jobs/secrets-scan.sh --working-tree`
   - Show secret guardrail execution path.
6. Open `morphio-io/docker-compose.yml`
   - Show frontend local build (no GHCR auth dependency for default path).

Troubleshooting:
- If Docker unavailable, start daemon and rerun guardrails/ci.
- If Python 3.13 missing, run `uv python install 3.13`.
