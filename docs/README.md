# Morphio Documentation

Shared documentation for the Morphio monorepo.

## Quick Links

- **[Project Status](./status.md)** - Current state, completed work, and what's next
- **[Configuration Guide](./configuration.md)** - Environment variables and setup
- **[Roadmap](./roadmap.md)** - Upcoming features and priorities

## Guides

| Guide | Description |
|-------|-------------|
| [Using morphio-core](./using-morphio-core.md) | How to use morphio-core in your own projects |
| [Architecture](./architecture.md) | How morphio-io uses morphio-core via adapters |

## Project-Specific Docs

Each project also has its own README with project-specific documentation:

- [morphio-io README](../morphio-io/README.md) - Web application setup and development
- [morphio-core README](../morphio-core/README.md) - Library API reference and examples

## Quick Links

- **Start developing**: `cp .env.example .env && make install && make ci && make dev` from monorepo root
- **Run all tests**: `make test`
- **Full CI check**: `make ci`
