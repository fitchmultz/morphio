# Smoke Test Checklist

Use this checklist after local changes or before release candidates.

## Services

- Start dev: `make dev` (native) or `docker compose -f morphio-io/docker-compose.watch.yml up -d --build`
- Backend health: `curl -fsS http://localhost:8005/health/`
- Database health: `curl -fsS http://localhost:8005/health/db`
- Redis health: `curl -fsS http://localhost:8005/health/redis`
- Frontend health: `curl -fsS http://localhost:3005/api/health`

## Metrics (optional)

- Set `PROMETHEUS_ENABLED=true`, restart backend, then:
  - `curl -fsS http://localhost:8005/metrics | rg "http_requests_total|http_request_duration_seconds"`

## Representative Workflow

- Register/login
- Profile: credits visible
- Create API key (copy once), then revoke it
- Admin export CSV
- Upload a small log file succeeds
- Upload a log file larger than configured max returns 413
