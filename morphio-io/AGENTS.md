# Repository Guidelines

## Project Structure & Module Organization
- `backend/` – FastAPI app (`app/{routes,services,models,schemas,utils}`), Alembic in `db/`.
- `frontend/` – Next.js 15 app (`src/app`, `src/components`, `src/utils`).
- `docs/` – project docs; `log_files/`, `uploads/` for local data.
- Env examples: `backend/.env.example`, `frontend/.env.example`, `stack.env.example`.

## Makefile Commands (Preferred)

**IMPORTANT**: Use Makefile commands from the project root. Always run `make check` before commits.

- `make check` - **Required before commits**: type-check, lint, build, and test everything
- `make test` - Run all tests (backend + frontend)
- `make lint` - Lint everything
- `make format` - Format all code
- `make type-check` - Type check everything
- `make dev` - Start all services in Docker with hot reload
- `make dev-native` - Start backend + frontend natively
- `make help` - Show all available commands

## Build, Test, and Development Commands
- Backend (Python 3.13):
  - Setup: `cd backend && uv sync --dev && cp .env.example .env`
  - Run API: `uv run uvicorn app.main:app --reload --port 8000`
  - Tests: `uv run pytest -q` (coverage: `uv run pytest --cov=app`)
- Frontend (Node >= 24, pnpm):
  - Setup: `cd frontend && corepack enable && corepack use && pnpm install && cp .env.example .env.local`
  - Dev server: `pnpm dev` (http://localhost:3005)
  - Build/start: `pnpm build && pnpm start`
  - Tests: `pnpm test` or `pnpm test:coverage`
- Docker (optional):
  - Dev stack: `./docker-dev.sh start` (stop: `./docker-dev.sh stop -d`)
  - Prod-ish stack: `docker-compose.yml` with services `backend`, `frontend`, `redis`, `worker-ml`, `crawler`.

## Coding Style & Naming Conventions
- Python: lint with Ruff; type-check with Basedpyright (basic mode). Line length 100, Python 3.13.
  - snake_case modules/functions, PascalCase classes; include type hints.
  - Run: `uv run ruff check . && uv run basedpyright` (from `backend/`).
- TypeScript/React: ESLint + Prettier (flat config at `frontend/eslint.config.js`).
  - PascalCase components, camelCase variables/hooks; co-locate component files in `src/components`.
  - Run: `pnpm -C frontend lint` and `pnpm -C frontend format`.

## Testing Guidelines
- Backend: Pytest with asyncio; tests live in `backend/tests/{unit,integration,e2e,...}` and are named `test_*.py`.
- Frontend: Jest + Testing Library. Tests live in `__tests__` with `.test.tsx|.test.ts`.
  - Coverage threshold is configured at 50% in `frontend/jest.config.js`; use `pnpm test:coverage` locally.

## Commit & Pull Request Guidelines
- Commits: short, imperative, and descriptive (e.g., "Fix session cleanup in get_db").
- Branches: use `feature/*`, `fix/*`; open PRs against `dev` unless maintainers specify otherwise.
- PRs must:
  - Pass `pytest` and `pnpm tlcbuild` (lint + type-check + format + build).
  - Include a clear description, linked issue, and screenshots/GIFs for UI changes.

**After Backend API Changes**: Regenerate frontend API types before running checks:
```bash
cd frontend && pnpm openapi:refresh  # Backend must be running
```
This keeps frontend TypeScript types in sync with backend API contracts.

## Security & Configuration Tips
- Never commit secrets; use the provided `*.env.example` files as templates.
- Required keys commonly include `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, DB/Redis settings, and `NEXT_PUBLIC_API_BASE_URL`.
- Rotate credentials used in local testing and prefer ephemeral data in `uploads/`.
