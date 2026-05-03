#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO_ROOT="$(cd "$ROOT/.." && pwd)"
COMPOSE=(docker compose --env-file "$REPO_ROOT/.env" -f "$ROOT/docker-compose.watch.yml" -f "$ROOT/docker-compose.ci-smoke.yml")

cleanup() {
  "${COMPOSE[@]}" down -v --remove-orphans
}

fail() {
  echo "❌ Docker smoke failed."
  "${COMPOSE[@]}" logs --no-color
  cleanup
  exit 1
}

wait_for() {
  local url="$1"
  local timeout="${2:-180}"
  local start=$SECONDS
  while (( SECONDS - start < timeout )); do
    if curl -fsS --max-time 5 "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.5
  done
  echo "Timeout waiting for $url"
  return 1
}

json_get() {
  local json="$1"
  local path="$2"
  python3 -c 'import json, sys
path = sys.argv[1].split(".")
data = json.load(sys.stdin)
try:
    for key in path:
        if key.isdigit():
            data = data[int(key)]
        else:
            data = data[key]
except (KeyError, IndexError, TypeError):
    sys.exit(1)
print(data)
' "$path" <<<"$json"
}

json_expect() {
  local json="$1"
  local path="$2"
  local expected="$3"
  local actual
  if ! actual=$(json_get "$json" "$path"); then
    echo "Missing $path in response."
    return 1
  fi
  if [[ "$actual" != "$expected" ]]; then
    echo "Unexpected $path: $actual (expected $expected)."
    return 1
  fi
}

cleanup

if ! "${COMPOSE[@]}" up -d --build; then
  fail
fi

wait_for "http://localhost:8005/health/" || fail
wait_for "http://localhost:8005/health/db" || fail
wait_for "http://localhost:8005/health/redis" || fail
wait_for "http://localhost:3005/api/health" || fail

API_BASE="http://localhost:8005"
USER_SUFFIX="$(python3 - <<'PY'
import uuid

print(uuid.uuid4().hex)
PY
)"
REGISTER_PAYLOAD=$(printf '{"email":"smoke_%s@example.com","password":"StrongP@ssw0rd","display_name":"Smoke User %s"}' "$USER_SUFFIX" "$USER_SUFFIX")

if ! REGISTER_RESPONSE=$(curl -fsS -X POST "$API_BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d "$REGISTER_PAYLOAD"); then
  fail
fi
json_expect "$REGISTER_RESPONSE" "status" "success" || fail
ACCESS_TOKEN=$(json_get "$REGISTER_RESPONSE" "data.access_token") || fail

if ! CREDITS_RESPONSE=$(curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE/user/credits"); then
  fail
fi
json_expect "$CREDITS_RESPONSE" "status" "success" || fail

API_KEY_NAME="smoke-key-$USER_SUFFIX"
API_KEY_PAYLOAD=$(printf '{"name":"%s","scopes":[]}' "$API_KEY_NAME")
if ! API_KEY_CREATE_RESPONSE=$(curl -fsS -X POST "$API_BASE/user/api-keys" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$API_KEY_PAYLOAD"); then
  fail
fi
json_expect "$API_KEY_CREATE_RESPONSE" "status" "success" || fail
API_KEY_ID=$(json_get "$API_KEY_CREATE_RESPONSE" "data.id") || fail

if ! API_KEY_LIST_RESPONSE=$(curl -fsS -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE/user/api-keys"); then
  fail
fi
json_expect "$API_KEY_LIST_RESPONSE" "status" "success" || fail
if ! python3 -c 'import json, sys
key_id = int(sys.argv[1])
data = json.load(sys.stdin).get("data", [])
ids = [item.get("id") for item in data]
if key_id not in ids:
    sys.exit(1)
' "$API_KEY_ID" <<<"$API_KEY_LIST_RESPONSE"; then
  echo "API key id $API_KEY_ID not found in list."
  fail
fi

if ! API_KEY_REVOKE_RESPONSE=$(curl -fsS -X DELETE \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  "$API_BASE/user/api-keys/$API_KEY_ID"); then
  fail
fi
json_expect "$API_KEY_REVOKE_RESPONSE" "status" "success" || fail

echo "✅ Docker smoke checks passed."
cleanup
