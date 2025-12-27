# Morphio Monorepo

This monorepo contains related Morphio projects for AI-powered content generation.

## Projects

| Project | Description | Path |
|---------|-------------|------|
| **morphio-io** | Full-stack web application (FastAPI + Next.js) | `morphio-io/` |
| **morphio-core** | Standalone Python library for audio/LLM/security utilities | `morphio-core/` |
| **morphio-native** | Native binaries and accelerators | `morphio-native/` |

## Documentation

- **[Shared Docs](./docs/)** - Cross-cutting guides
- **[Using morphio-core](./docs/using-morphio-core.md)** - How to use morphio-core in your own projects
- **[Architecture](./docs/architecture.md)** - How morphio-io uses morphio-core via adapters

## Quick Start

```bash
# Start the web app (backend + frontend)
make dev

# Run all tests
make test

# Full CI check (required before commits)
make check
```

## Project Relationship

morphio-core is a standalone library extracted from morphio-io. The web app uses it via **uv workspace dependency**:

```
morphio-io/backend
    |
    +-- app/adapters/       # Thin wrappers that translate exceptions
    |       audio.py        # Uses morphio_core.audio
    |       video.py        # Uses morphio_core.video
    |       url_validation.py  # Uses morphio_core.security
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

## Commands

### Root Commands (from monorepo root)

| Command | Description |
|---------|-------------|
| `make dev` | Start morphio-io dev servers |
| `make test` | Run all tests (morphio-core + morphio-io) |
| `make lint` | Lint everything |
| `make check` | Full CI check (required before commits) |
| `make clean` | Clean all build artifacts |

### morphio-io Commands (from `morphio-io/`)

| Command | Description |
|---------|-------------|
| `make dev` | Start backend + frontend |
| `make check` | Full check (openapi, format, lint, build, test) |
| `make test` | Run backend + frontend tests |
| `make dev-docker` | Run everything in Docker |

See `morphio-io/README.md` for full documentation.

### morphio-core Commands (from `morphio-core/`)

| Command | Description |
|---------|-------------|
| `uv run pytest` | Run all 133 tests |
| `uv run ruff check .` | Lint |
| `uv run ruff format .` | Format |

See `morphio-core/README.md` for full documentation.

## Development Workflow

### Working on morphio-io

```bash
cd morphio-io
make dev          # Start dev servers
make check        # Run before committing
```

### Working on morphio-core

```bash
cd morphio-core
uv run pytest     # Run tests
uv run ruff check # Lint
```

### Cross-Project Changes

When modifying morphio-core APIs that morphio-io uses:

1. Update morphio-core
2. Run morphio-core tests: `cd morphio-core && uv run pytest`
3. Update morphio-io adapters if needed
4. Run morphio-io tests: `cd morphio-io && make check`

## Architecture

### Why Separate Library?

- **Reusability**: morphio-core can be used in other projects
- **Clean separation**: No HTTP/web dependencies in core logic
- **Easier testing**: Library can be tested in isolation
- **Explicit boundaries**: Adapters translate between library and app concerns

### Adapter Pattern

morphio-io uses thin adapters (`app/adapters/`) that:
- Import from morphio-core
- Translate library exceptions to HTTP exceptions (ApplicationException)
- Keep the boundary clear between library and application concerns

## Tech Stack

### morphio-io
- **Backend**: Python 3.13+, FastAPI, SQLAlchemy, PostgreSQL, Redis
- **Frontend**: Next.js 16.1.1, React 19, TypeScript, TailwindCSS 4
- **Node.js**: ≥24.0.0
- **Ports**: Backend 8005, Frontend 3005 (Docker 3500→3005), Redis 6384
- **DevOps**: Docker, GitHub Actions

### morphio-core
- **Language**: Python 3.13+
- **Audio**: FFmpeg, Whisper (MLX/faster-whisper)
- **LLM**: OpenAI, Anthropic, Gemini SDKs
- **Video**: yt-dlp
- **Security**: URL validation, content anonymization

## Contributing

1. Create a feature branch
2. Make changes
3. Run `bash scripts/install-git-hooks.sh` once
4. Run `make ci` from monorepo root
5. Create a Pull Request

For bugs or feature requests, open an issue.
