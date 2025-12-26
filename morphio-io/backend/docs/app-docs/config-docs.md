# Configuration Documentation

> **Source of Truth:** `app/config.py`

## Overview

Backend configuration is managed via Pydantic Settings, supporting environment variables and Docker secrets.

## Key Settings

### Application

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_ENV` | `production` | Environment mode |
| `DEBUG` | `False` | Debug mode |
| `LOG_LEVEL` | `INFO` | Logging level |
| `APP_PORT` | `8005` | Server port |

### Security

| Variable | Default | Description |
|----------|---------|-------------|
| `SECRET_KEY` | `dev_secret_key` | Session secret (must change in prod) |
| `JWT_SECRET_KEY` | `dev_jwt_secret_key` | JWT signing key (must change in prod) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

### AI/LLM

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | Required |
| `ANTHROPIC_API_KEY` | - | Optional |
| `GEMINI_API_KEY` | - | Optional |
| `HUGGING_FACE_TOKEN` | - | Required for diarization |

### Database

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | SQLite | Full connection string |
| `DB_DIALECT` | `sqlite` | `sqlite` or `postgres` |

## Docker Secrets

Sensitive values can be provided via `*_FILE` env vars:

```bash
SECRET_KEY_FILE=/run/secrets/SECRET_KEY
```

Supported: `SECRET_KEY`, `JWT_SECRET_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `DATABASE_URL`, `REDIS_URL`, `REDIS_PASSWORD`, `DB_PASSWORD`

## Production Requirements

When `APP_ENV=production`:
1. `SECRET_KEY` must be non-default
2. `JWT_SECRET_KEY` must be non-default
3. `DATABASE_URL` must be PostgreSQL

The app **refuses to start** if these aren't met.

## Related Files

- `app/config.py` - Settings class definition
- `.env.example` - Local development template
- `../stack.env.example` - Docker Compose template
