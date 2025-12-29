# Morphio.io Development Guidelines

## Workspace Setup

This project is part of the `morphio-all` monorepo using **uv workspaces**. The Python `.venv` lives at the monorepo root (not in `backend/`).

```bash
# From monorepo root
make install    # Install all deps (Python + frontend)
make dev        # Start backend + frontend

# Or from this directory
make dev        # Also works
```

## Pre-Commit Requirements

**IMPORTANT**: Always run `make ci` before committing (from here or monorepo root). This runs OpenAPI type generation, type checking, linting, build, and tests for both frontend and backend. All checks must pass (green) before commits.

```bash
make ci  # Run from project root - must pass before committing
```

OpenAPI types are automatically regenerated as part of `make ci`, so frontend TypeScript types stay in sync with backend API contracts without requiring a running server.

## Makefile Commands (Preferred)

Run all commands from the **project root** using the Makefile:

- `make ci` - **Required before commits**: openapi, format, type-check, lint, build, and test everything
- `make openapi` - Regenerate frontend API types from backend (no server needed)
- `make test` - Run all tests (backend + frontend)
- `make lint` - Lint everything
- `make format` - Format all code
- `make type-check` - Type check everything
- `make dev` - Start backend + frontend natively (Redis via Docker)
- `make dev-full` - Start ALL services natively (Apple Silicon)
- `make dev-docker` - Start all services in Docker with hot reload
- `make help` - Show all available commands

## Build and Test Commands

- **Frontend (from frontend/ directory):**

  - `pnpm dev` - Start frontend dev server (port 3005)
  - `pnpm build` - Production build
  - `pnpm tlc` - Run type-check and Biome (lint + format)
  - `pnpm lint` - Run Biome check
  - `pnpm lint:fix` - Run Biome with auto-fix
  - `pnpm format` - Format code with Biome
  - `pnpm type-check` - TypeScript type checking
  - `pnpm test` - Run all tests
  - `pnpm test:utils` - Run utility tests only
  - `pnpm test:watch` - Run tests in watch mode
  - `pnpm openapi:refresh` - Regenerate API types from backend (calls `make openapi`)

- **Backend (from backend/ directory):**
  - `source ../.env && uv run uvicorn app.main:app --reload` - Start backend server (port 8005)
  - `uv run pytest tests/unit/test_file.py::TestClass::test_method -v` - Run single test
  - `uv run pytest` - Run all tests
  - `uv run ruff check .` - Lint
  - `uv run ruff format .` - Format
  - `uv run ty check` - Type check

## Code Style Guidelines

- **Frontend:**

  - Use TypeScript with strict type checking
  - PascalCase for components, camelCase for hooks (useX) and utilities
  - Use React hooks pattern for state management
  - Use Biome for linting and formatting
  - ALWAYS use pnpm (never npm or yarn)

- **Backend:**
  - Python 3.13+ with type hints
  - snake_case for functions/variables, PascalCase for classes
  - Use Ruff for linting and formatting
  - Use ty for type checking (Astral's type checker)
  - Use custom exceptions with proper error handling
  - Follow asyncio patterns for async code

## Development Ports

- **Frontend**: Port 3005 (http://localhost:3005)
- **Backend API**: Port 8005 (http://localhost:8005)
- **Redis**: Port 6384 (localhost:6384)

## Project Conventions

- Comprehensive error handling with custom exception classes
- Centralized API response formats
- Prefer reusing existing code patterns
- After changes, run full lint and type checks
- Native development by default (`make dev`), Docker available via `make dev-docker`

## API Type Generation

Frontend API types are auto-generated from the backend OpenAPI schema using @hey-api/openapi-ts:

- **Generated files**: `frontend/src/client/` (DO NOT manually edit these files)
- **When to regenerate**: After any backend API changes (routes, schemas, models)
- **How to regenerate**: Run `make openapi` from project root (no server needed)
- **Automatic regeneration**: `make ci` includes OpenAPI regeneration automatically
- **Usage**: Import types and SDK functions from `@/client` or `@/client/sdk.gen`
- **Wrapper functions**: `src/lib/apiWrappers.ts` provides compatibility wrappers with simpler signatures
