# ADR 0002: Provider SDK Boundary Adapters

Status: Accepted
Date: 2025-12-29

## Context

morphio-core should remain provider-agnostic to keep the core library portable and
unit-testable. Direct SDK imports in morphio-io backend blur boundaries and increase
coupling to external services.

## Decision

Introduce provider adapters in morphio-io and route all SDK interactions through
those adapters. Enforce the boundary with the audit script and pre-commit checks.

## Consequences

- Provider integrations must add or update an adapter instead of calling SDKs
  directly from business logic.
- The separation improves testability and allows alternate providers to be swapped
  more easily.
- Some additional indirection is required when adding new provider features.
