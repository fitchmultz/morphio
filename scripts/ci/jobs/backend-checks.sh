#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
uv venv --python 3.13 .venv-ci
UV_PROJECT_ENVIRONMENT=.venv-ci uv sync --project morphio-io/backend --dev --frozen
.venv-ci/bin/python3 morphio-io/scripts/audit_env_template.py
UV_PROJECT_ENVIRONMENT=.venv-ci uv run --project morphio-io/backend ruff check morphio-io/backend
UV_PROJECT_ENVIRONMENT=.venv-ci uv run --project morphio-io/backend ruff format --check morphio-io/backend
cd "${ROOT_DIR}/morphio-io/backend"
UV_PROJECT_ENVIRONMENT=../../.venv-ci uv run ty check --exclude "worker_ml/" --exclude "crawler/" --exclude "app/services/diarization/" --exclude "tests/performance/"
