# Morphio.io Backend

## Admin User Setup

The application will automatically create an admin user if:

1. No admin user already exists in the database
2. The `ADMIN_PASSWORD` environment variable is set

To set up an admin user during development:

```bash
# Development
ADMIN_PASSWORD="your-secure-password" uvicorn app.main:app --reload
```

You can also customize the admin email and name:

```bash
ADMIN_EMAIL="youremail@example.com" ADMIN_NAME="Your Name" ADMIN_PASSWORD="secure-password" uvicorn app.main:app
```

For production deployment, set these environment variables in your deployment configuration or Docker environment.

## Default Admin Credentials

If not specified:

- Default email: `admin@morphio.io`
- Default name: `Administrator`

Note: There is no default password. You must set the `ADMIN_PASSWORD` environment variable.

## Docker Deployment

For Docker deployment, either:

1. Set the environment variables in your docker-compose file:

   ```yaml
   services:
     backend:
       environment:
         - ADMIN_EMAIL=admin@morphio.io
         - ADMIN_PASSWORD=your-secure-password
         - ADMIN_NAME=Administrator
   ```

2. Or pass them when running the container:
   ```bash
   docker run -e ADMIN_PASSWORD="your-secure-password" -e ADMIN_EMAIL="admin@yourdomain.com" your-image-name
   ```

## Secrets

- In production (`APP_ENV=production`), the API refuses to start if `SECRET_KEY` or `JWT_SECRET_KEY` are unset or left at dev defaults. Set strong values via env or Docker secrets.
- Docker secrets are supported via `*_FILE` variables (e.g., `SECRET_KEY_FILE=/run/secrets/SECRET_KEY`). See the root README for an example compose snippet.

## Database (Prod vs Dev)

- Development: Defaults to SQLite at `./db/morphio_io.db` for convenience.
- Production: Requires PostgreSQL. Set `DATABASE_URL` to a Postgres async DSN (e.g.,
  `postgresql+asyncpg://user:pass@host:5432/dbname`). The app refuses to start with SQLite in production.

## Docker Best Practices

- Single apt transaction: `apt-get update` and `apt-get install` occur in the same `RUN` layer; caches are purged with `rm -rf /var/lib/apt/lists/*`.
- Minimal packages: Only runtime libs for Chromium (Playwright) and `ffmpeg` are installed in the final image.
- No Rust toolchain in final image: Rust is not installed; wheels from PyPI are used to avoid native builds.
- Reproducible deps: Python deps are resolved from `uv.lock` using `uv sync --frozen`.
- Healthcheck: Image declares a `HEALTHCHECK` against `/health/` for orchestration.
- For stricter reproducibility in your fork:
  - Pin base image by digest (e.g., `FROM python:3.14-slim@sha256:<digest>`).
  - Consider pinning apt versions to your Debian snapshot mirror.
  - Keep `UV_FROZEN=1` in CI to forbid drift from the lockfile.

## Uvicorn performance

- Install `uvloop` and `httptools` for better throughput/latency. Already included in `pyproject.toml`.
- Uvicorn auto-detects these; no config needed. Workers are controlled via `UVICORN_WORKERS` (default 4 in Dockerfile).

## CSRF & Rate Limiting

- CSRF scope: Enabled only in production and only for cookie-backed flows (e.g., refresh token endpoint). Token-based APIs using `Authorization: Bearer` are not subject to CSRF checks.
- To refresh tokens from a browser, call `POST /auth/csrf-token` to obtain a CSRF token (cookie + response body) and send it in `X-CSRF-Token` when calling `POST /auth/refresh-token`.
- Rate limiting: Per-route limits via SlowAPI with Redis storage (see `utils/decorators.rate_limit`). Sensitive routes (login, register, refresh) are limited; configure `REDIS_URL` accordingly.

## API Docs

- Built-in FastAPI docs are enabled at `/api/docs` (Swagger UI) and OpenAPI schema at `/openapi.json`.

## Observability

- JSON logs: All app and Uvicorn logs are emitted as single-line JSON with fields `timestamp`, `level`, `logger`, `message`, and `correlation_id`. Uvicorn access logs also include `client_addr`, `request_line`, and `status_code`.
- Correlation IDs: Middleware accepts incoming `X-Correlation-ID` or `X-Request-ID`; otherwise generates one. The ID is added to `request.state`, propagated to logs, and returned in the `X-Correlation-ID` response header.
- Frontend propagation: The frontend sends a fresh `X-Correlation-ID` for each API call to aid cross-tier tracing.

### Reverse Proxy

- `nginx-backend.conf` forwards `X-Correlation-ID` to the API, returns it to clients, and logs access in JSON (`json_elk` format) with the correlation_id.

### Shipping to OpenSearch/ELK

- A Vector agent is included in `docker-compose.prod.yml` to tail Docker logs and ship to OpenSearch.
- Configure:
  - `OPENSEARCH_ENDPOINT=https://opensearch.example.com:9200`
  - `OPENSEARCH_USER`, `OPENSEARCH_PASSWORD`
- Index pattern: `morphio-*` with fields from our JSON logs.

Dashboards
- Filter by `correlation_id` to trace a request across services.
- Useful fields: `logger`, `status_code`, `request`, `request_time`, `upstream_time`, `user_id`.

## Development Setup
1. Install dependencies with uv (includes dev tools):

```bash
cd backend
uv sync --dev
```

2. Run the API locally:

```bash
uv run uvicorn app.main:app --reload --port 8005
```

3. Lint and type-check:

```bash
uv run ruff check .
uv run ty check
```

4. Tests:

```bash
uv run pytest -q
```
-
## Services Split

- Images:
  - API (`backend/Dockerfile.api`): FastAPI app only; no Playwright/Torch/Whisper.
  - ML Worker (`backend/Dockerfile.worker-ml`): Whisper/Torch + ffmpeg; exposes `:8001`.
  - Crawler (`backend/Dockerfile.crawler`): Playwright Chromium runtime; exposes `:8002`.
- Compose wires API → Worker via `WORKER_ML_URL` and API → Crawler via `CRAWLER_URL`.
- Endpoints used by API (internal):
  - Worker: `POST /transcribe` (multipart: file)
  - Crawler: `POST /render` (JSON: { url })
## Performance Testing

### k6 baseline

- Script: `perf/k6/api-baseline.js`
- Run locally (API at http://localhost:8005):

```bash
docker run --rm -it \
  -e BASE_URL=http://host.docker.internal:8005 \
  -e VUS=50 -e DURATION=5m \
  -v "$PWD":/work -w /work grafana/k6:0.48.0 \
  run perf/k6/api-baseline.js
```

Metrics to watch: `http_reqs`, `http_req_duration{p(95)}`, error rate.

### Locust (user-centric)

- File: `perf/locust/locustfile.py`
- Run via Docker:

```bash
docker run --rm -it -p 8089:8089 \
  -v "$PWD/perf/locust":/mnt/locust \
  --add-host host.docker.internal:host-gateway \
  -e LOCUST_HOST=http://host.docker.internal:8005 \
  locustio/locust:2.32.2 -f /mnt/locust/locustfile.py
```

### Tuning

- Compare monolith vs split:
  - Monolith: build `backend/Dockerfile` and run alone.
  - Split: `docker compose -f docker-compose.prod.yml up -d --build`.
- Vary `UVICORN_WORKERS` (e.g., 2, 4, 8) and record RPS and p95 latency under the same load.
- Expect improved cold start and lower memory on API-only; peak throughput is shaped by DB/Redis and worker latency.
