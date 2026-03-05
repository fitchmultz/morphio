# Workshop Outline (45–60 Minutes)

## Agenda
1. Monorepo architecture and CI tiers (10 min)
2. Guardrails and security posture (10 min)
3. Hands-on: run fast gate + inspect failures (15 min)
4. Hands-on: production secret hardening test walk-through (10 min)
5. Debrief: trade-offs and rollout policy (10–15 min)

## Hands-on Labs
- Lab A: Execute `make ci-fast` and map outputs to job scripts.
- Lab B: Intentionally set placeholder production secret and observe config/test failure.
- Lab C: Run working-tree secret scan and interpret results.

## Success Criteria
- Participants can explain PR vs nightly vs local gates.
- Participants can reproduce and diagnose guardrail failures.
- Participants can run reviewer checklist independently.

## Failure Modes to Discuss
- CI runtime regression above budget.
- False positives in secret scanning.
- Drift between docs and executable gate scripts.
