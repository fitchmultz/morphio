# Morphio Configuration Guide

> **Source of Truth:** `morphio-io/backend/app/config.py`

This document defines the canonical configuration contract for the Morphio monorepo.

## Ports

| Service | Port | Notes |
|---------|------|-------|
| Backend API | 8000 | FastAPI server |
| Frontend Dev | 3005 | Next.js dev server (`pnpm dev`) |
| Frontend Docker | 3500 → 3000 | Published port maps to container port 3000 |
| PostgreSQL | 5432 | Production database |
| Redis | 6379 | Caching and job queues |

## Environment Variable Sources

| File | Purpose |
|------|---------|
| `morphio-io/backend/app/config.py` | **Canonical source** - all backend env vars |
| `morphio-io/backend/.env.example` | Backend local development |
| `morphio-io/frontend/.env.example` | Frontend local development |
| `morphio-io/stack.env.example` | Docker Compose stack |

## Required Variables by Service

### Backend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APP_ENV` | Yes | `production` | Environment: `development`, `production` |
| `SECRET_KEY` | **Prod** | `dev_secret_key` | Strong secret for sessions |
| `JWT_SECRET_KEY` | **Prod** | `dev_jwt_secret_key` | JWT signing key |
| `OPENAI_API_KEY` | Yes | - | OpenAI API key |
| `DATABASE_URL` | **Prod** | SQLite | PostgreSQL connection string |
| `REDIS_URL` | Yes | `redis://localhost:6379/0` | Redis connection URL |

**AI/LLM Keys:**
- `OPENAI_API_KEY` - Required
- `ANTHROPIC_API_KEY` - Optional
- `GEMINI_API_KEY` - Optional
- `HUGGING_FACE_TOKEN` - Required for diarization

**Model Configuration:**
- `AUDIO_TRANSCRIPTION_MODEL` - Default: `local`
- `WHISPER_MODEL` / `WHISPER_MLX_MODEL` - Default: `small`
- `TITLE_GENERATION_MODEL` - Default: `gemini-3-flash-preview-minimal`
- `CONTENT_MODEL` - Default: `gemini-3-flash-preview`

### Frontend

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_BASE_URL` | Yes | - | Backend API URL |
| `NEXT_PUBLIC_MAX_UPLOAD_SIZE` | No | 3221225472 | Max upload size (3GB) |
| `NEXT_PUBLIC_ALLOWED_AUDIO_EXTENSIONS` | No | - | Override allowed audio types |

### Redis

| Variable | Description |
|----------|-------------|
| `REDIS_URL` | Full URL with DB index: `redis://localhost:6379/0` |
| `REDIS_PASSWORD` | Password (optional in dev, recommended in prod) |

**URL Format:**
- Development: `redis://localhost:6379/0`
- Docker: `redis://redis:6379/0`
- Production with auth: `redis://:PASSWORD@redis:6379/0`

## Docker Compose Configuration

### Development (`docker-compose.yml`)

```yaml
backend:
  environment:
    - REDIS_URL=redis://redis:6379/0
  ports:
    - "8000:8000"

frontend:
  environment:
    - NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
  ports:
    - "3500:3000"

redis:
  image: redis:7.4-alpine
  ports:
    - "6379:6379"
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
CORS_ORIGINS=["http://localhost:3000","http://localhost:3005","https://morphio.io"]
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
