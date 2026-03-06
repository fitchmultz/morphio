# Morphio Documentation

Shared documentation for the Morphio monorepo.

## Getting Started

**New to the project?** Start here:

- **[Onboarding Guide](./onboarding.md)** - First hour setup: install deps, configure env, verify CI passes

## Quick Links

- **[Architecture Overview](./architecture-overview.md)** - System architecture and trade-offs
- **[Validation Commands](./validation-commands.md)** - CI-equivalent local checks
- **[Verification Checklist](./verification-checklist.md)** - Short validation path
- **[Release Readiness Report](./release-readiness-report.md)** - Concrete hardening outcomes and receipts
- **[Configuration Guide](./configuration.md)** - Environment variables and setup
- **[CI Strategy](./ci-strategy.md)** - PR required vs nightly/manual gate model
- **[Upgrade Procedures](./upgrade-procedures.md)** - How to run dependency and schema upgrades
- **[Architecture Decision Records](./adrs/README.md)** - Key architectural decisions and rationale
- **[Contributing](../CONTRIBUTING.md)** - Workflow, PR protocol, and non-negotiables
- **[Troubleshooting FAQ](./troubleshooting.md)** - Common setup and CI fixes

## Guides

| Guide | Description |
|-------|-------------|
| [Architecture Overview](./architecture-overview.md) | System architecture and trade-offs |
| [Using morphio-core](./using-morphio-core.md) | How to use morphio-core in your own projects |
| [Architecture](./architecture.md) | Deep dive: adapter boundary and integration details |

## Project-Specific Docs

Each project also has its own README with project-specific documentation:

- [morphio-io README](../morphio-io/README.md) - Web application setup and development
- [morphio-core README](../morphio-core/README.md) - Library API reference and examples

## Quick Commands

```bash
# Full setup from scratch
make env && make install && bash scripts/install-git-hooks.sh && make ci-fast && make ci

# Daily development
make dev          # Start backend + frontend
make ci-fast      # Fast checks (PR parity)
make ci           # Full local release gate
make test         # Run all tests
```
