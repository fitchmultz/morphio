# Morphio Monorepo Development Guidelines

This monorepo contains two related Python projects:

| Project | Description | Path |
|---------|-------------|------|
| **morphio-io** | Full-stack web application (FastAPI + Next.js) | `morphio-io/` |
| **morphio-core** | Standalone library for audio/LLM/security utilities | `morphio-core/` |

## Quick Start

```bash
# morphio-io (web app)
cd morphio-io
make dev          # Start backend + frontend
make check        # Run all checks (required before commits)

# morphio-core (library)
cd morphio-core
uv run pytest     # Run tests
uv run ruff check # Lint
```

## Project Relationship

morphio-core was extracted from morphio-io to create a reusable library. The relationship:

```
morphio-io/backend
    |
    +-- app/adapters/       # Thin wrappers that translate exceptions
    |       video.py        # Uses morphio_core.video
    |       url_validation.py  # Uses morphio_core.security
    |
    +-- app/utils/youtube_utils.py  # Re-exports from adapters (backward compat)
    |
    +-- pyproject.toml      # Has morphio-core as path dependency
            |
            v
morphio-core/
    +-- src/morphio_core/
            security/       # URLValidator, Anonymizer, SSRF protection
            audio/          # Chunking, transcription, speaker alignment
            llm/            # Multi-provider router (OpenAI, Anthropic, Gemini)
            video/          # YouTube URL parsing, yt-dlp download
            media/          # FFmpeg utilities
```

## Development Workflow

### Working on morphio-io (web app)
See `morphio-io/CLAUDE.md` for detailed guidelines. Key points:
- Run `make check` from `morphio-io/` before commits
- Backend: FastAPI with Python 3.13+
- Frontend: Next.js with TypeScript, pnpm, Biome

### Working on morphio-core (library)
See `morphio-core/CLAUDE.md` for detailed guidelines. Key points:
- Run `uv run pytest && uv run ruff check .` before commits
- Pure library with no HTTP/web dependencies
- 133 tests covering all modules

### Cross-Project Changes
When modifying morphio-core APIs that morphio-io uses:
1. Update morphio-core
2. Run morphio-core tests: `cd morphio-core && uv run pytest`
3. Update morphio-io adapters if needed
4. Run morphio-io tests: `cd morphio-io && make check`

## Testing

```bash
# Test morphio-core (133 tests)
cd morphio-core && uv run pytest -v

# Test morphio-io backend (79+ tests)
cd morphio-io/backend && uv run pytest

# Full morphio-io check (frontend + backend)
cd morphio-io && make check
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

## Common Tasks

| Task | Command |
|------|---------|
| Start morphio-io dev server | `cd morphio-io && make dev` |
| Run all morphio-io checks | `cd morphio-io && make check` |
| Run morphio-core tests | `cd morphio-core && uv run pytest` |
| Lint morphio-core | `cd morphio-core && uv run ruff check .` |
| Build morphio-core | `cd morphio-core && uv build` |
