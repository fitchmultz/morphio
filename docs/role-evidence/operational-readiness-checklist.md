# Operational Readiness Checklist

## Configuration
- [ ] Root `/.env` created via `make env`.
- [ ] Production secrets are non-default/non-placeholder values.
- [ ] `DATABASE_URL` set to PostgreSQL in production.

## Logging and Health
- [ ] API health endpoints pass (`/health/`, `/health/db`, `/health/redis`).
- [ ] Docker smoke includes auth and API key CRUD checks.

## CI / Quality Gates
- [ ] `make ci-fast` passes.
- [ ] `make ci` passes.
- [ ] Fast gate jobs required in branch protection.
- [ ] Nightly full smoke enabled.

## Security
- [ ] Working-tree secret scan passes (`secrets-scan.sh --working-tree`).
- [ ] History scan passes before public release (`--history`).

## Rollout / Rollback Notes
- Roll forward with baseline gate success + smoke evidence.
- Roll back by reverting deployment artifact/tag and re-running smoke checks.
