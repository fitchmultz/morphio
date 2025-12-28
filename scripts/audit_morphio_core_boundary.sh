#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR="$ROOT_DIR/morphio-io/backend/app"

if ! command -v rg >/dev/null 2>&1; then
  echo "ERROR: rg is required to run morphio_core boundary audit." >&2
  exit 1
fi

cd "$APP_DIR"
matches="$(rg -n "^(from morphio_core|import morphio_core)\\b" . --glob '!adapters/**' || true)"
if [[ -n "$matches" ]]; then
  echo "ERROR: morphio_core imports found outside adapters:" >&2
  echo "$matches" >&2
  exit 1
fi

echo "OK: No morphio_core imports outside adapters."
