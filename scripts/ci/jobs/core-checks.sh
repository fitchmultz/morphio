#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}/morphio-core"
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
