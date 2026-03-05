# Repository Guidelines

## Workspace Setup

This project is part of the `morphio-all` monorepo using **uv workspaces**. The Python `.venv` lives at the monorepo root.

```bash
# From monorepo root (recommended)
make install    # Install baseline deps (safe defaults)
make install-full  # Optional heavy dependency groups/extras
make dev        # Start backend + frontend
make ci         # Full CI gate (required for PRs)
```

## Project Structure & Module Organization
- `backend/` – FastAPI app (`app/{routes,services,models,schemas,utils}`), Alembic in `db/`.
- `frontend/` – Next.js 16.1.1 app (`src/app`, `src/components`, `src/utils`).
- `docs/` – project docs; `log_files/`, `uploads/` for local data.
- Env example: `.env.example` at the repo root.

## Makefile Commands (Preferred)

**IMPORTANT**: Use Makefile commands from the project root. Always run `make ci` before commits.

- `make ci` - **Required before commits**: type-check, lint, build, and test everything
- `make test` - Run all tests (backend + frontend)
- `make lint` - Lint everything
- `make format` - Format all code
- `make type-check` - Type check everything
- `make dev` - Start backend + frontend natively (Redis via Docker)
- `make dev-full` - Start ALL services natively (Apple Silicon)
- `make dev-docker` - Start all services in Docker with hot reload
- `make help` - Show all available commands

## Build, Test, and Development Commands

- **Backend (Python 3.13+)**:
  - Tests: `uv run pytest -q` (coverage: `uv run pytest --cov=app`)
  - Lint: `uv run ruff check .`
  - Format: `uv run ruff format .`
  - Type check: `uv run ty check`
  - Run API: `source ../.env && uv run uvicorn app.main:app --reload --port 8005`

- **Frontend (Node >= 24, pnpm)**:
  - Setup: `corepack enable && pnpm install`
  - Dev server: `pnpm dev` (http://localhost:3005)
  - Build: `pnpm build`
  - Tests: `pnpm test`
  - Lint/format: `pnpm lint` / `pnpm format`

## Development Ports

- **Frontend**: Port 3005 (http://localhost:3005)
- **Backend API**: Port 8005 (http://localhost:8005)
- **Redis**: Port 6384 (localhost:6384)

## Coding Style & Naming Conventions

- **Rate-limited FastAPI routes**: Any endpoint using `@rate_limit(...)` must include `request: Request` in the function signature so decorator enforcement has request context.

- **Python**: Ruff for lint/format; ty for type-check. Line length 100, Python 3.13+.
  - snake_case modules/functions, PascalCase classes; include type hints.
  - Run: `uv run ruff check . && uv run ty check` (from `backend/`).

- **TypeScript/React**: Biome for lint/format.
  - PascalCase components, camelCase variables/hooks; co-locate component files in `src/components`.
  - Run: `pnpm lint` and `pnpm format`.
  - OpenAPI client generation is source-of-truth driven by `frontend/openapi-ts.config.ts`; generated `src/client/**` output must stay Biome-formatted and should never be hand-edited.

## Testing Guidelines

- **Backend**: Pytest with asyncio; tests in `backend/tests/{unit,integration,e2e}` named `test_*.py`.
- **Frontend**: Vitest + Testing Library. Tests in `__tests__` with `.test.tsx|.test.ts`.

## Commit & Pull Request Guidelines

- Commits: short, imperative, descriptive (e.g., "Fix session cleanup in get_db").
- Branches: use `feature/*`, `fix/*`; open PRs against `main`.
- PRs must:
  - Pass `make ci` (lint + type-check + format + build + test).
  - Include clear description, linked issue, and screenshots for UI changes.

**After Backend API Changes**: Regenerate frontend API types:
```bash
make openapi  # From project root, no server needed
```

**Secrets scan behavior**: `scripts/ci/jobs/secrets-scan.sh` prefers a local `gitleaks` binary, then Docker if the daemon is available, then a pinned `gh`-downloaded cache. Do not reintroduce an unconditional Docker daemon dependency for the fast gate.

## Docker Builds

Default local compose/build paths use local Dockerfiles and do not require GHCR auth. GHCR image pulls are reserved for release/production workflows.

```bash
docker build -f backend/Dockerfile.dev ..
```

- Compose-backed backend/crawler/worker builds use the **monorepo root** as Docker context; when excluding local artifacts, update the root `.dockerignore`, not just `morphio-io/.dockerignore`.

**Platform constraint**: `worker-ml` is amd64-only (torchcodec lacks ARM64 wheels). Docker Compose files include `platform: linux/amd64`. For manual builds on ARM64:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -f backend/Dockerfile.worker-ml ..
```

## Security & Configuration

- Never commit secrets; use `*.env.example` files as templates.
- Required keys: `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, DB/Redis settings, `NEXT_PUBLIC_API_BASE_URL`.
- Rotate credentials used in local testing.
