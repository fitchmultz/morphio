# ADR 0003: Make CI Required Gate

Status: Accepted
Date: 2025-12-29

## Context

The repo spans Python, TypeScript, and Rust with shared tooling. Historically,
checks ran in different ways locally and in CI, leading to drift and inconsistent
results.

## Decision

Use `make ci` as the single required gate for PRs. CI runs the same target, and
merges require it to pass.

## Consequences

- All changes must satisfy formatting, linting, type checks, builds, and tests
  before merge.
- The development workflow is consistent across local and CI environments.
- CI can be slower, but it prevents regressions from slipping through.
