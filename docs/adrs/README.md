# Architecture Decision Records (ADRs)

ADRs capture the significant architectural decisions for the Morphio monorepo so we
can understand why choices were made and when to revisit them.

## Format

- Store ADRs in this directory.
- Filename format: `NNNN-short-title.md` (zero-padded, lowercase, hyphenated).
- Use this template in order: **Context** -> **Decision** -> **Consequences**.
- Status values: **Proposed**, **Accepted**, **Deprecated**, **Superseded**.
- New ADRs take the next sequential number; never reuse numbers.

## Workflow

1. Draft with status **Proposed** if still under discussion.
2. Move to **Accepted** once the decision is implemented or approved.
3. Use **Deprecated** if no longer recommended.
4. Use **Superseded** when replaced by a newer ADR and link to it.

## Current ADRs

- [0001-uv-workspace-single-venv.md](./0001-uv-workspace-single-venv.md)
- [0002-provider-sdk-boundary-adapters.md](./0002-provider-sdk-boundary-adapters.md)
- [0003-make-ci-required-gate.md](./0003-make-ci-required-gate.md)
- [0004-openapi-client-generation.md](./0004-openapi-client-generation.md)
- [0005-credits-gating-usage-tracking.md](./0005-credits-gating-usage-tracking.md)
- [0006-two-tier-ci-gates.md](./0006-two-tier-ci-gates.md)
