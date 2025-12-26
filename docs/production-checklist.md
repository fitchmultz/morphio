# Production Checklist

Use this checklist before promoting a release to production.

## Frontend (Next.js)
- Run `pnpm build` and address warnings or chunk size regressions.
- Validate caching + dynamic rendering behavior for critical routes.
- Verify `NEXT_PUBLIC_API_BASE_URL` and other public env vars are set correctly.
- Confirm image domains/remote patterns match production assets.
- Smoke test key pages: login, dashboard, logs, profile, admin.

## Backend (FastAPI)
- Set `APP_ENV=production` with strong `SECRET_KEY` and `JWT_SECRET_KEY`.
- Verify `DATABASE_URL` points to PostgreSQL and migrations are applied.
- Confirm Redis connectivity, `REDIS_URL`, and rate-limit settings.
- Configure `UVICORN_WORKERS`, `LOG_LEVEL`, and `SERVICE_TIMEOUT`.
- Check `FRONTEND_URL`, `CORS_ORIGINS`, and CSRF settings.

## Infrastructure
- Ensure `/health` and `/metrics` endpoints respond as expected.
- Confirm Prometheus scraping if `PROMETHEUS_ENABLED=true`.
- Verify log aggregation (Vector) and storage retention.
- Validate backup/restore for Postgres and any persistent volumes.

## Security
- Enforce HTTPS at the edge and secure cookies.
- Rotate secrets and verify no defaults remain in production.
- Verify auth flows and API key creation/revocation in UI.
- Confirm rate limiting is enabled for user routes.
