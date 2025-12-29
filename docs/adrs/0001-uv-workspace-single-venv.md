# ADR 0001: UV Workspace Single Venv

Status: Accepted
Date: 2025-12-29

## Context

The monorepo contains multiple Python packages (morphio-native, morphio-core, and
morphio-io/backend). We need consistent dependency resolution, shared tooling,
reliable CI, and a single source of truth for Python dependency versions.

## Decision

Use a single uv workspace with one root `.venv` and a shared `uv.lock`. All Python
packages are installed via root-level `uv sync` commands.

## Consequences

- Dependency resolution is centralized in one lockfile.
- Developers use root `make install`/`make update` to keep environments consistent.
- Per-package virtual environments are not supported, so local tooling should point
  to the root `.venv`.
