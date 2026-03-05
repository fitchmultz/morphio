# Release Runbook

This runbook covers staging, deployment, rollback, and verification.

## Staging
- Generate staging secrets, bring up the stack, and smoke test:
  - `make staging-secrets`
  - `make staging-up`
  - `make staging-smoke`
- Validate `/health`, `/health/db`, `/health/redis`, and `/admin/health`.
- Confirm OpenSearch Dashboards is reachable on port 5601.

## Deploy
- Run `make ci` from the repo root (full local release gate).
- Ensure the PR fast gate (`.github/workflows/ci-cd.yml`) is green.
- Build and push the release images locally (backend API, worker-ml, crawler, frontend) to GHCR.
- Capture the pushed image digests and generate a pinned `docker-compose.release.yml`.
- Create and push a release tag (e.g. `v1.2.3`), then publish a GitHub Release with the pinned compose + SBOMs attached.
- Apply the pinned `docker-compose.release.yml` for deterministic deploys.
- Record the tag + image digests for rollback.

## Rollback
- Re-deploy the previous pinned compose (or prior tag).
- Verify DB schema compatibility before rollback.
- Validate critical workflows post-rollback.

## Verification
- Check logs for error spikes, auth failures, and queue backlogs.
- Inspect Prometheus metrics for request rate/latency regressions.
- Confirm Stripe checkout + billing portal flows.
- Monitor Redis and database health.
