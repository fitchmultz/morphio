# ADR 0005: Demo Quota Gating and Usage Tracking

Status: Accepted
Date: 2025-12-29

## Context

Morphio needs a consistent way to track usage and enforce demo quota limits across
processing workloads. Without a unified approach, limits are inconsistent and
usage-quota logic becomes fragmented.

## Decision

Track weighted usage per user and gate processing based on remaining monthly quota.
Expose usage summaries via the `/user/credits` endpoint and related UI components.

## Consequences

- Processing requests must record usage and enforce limits before execution.
- Users receive consistent visibility into remaining monthly quota.
- Admin users are treated as unlimited for operational flexibility.
