# Routes Documentation

## Overview

API routes are organized by domain in `app/routes/`. OpenAPI docs are available at `/docs` when running.

## Route Modules

| Module | Prefix | Description |
|--------|--------|-------------|
| `auth/` | `/auth` | Login, registration, token refresh |
| `content/` | `/content` | Content CRUD, comments, conversations |
| `media.py` | `/media` | Video/audio processing + status |
| `logs.py` | `/logs` | Log file processing + status |
| `web.py` | `/web` | Web scraping + status |
| `user.py` | `/user` | Profile, password change, usage limits |
| `admin.py` | `/admin` | Usage stats, user management |
| `template.py` | `/template` | Template CRUD |
| `health.py` | `/health` | Health checks |
| `upload.py` | `/upload` | File upload handling |
| `docs.py` | `/` | OpenAPI redirect |

## Key Endpoints

### Status Polling

| Endpoint | Description |
|----------|-------------|
| `GET /media/status/{job_id}` | Video/audio processing status |
| `GET /logs/status/{job_id}` | Log processing status |
| `GET /web/status/{job_id}` | Web scraping status |

Status responses include:
- `status`: pending, processing, completed, failed
- `progress`: 0-100
- `stage`: QUEUED, DOWNLOADING, TRANSCRIBING, etc.
- `message`: Human-readable status message
- `result`: Completed content (when done)
- `error`: Error message (when failed)

### Authentication

| Endpoint | Description |
|----------|-------------|
| `POST /auth/login` | Login, returns access + refresh tokens |
| `POST /auth/register` | User registration |
| `POST /auth/token/refresh` | Refresh access token |
| `POST /auth/logout` | Logout, blacklists tokens |

### Content

| Endpoint | Description |
|----------|-------------|
| `GET /content/` | List user's saved content |
| `POST /content/{id}/comment` | Add comment to content |
| `POST /content/{id}/conversation/send` | Chat about content |

## Rate Limiting

Endpoints are rate-limited via `@rate_limit` decorator:
- Auth endpoints: 30-60/minute
- CRUD endpoints: 60-100/minute
- Status endpoints: 150-200/minute

## Related Files

- `app/routes/` - Route modules
- `app/schemas/` - Request/response schemas
- OpenAPI spec: `GET /openapi.json`
