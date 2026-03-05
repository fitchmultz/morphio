# ADR 0003: Make CI Required Gate

Status: Superseded by ADR 0006
Date: 2025-12-29

## Context

The repo spans Python, TypeScript, and Rust with shared tooling. Historically,
checks ran in different ways locally and in CI, leading to drift and inconsistent
results.

## Decision

At the time of adoption, `make ci` was the single required gate for PRs to keep local and CI behavior identical.

## Supersession

This ADR is superseded by [ADR 0006](./0006-two-tier-ci-gates.md), which introduced a two-tier model:
- PR-required fast gate (`ci-cd.yml`)
- nightly/manual heavy smoke (`docker-full-smoke.yml`)
- local full release parity gate remains `make ci`

## Consequences

- `make ci` remains the canonical full local release gate.
- PR CI no longer runs the full local gate on every change.
- Branch protection should require the fast gate checks defined in ADR 0006.
