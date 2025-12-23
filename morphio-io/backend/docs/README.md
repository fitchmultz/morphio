# Morphio Backend Documentation

FastAPI backend for the Morphio content generation platform.

## Quick Links

- **[Configuration](./app-docs/config-docs.md)** - Environment variables and settings
- **[Routes](./app-docs/routes-docs.md)** - API endpoints and route modules
- **[Models](./app-docs/models-docs.md)** - Database models and relationships
- **[Schemas](./app-docs/schemas-docs.md)** - Pydantic schemas for request/response
- **[Authentication](./app-docs/auth-docs.md)** - JWT, CSRF, and security
- **[Utilities](./app-docs/utils-docs.md)** - Helper functions and enums
- **[Deployment](./deployment-docs.md)** - Docker and production setup
- **[Testing](./test-docs/testing-docs.md)** - Test structure and commands

## Architecture

```
backend/
├── app/
│   ├── adapters/       # morphio-core wrappers (SDK boundary)
│   ├── middlewares/    # Security, CSRF, rate limiting
│   ├── models/         # SQLAlchemy models
│   ├── routes/         # API endpoints
│   ├── schemas/        # Pydantic schemas
│   ├── services/       # Business logic
│   ├── utils/          # Helpers, enums, decorators
│   ├── config.py       # Settings (source of truth)
│   └── main.py         # FastAPI app entry point
├── db/                 # Alembic migrations
├── templates/          # Content generation templates
└── tests/              # Test suite
```

## Key Concepts

### Adapter Boundary

Provider SDKs (OpenAI, Anthropic, Gemini) are accessed through `morphio-core` via adapters in `app/adapters/`. Direct SDK imports in `app/` are forbidden. See `docs/architecture.md` in the monorepo root.

### Job Status Pipeline

1. Processing services call `update_job_status()` with stage info
2. Status is cached in Redis with TTL
3. Frontend polls status endpoints (`/media/status/{job_id}`, etc.)
4. Stages: QUEUED → DOWNLOADING → CHUNKING → TRANSCRIBING → DIARIZING → GENERATING → SAVING

### Usage Tracking

- `app/models/usage.py` - Usage and LLMUsageRecord models
- `app/services/usage/tracking.py` - `increment_usage()`, `check_usage_limit()`
- Gating happens before expensive operations (fail-fast)
