# Deployment Documentation

## Overview

The backend can be deployed via Docker Compose (recommended) or directly.

## Docker Compose

### Development

```bash
cd morphio-io
cp stack.env.example stack.env
# Edit stack.env with your API keys

docker compose up -d --build
```

Access:
- Backend: http://localhost:8000
- Frontend: http://localhost:3500

### Production

```bash
# Prepare secrets
mkdir -p secrets
openssl rand -base64 48 > secrets/SECRET_KEY
openssl rand -base64 48 > secrets/JWT_SECRET_KEY
echo "postgresql+asyncpg://user:pass@postgres:5432/morphio" > secrets/DATABASE_URL

# Start stack
docker compose -f docker-compose.prod.yml up -d --build
```

Production compose uses Docker secrets for sensitive values.

## Environment Requirements

### Required in Production

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Strong, non-default value |
| `JWT_SECRET_KEY` | Strong, non-default value |
| `DATABASE_URL` | PostgreSQL connection string |

The backend **refuses to start** if these aren't properly configured.

### Recommended

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Redis connection with password |
| `OPENAI_API_KEY` | At least one LLM provider |

## Port Configuration

| Service | Port | Description |
|---------|------|-------------|
| Backend | 8000 | FastAPI API |
| Frontend | 3500 → 3000 | Next.js (Docker published → container) |
| Redis | 6379 | Cache and job queue |
| PostgreSQL | 5432 | Database |

## Health Checks

| Endpoint | Description |
|----------|-------------|
| `GET /health/` | Basic health check |
| `GET /health/db` | Database connectivity |
| `GET /health/redis` | Redis connectivity |

## Database Migrations

```bash
# Run migrations
cd morphio-io/backend
uv run alembic upgrade head

# Create new migration
uv run alembic revision --autogenerate -m "description"
```

## Scaling Considerations

- Backend is stateless; scale horizontally
- Redis is shared state for job status
- PostgreSQL handles persistence
- Worker services (worker-ml, crawler) can scale independently

## Related Files

- `docker-compose.yml` - Development stack
- `docker-compose.prod.yml` - Production stack
- `Dockerfile.api` - Backend image
- `alembic.ini` - Migration config