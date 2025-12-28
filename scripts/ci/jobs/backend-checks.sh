#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
if [ -x ".venv-ci/bin/python3" ]; then
  if .venv-ci/bin/python3 - <<'PY'
import sys
raise SystemExit(0 if (sys.version_info.major, sys.version_info.minor) == (3, 13) else 1)
PY
  then
    : # Reuse the existing venv when it is already Python 3.13.x.
  else
    rm -rf .venv-ci
  fi
fi

if [ ! -x ".venv-ci/bin/python3" ]; then
  rm -rf .venv-ci
  uv venv --python 3.13 .venv-ci
fi
UV_PROJECT_ENVIRONMENT=.venv-ci uv sync --project morphio-io/backend --dev --frozen
.venv-ci/bin/python3 morphio-io/scripts/audit_env_template.py
UV_PROJECT_ENVIRONMENT=.venv-ci uv run --project morphio-io/backend ruff check morphio-io/backend
UV_PROJECT_ENVIRONMENT=.venv-ci uv run --project morphio-io/backend ruff format --check morphio-io/backend
cd "${ROOT_DIR}/morphio-io/backend"
UV_PROJECT_ENVIRONMENT=../../.venv-ci uv run ty check --exclude "worker_ml/" --exclude "crawler/" --exclude "app/services/diarization/" --exclude "tests/performance/"
UV_PROJECT_ENVIRONMENT=../../.venv-ci uv run pytest -q tests/unit/test_stage_progression.py
