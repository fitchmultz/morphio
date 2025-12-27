# Release Runbook

This runbook covers staging, deployment, rollback, and verification.

## Staging
- Sync `.env`/secrets for staging.
- Deploy with `docker-compose.prod.yml` (or the pinned release compose).
- Run smoke tests: login, content generation, log upload, billing.
- Validate `/health` and `/metrics` endpoints.

## Deploy
- Run `make ci` from the repo root (local CI is the release gate; Actions are disabled).
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
