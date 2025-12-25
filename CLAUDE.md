# Morphio Monorepo Development Guidelines

This monorepo uses **uv workspaces** with a single `.venv` at the root.

**IMPORTANT**: This is a **uv-managed project**. NEVER use `pip install`, `uv pip install`, or any direct package installation. All dependencies must be declared in `pyproject.toml` files and installed via `make install` or `uv sync`.

- **To add a dependency**: Edit the appropriate `pyproject.toml` and run `make install`
- **NEVER run**: `pip install X`, `uv pip install X`, or similar commands

| Project | Description | Path |
|---------|-------------|------|
| **morphio-io** | Full-stack web application (FastAPI + Next.js) | `morphio-io/` |
| **morphio-core** | Standalone library for audio/LLM/security utilities | `morphio-core/` |

## Quick Start

```bash
# From monorepo root (recommended)
make install      # Install all deps (Python + frontend)
make dev          # Start backend + frontend
make check        # Run all checks (required before commits)
make test         # Run all tests

# Or work in subdirectories
cd morphio-io && make dev
cd morphio-core && uv run pytest
```

## Workspace Structure

This monorepo uses uv workspaces with a **single `.venv` at the root**:

```
morphio-all/
    pyproject.toml          # Workspace root - defines members
    .venv/                  # Single venv for all Python deps
    uv.lock                 # Unified lockfile
    |
    +-- morphio-core/       # Workspace member (library)
    |       pyproject.toml
    |       src/morphio_core/
    |
    +-- morphio-io/
            +-- backend/    # Workspace member (app)
            |       pyproject.toml  # Uses: morphio-core = { workspace = true }
            +-- frontend/   # Next.js (pnpm)
```

morphio-core is referenced as a workspace dependency (not path):
```toml
# morphio-io/backend/pyproject.toml
morphio-core = { workspace = true }
```

## Development Workflow

### Working on morphio-io (web app)
See `morphio-io/CLAUDE.md` for detailed guidelines. Key points:
- Run `make check` before commits (from root or `morphio-io/`)
- Backend: FastAPI with Python 3.13+
- Frontend: Next.js with TypeScript, pnpm, Biome

### Working on morphio-core (library)
See `morphio-core/CLAUDE.md` for detailed guidelines. Key points:
- Run `uv run pytest && uv run ruff check .` before commits
- Pure library with no HTTP/web dependencies
- 175+ tests covering all modules

### Cross-Project Changes
Since both projects share the same `.venv`, changes are immediately available:
1. Update morphio-core
2. Run tests: `make test` (runs both projects)
3. Update morphio-io adapters if needed

## Testing

```bash
# From root - run all tests
make test

# Or individually
make test-core    # morphio-core tests (175+ tests)
make test-io      # morphio-io tests (backend + frontend)

# Direct pytest (from any directory - uses root .venv)
uv run pytest morphio-core/tests -v
uv run pytest morphio-io/backend/tests -v
```

## Architecture Decisions

### Why Separate Library?
- Reusable across multiple projects
- Cleaner separation of concerns
- No FastAPI/HTTP dependencies in core logic
- Easier to test in isolation

### Adapter Pattern
morphio-io uses thin adapters (`app/adapters/`) that:
- Import from morphio-core
- Translate library exceptions to HTTP exceptions (ApplicationException)
- Keep the boundary clear between library and application concerns

### Design Principles (morphio-core)
- No global settings - all config via explicit objects
- Library exceptions only - no HTTP status codes
- Protocol-first interfaces for testability
- SDK client injection for mocking

## Docker Builds

Docker images pull from GHCR (ghcr.io) and require authentication:

```bash
# Source secrets before Docker builds
source ~/.secrets

# Build examples
docker build -f morphio-io/backend/Dockerfile.dev .
docker build -f morphio-io/backend/Dockerfile.api .
```

**Note**: `~/.secrets` should export `GITHUB_TOKEN` or configure Docker credential helpers for GHCR access.

## Common Tasks

| Task | Command |
|------|---------|
| Install all dependencies | `make install` |
| Update all dependencies | `make update` |
| Start dev servers | `make dev` |
| Run all checks (pre-commit) | `make check` |
| Run all tests | `make test` |
| Run morphio-core tests only | `make test-core` |
| Run morphio-io tests only | `make test-io` |
| Lint everything | `make lint` |
| Format everything | `make format` |
| Build morphio-core | `cd morphio-core && uv build` |
