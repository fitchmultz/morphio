# Morphio Configuration Guide

> **Source of Truth:** `morphio-io/backend/app/config.py`

This document defines the canonical configuration contract for the Morphio monorepo.

## Ports

| Service | Port | Notes |
|---------|------|-------|
| Backend API | 8005 | FastAPI server |
| Frontend Dev | 3005 | Next.js dev server (`pnpm dev`) |
| Frontend Docker | 3500 → 3005 | Published port maps to container port 3005 |
| PostgreSQL | 5432 | Production database |
| Redis | 6384 | Host and container port |

## Environment Variable Sources

| File | Purpose |
|------|---------|
| `morphio-io/backend/app/config.py` | **Canonical source** - all backend env vars |
| `.env.example` | Repo-root env template (committed) |
| `.env` | Repo-root env file for local dev and Docker (copy from `.env.example`) |

Only `/.env` and `/.env.example` are allowed in the repo.

## Required Variables by Service

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | Yes | `production` | Environment: `development`, `production` |
| `SECRET_KEY` | **Prod** | `dev_secret_key` | Strong secret for sessions |
| `JWT_SECRET_KEY` | **Prod** | `dev_jwt_secret_key` | JWT signing key |
| `OPENAI_API_KEY` | Optional | - | Required if using OpenAI models |
| `DATABASE_URL` | **Prod** | SQLite | PostgreSQL connection string |
| `REDIS_URL` | Yes | `redis://localhost:6384/0` | Redis connection URL |
| `REDIS_DB` | No | `0` | Redis database index |
| `FRONTEND_URL` | No | `http://localhost:3005` | Frontend origin for redirects |
| `PROMETHEUS_ENABLED` | No | `false` | Enable Prometheus metrics |
| `OPENSEARCH_ENDPOINT` | No | - | Vector OpenSearch endpoint (prod logging) |
| `OPENSEARCH_USER` | No | - | Vector OpenSearch username |
| `OPENSEARCH_PASSWORD` | No | - | Vector OpenSearch password |
| `USER_ROUTES_RATE_LIMIT` | No | `60` | Requests per window for user routes |
| `USER_ROUTES_RATE_WINDOW` | No | `60` | Rate limit window in seconds |
| `CSRF_COOKIE_EXPIRE_SECONDS` | No | `86400` | CSRF cookie lifetime in seconds |
| `STRIPE_PRO_PRICE_ID` | No | - | Stripe Pro price ID |
| `STRIPE_ENTERPRISE_PRICE_ID` | No | - | Stripe Enterprise price ID |
| `WORKER_ML_URL` | No | - | Optional ML worker URL |
| `CRAWLER_URL` | No | - | Optional crawler service URL |
| `SERVICE_TIMEOUT` | No | `60` | Upstream service timeout in seconds |

**AI/LLM Keys:**
- Provide at least one provider key that matches the model you configure.
- `OPENAI_API_KEY` - Required if using OpenAI models
- `ANTHROPIC_API_KEY` - Required if using Anthropic models
- `GEMINI_API_KEY` - Required if using Gemini models
- `HUGGING_FACE_TOKEN` - Required for diarization

**Model Configuration:**
- `AUDIO_TRANSCRIPTION_MODEL` - Default: `local`
- `WHISPER_MODEL` / `WHISPER_MLX_MODEL` - Default: `small`
- `TITLE_GENERATION_MODEL` - Default: `gemini-3-flash-preview-minimal`
- `CONTENT_MODEL` - Default: `gemini-3-flash-preview`
- `DIARIZATION_ENABLED` - Enable diarization
- `DIARIZATION_MODEL` - Default: `pyannote/speaker-diarization-3.1`
- `DIARIZATION_MIN_SPEAKERS` / `DIARIZATION_MAX_SPEAKERS` - Optional bounds
- `DIARIZATION_USE_SUBPROCESS` - Run diarization in a subprocess

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | - | Backend API URL |
| `NEXT_PUBLIC_MAX_UPLOAD_SIZE` | No | 3221225472 | Max upload size (3GB) |

### Redis

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Full URL with DB index: `redis://localhost:6384/0` |
| `REDIS_PASSWORD` | Password (optional in dev, recommended in prod) |

**URL Format:**
- Development: `redis://localhost:6384/0`
- Docker: `redis://redis:6384/0`
- Production with auth: `redis://:PASSWORD@redis:6384/0`

## Docker Compose Configuration

### Development (`docker-compose.yml`)

```yaml
backend:
  environment:
    - REDIS_URL=redis://redis:6384/0
  ports:
    - "8005:8005"

frontend:
  environment:
    - NEXT_PUBLIC_API_BASE_URL=http://localhost:8005
  ports:
    - "3500:3005"

redis:
  image: redis:7.4-alpine
  ports:
    - "6384:6384"
```

### Production (`docker-compose.prod.yml`)

Uses Docker secrets for sensitive values:
- `SECRET_KEY_FILE=/run/secrets/SECRET_KEY`
- `JWT_SECRET_KEY_FILE=/run/secrets/JWT_SECRET_KEY`
- `DATABASE_URL_FILE=/run/secrets/DATABASE_URL`
- `REDIS_URL_FILE=/run/secrets/REDIS_URL`

## Media Extensions

Backend expects separate extension arrays:

```env
# Correct format (JSON arrays)
ALLOWED_VIDEO_EXTENSIONS=["mp4","avi","mov","wmv","flv","mkv","webm","ogg","3gp","mpeg","mpg","m4v"]
ALLOWED_AUDIO_EXTENSIONS=["mp3","wav","m4a","aac","flac","wma","m4p"]
ALLOWED_LOG_EXTENSIONS=["csv","json","log","md","txt"]
```

**Do NOT use:**
- `ALLOWED_MEDIA_EXTENSIONS` (legacy, not supported)
- `REACT_APP_*` prefix (React.js, not Next.js)

## CORS Origins

```env
# JSON array format
CORS_ORIGINS=["http://localhost:3005","http://localhost:3500","https://morphio.io"]
```

## Usage & Subscription

```env
USAGE_WEIGHTS_JSON={"VIDEO_PROCESSING":2,"AUDIO_PROCESSING":1,"WEB_SCRAPING":1,"CONTENT_GENERATION":2,"LOG_PROCESSING":1,"OTHER":1}
SUBSCRIPTION_PLAN_LIMITS_JSON={"free":50,"pro":1000,"enterprise":999999999}
```

## Production Security Requirements

When `APP_ENV=production`:
1. `SECRET_KEY` must be strong, non-default
2. `JWT_SECRET_KEY` must be strong, non-default
3. `DATABASE_URL` must be PostgreSQL (not SQLite)

The backend **refuses to start** if these requirements are not met.

## Docker Secrets Support

For sensitive values, use `*_FILE` environment variables:

```env
SECRET_KEY_FILE=/run/secrets/SECRET_KEY
JWT_SECRET_KEY_FILE=/run/secrets/JWT_SECRET_KEY
OPENAI_API_KEY_FILE=/run/secrets/OPENAI_API_KEY
DATABASE_URL_FILE=/run/secrets/DATABASE_URL
```

Or mount secrets directly to `/run/secrets/<NAME>`.
