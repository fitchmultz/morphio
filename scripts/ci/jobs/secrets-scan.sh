#!/usr/bin/env bash
# Purpose: Detect potential secrets before merge or release.
# Responsibilities: Execute gitleaks in deterministic modes for working-tree or history scans.
# Scope: Repository secret scanning for CI guardrails and release readiness checks.
# Usage: bash scripts/ci/jobs/secrets-scan.sh [--working-tree|--history]
# Invariants/Assumptions: Docker is available and .gitleaks.toml defines repository-specific allowlists.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/ci/jobs/secrets-scan.sh [OPTION]

Options:
  --working-tree   Scan current filesystem content only (default, fast CI mode)
  --history        Scan git history as well (release readiness mode)
  -h, --help       Show this help message

Examples:
  bash scripts/ci/jobs/secrets-scan.sh
  bash scripts/ci/jobs/secrets-scan.sh --working-tree
  bash scripts/ci/jobs/secrets-scan.sh --history

Exit codes:
  0 success (no leaks found)
  1 runtime failure or leaks detected
  2 usage error
EOF
}

mode="working-tree"
case "${1:-}" in
  ""|--working-tree)
    mode="working-tree"
    ;;
  --history)
    mode="history"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown option: ${1}" >&2
    usage >&2
    exit 2
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
GITLEAKS_IMAGE="${GITLEAKS_IMAGE:-ghcr.io/gitleaks/gitleaks:v8.24.2}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker is required for secrets scan" >&2
  exit 1
fi

scan_args=(
  detect
  --source=/repo
  --config=/repo/.gitleaks.toml
  --redact
  --exit-code=1
  --max-target-megabytes=5
)
if [[ "${mode}" == "working-tree" ]]; then
  scan_args+=(--no-git)
fi

echo "🔐 Running secrets scan (${mode})..."
docker run --rm -v "${ROOT_DIR}:/repo" "${GITLEAKS_IMAGE}" "${scan_args[@]}"
echo "✅ Secrets scan passed (${mode})."
