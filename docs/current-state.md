# Current State (Takeover Baseline)

Date: 2026-03-05

## Stack and Structure
- Monorepo with three projects: `morphio-core` (Python library), `morphio-io` (FastAPI + Next.js app), `morphio-native` (Rust extension).
- Root orchestration via `Makefile` and `scripts/ci/run.sh`.

## Primary User/Operator Flows
1. **Install and run locally**
   - `make env`
   - `make install`
   - `make dev`
2. **Fast PR confidence**
   - `make ci-fast`
3. **Full release parity gate**
   - `make ci`
4. **Heavy smoke (nightly/manual parity)**
   - `bash scripts/ci/jobs/docker-full-smoke.sh`

## Known Constraints and Risks (Snapshot)
- Optional heavy ML stacks can be platform-sensitive (opt-in only).
- Fast gate runtime target requires ongoing measurement on hosted runners.
- History-level secret scan remains required before public repository flip.

## Top Risks Addressed in This Pass
- Resource-abusive default install path
- Placeholder production secrets acceptance
- Weak PR gate structure/runtime controls
- Missing CI-enforced secret scanning
- Default compose path requiring GHCR image pulls
- ADR/documentation gate-contract drift
