# ADR 0004: OpenAPI Client Generation

Status: Accepted
Date: 2025-12-29

## Context

The frontend depends on backend API contracts. Manual updates to API clients and
schemas are error-prone and lead to drift between backend changes and frontend
assumptions.

## Decision

Generate OpenAPI schemas and TypeScript clients from the backend using `make generate`
(root) or `make openapi` (morphio-io). Commit the generated `openapi.json` and
frontend client artifacts to the repo.

## Consequences

- Backend API changes must be followed by regeneration and commit of client
  artifacts.
- The frontend stays in sync with backend contracts, reducing runtime errors.
- Generated files should not be hand-edited.
