# ADR 0005: Credits Gating and Usage Tracking

Status: Accepted
Date: 2025-12-29

## Context

Morphio needs a consistent way to track usage and enforce plan limits across
processing workloads. Without a unified approach, limits are inconsistent and
usage-quota logic becomes fragmented.

## Decision

Track usage credits per user and gate processing based on remaining credits. Expose
credit summaries via the `/user/credits` endpoint and related UI components.

## Consequences

- Processing requests must record usage and enforce limits before execution.
- Users receive consistent visibility into remaining credits.
- Admin users are treated as unlimited for operational flexibility.
