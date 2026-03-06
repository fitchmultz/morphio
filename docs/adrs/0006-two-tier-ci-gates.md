# ADR 0006: Two-Tier CI Gates (Fast PR + Heavy Nightly)

Status: Accepted
Date: 2026-03-05

## Context

The repository spans Python, TypeScript, Rust, and Dockerized integration paths. Running every heavy check for every PR increases latency and consumes significant CI resources, while skipping CI entirely reduces release confidence.

## Decision

Adopt two CI tiers:

1. **Fast PR-required gate** (`.github/workflows/ci-cd.yml`)
   - backend checks
   - frontend checks
   - guardrails

2. **Heavy smoke gate** (`.github/workflows/docker-full-smoke.yml`)
   - full-stack Docker smoke on nightly schedule
   - manual dispatch for on-demand validation

The full local release gate remains `make ci` (canonical local parity flow).

## Consequences

- PR feedback stays fast and deterministic.
- Heavy checks still run continuously on a schedule and can be triggered manually.
- CI resource usage is controlled without sacrificing confidence in full-stack behavior.
- Branch protection must require the fast gate to preserve baseline quality on merges.
