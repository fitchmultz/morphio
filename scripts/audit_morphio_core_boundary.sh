#!/usr/bin/env bash
# Purpose: Enforce morphio-core import boundary for the backend application layer.
# Responsibilities: Detect direct morphio_core imports outside approved adapters package.
# Scope: morphio-io/backend/app Python modules.
# Usage: bash scripts/audit_morphio_core_boundary.sh
# Invariants/Assumptions: app/adapters is the only allowed import boundary for morphio_core.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash scripts/audit_morphio_core_boundary.sh

Fails when morphio_core is imported outside app/adapters.

Exit codes:
  0 success
  1 violations or runtime failure
  2 invalid usage
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/morphio-io/backend/app"

if [[ ! -d "$APP_DIR" ]]; then
  echo "ERROR: backend app directory not found at $APP_DIR" >&2
  exit 1
fi

matches="$(grep -RInE '^(from[[:space:]]+morphio_core|import[[:space:]]+morphio_core)(\.|[[:space:]]|$)' "$APP_DIR" --include='*.py' --exclude-dir='adapters' || true)"
if [[ -n "$matches" ]]; then
  echo "ERROR: morphio_core imports found outside adapters:" >&2
  echo "$matches" >&2
  exit 1
fi

echo "OK: No morphio_core imports outside adapters."
