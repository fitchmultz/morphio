#!/usr/bin/env bash
# Purpose: Run policy guardrails that protect architecture, config safety, and secret hygiene.
# Responsibilities: Validate env layout/template, compose preflight, import boundaries, and secret scan.
# Scope: Repository-level deterministic safety checks for CI and local gating.
# Usage: bash scripts/ci/jobs/guardrails.sh
# Invariants/Assumptions: Root-level env policy and adapter/import boundaries are enforced with zero violations.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash scripts/ci/jobs/guardrails.sh

Runs repository guardrails:
  1) env layout audit
  2) compose/env preflight validation
  3) provider SDK import boundary audit
  4) morphio_core adapter boundary audit
  5) working-tree secrets scan

Exit codes:
  0 success
  1 runtime failure
  2 invalid usage
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
bash scripts/audit_env_layout.sh
bash morphio-io/scripts/preflight.sh
bash scripts/audit_imports.sh
bash scripts/audit_morphio_core_boundary.sh
bash scripts/ci/jobs/secrets-scan.sh --working-tree
