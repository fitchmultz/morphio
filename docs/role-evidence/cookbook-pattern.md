# Cookbook Pattern: Safe-by-Default Install + Explicit Heavy Opt-In

## Problem
Public monorepos often fail cold-start because default setup installs every optional heavy dependency.

## Pattern
1. Keep default install path minimal and deterministic.
2. Move expensive/fragile surfaces to explicit opt-in targets.
3. Keep CI fast gate aligned to minimal defaults.
4. Keep full release parity available as a separate gate.

## Implementation in this repo
- `make install` → baseline dependencies only.
- `make install-full`, `make install-ml`, `make install-ml-apple` → explicit heavy opt-ins.
- PR gate runs fast checks only; full `make ci` remains local release gate.

## Trade-offs
- Pros: faster onboarding, fewer platform failures, better reviewer confidence.
- Cons: contributors need to opt in explicitly for some specialized stacks.

## Safe Defaults
- Never require private registry auth in default local compose path.
- Fail production config on placeholder secrets.
- Enforce secret scan and architecture guardrails in PR checks.
