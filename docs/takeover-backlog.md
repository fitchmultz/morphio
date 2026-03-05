# Takeover Backlog (P0 / P1 / P2)

Date: 2026-03-05

## P0 (Must be true for public release)

- [x] **Safe default install path**
  - Baseline install avoids heavy optional groups by default.
- [x] **Production secret hardening**
  - Reject default/sentinel secrets in production and cover with tests.
- [x] **Fast gate structure cleanup**
  - Backend/frontend/guardrails split into parallel required jobs.
- [x] **Secret scanning in CI/local gates**
  - Guardrails now enforce working-tree secret scan.
- [x] **Default compose cold-start**
  - Local frontend build replaces GHCR-only image pull path.
- [x] **ADR/docs contract coherence**
  - ADR 0003 superseded by ADR 0006 and docs aligned.

## P1 (Should improve next)

- [ ] Add automatic fast-gate runtime budget reporting artifacts from GitHub runs.
- [ ] Add path-scoped OpenAPI drift checks for backend API surface changes.
- [ ] Add path-scoped core/native checks for PRs that touch those areas.

## P2 (Polish)

- [ ] Tighten release workflow policy and publish runbook with rollback drills.
- [ ] Expand role-evidence materials with recorded screenshots and run logs.
- [ ] Evaluate digest pinning policy for all compose/deploy surfaces.
