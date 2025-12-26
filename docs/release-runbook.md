# Release Runbook

This runbook covers staging, deployment, rollback, and verification.

## Staging
- Sync `.env`/secrets for staging.
- Deploy with `docker-compose.prod.yml` (or the pinned release compose).
- Run smoke tests: login, content generation, log upload, billing.
- Validate `/health` and `/metrics` endpoints.

## Deploy
- Create and push a release tag (e.g. `v1.2.3`).
- Pull the tagged images from GHCR.
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
