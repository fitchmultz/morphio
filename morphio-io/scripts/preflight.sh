#!/usr/bin/env bash
# Purpose: Validate local compose/runtime preconditions before running Docker workflows.
# Responsibilities: Check env-template parity, compose config validity, and forbidden standard ports.
# Scope: morphio-io compose files plus repository URL/port policy checks.
# Usage: bash morphio-io/scripts/preflight.sh
# Invariants/Assumptions: Only custom project ports are allowed and compose files must resolve with root .env.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash morphio-io/scripts/preflight.sh

Preflight checks:
  1) env-template audit
  2) docker compose config validation for all compose files
  3) forbidden standard-port scan in URLs/compose mappings

Exit codes:
  0 success
  1 runtime failure
  2 invalid usage
EOF
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"

python3 "$ROOT/scripts/audit_env_template.py"

docker compose --env-file "$REPO_ROOT/.env" -f "$ROOT/docker-compose.yml" config >/dev/null
docker compose --env-file "$REPO_ROOT/.env" -f "$ROOT/docker-compose.watch.yml" config >/dev/null
docker compose --env-file "$REPO_ROOT/.env" -f "$ROOT/docker-compose.prod.yml" config >/dev/null
docker compose --env-file "$REPO_ROOT/.env" -f "$ROOT/docker-compose.staging.yml" config >/dev/null

forbidden_url_regex='https?://[^[:space:]]+:(3000|8000|6379)([^0-9]|$)|redis://[^[:space:]]+:(6379)([^0-9]|$)'
if grep -RInE "$forbidden_url_regex" "$REPO_ROOT" \
  --exclude-dir=.git \
  --exclude-dir=node_modules \
  --exclude-dir=.venv \
  --exclude-dir=.venv-ci \
  --exclude-dir=target \
  --exclude-dir=mlx_models \
  --exclude-dir=dist \
  --exclude-dir=.next \
  --exclude-dir=log_files \
  --exclude-dir=uploads; then
  echo "Forbidden standard ports found in URLs." >&2
  exit 1
fi

compose_port_regex='(^|[^0-9])(3000|8000|6379):[0-9]+([^0-9]|$)|(^|[^0-9])[0-9]+:(3000|8000|6379)([^0-9]|$)'
if grep -nE "$compose_port_regex" \
  "$ROOT/docker-compose.yml" \
  "$ROOT/docker-compose.watch.yml" \
  "$ROOT/docker-compose.prod.yml" \
  "$ROOT/docker-compose.staging.yml"; then
  echo "Forbidden standard ports found in compose port mappings." >&2
  exit 1
fi

echo "✅ Preflight checks passed."
