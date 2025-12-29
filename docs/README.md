# Morphio Documentation

Shared documentation for the Morphio monorepo.

## Getting Started

**New to the project?** Start here:

- **[Onboarding Guide](./onboarding.md)** - First hour setup: install deps, configure env, verify CI passes

## Quick Links

- **[Project Status](./status.md)** - Current state, completed work, and what's next
- **[Configuration Guide](./configuration.md)** - Environment variables and setup
- **[Upgrade Procedures](./upgrade-procedures.md)** - How to run dependency and schema upgrades
- **[Architecture Decision Records](./adrs/README.md)** - Key architectural decisions and rationale
- **[Contributing](../CONTRIBUTING.md)** - Workflow, PR protocol, and non-negotiables
- **[Troubleshooting FAQ](./troubleshooting.md)** - Common setup and CI fixes
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

## Quick Commands

```bash
# Full setup from scratch
cp .env.example .env && make install && bash scripts/install-git-hooks.sh && make ci

# Daily development
make dev          # Start backend + frontend
make ci           # Run all checks before commit
make test         # Run all tests
```
