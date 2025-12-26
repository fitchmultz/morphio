#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

python3 "$ROOT/scripts/audit_env_template.py"

docker compose -f "$ROOT/docker-compose.yml" config >/dev/null
docker compose -f "$ROOT/docker-compose.watch.yml" config >/dev/null
docker compose -f "$ROOT/docker-compose.prod.yml" config >/dev/null

forbidden_url_regex='https?://[^[:space:]]+:(3000|8000|6379)\b|redis://[^[:space:]]+:(6379)\b'
if rg -n -e "$forbidden_url_regex" "$ROOT" \
  --glob '!**/.git/**' \
  --glob '!**/node_modules/**' \
  --glob '!**/.venv/**' \
  --glob '!**/dist/**' \
  --glob '!**/.next/**'; then
  echo "Forbidden standard ports found in URLs."
  exit 1
fi

compose_port_regex='\\b(3000|8000|6379):\\d+\\b|\\b\\d+:(3000|8000|6379)\\b'
if rg -n -e "$compose_port_regex" \
  "$ROOT/docker-compose.yml" \
  "$ROOT/docker-compose.watch.yml" \
  "$ROOT/docker-compose.prod.yml"; then
  echo "Forbidden standard ports found in compose port mappings."
  exit 1
fi

echo "✅ Preflight checks passed."
