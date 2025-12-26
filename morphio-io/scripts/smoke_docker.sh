#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE=(docker compose -f "$ROOT/docker-compose.watch.yml")

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
    if curl -fsS "$url" >/dev/null; then
      return 0
    fi
    sleep 2
  done
  echo "Timeout waiting for $url"
  return 1
}

cleanup

if ! "${COMPOSE[@]}" up -d --build; then
  fail
fi

wait_for "http://localhost:8005/health/" || fail
wait_for "http://localhost:8005/health/db" || fail
wait_for "http://localhost:8005/health/redis" || fail
wait_for "http://localhost:3005/api/health" || fail

echo "✅ Docker smoke checks passed."
cleanup
