#!/usr/bin/env bash
# Purpose: Run deterministic backend checks used by fast CI and local inner-loop validation.
# Responsibilities: Sync backend deps in pinned env, run lint/format/type checks, run smoke-critical tests.
# Scope: morphio-io/backend static checks and selected regression/integration tests.
# Usage: bash scripts/ci/jobs/backend-checks.sh
# Invariants/Assumptions: Uses Python 3.14 in .venv-ci and uv lockfile for reproducibility.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash scripts/ci/jobs/backend-checks.sh

Runs the backend fast-gate checks:
  1) sync backend dependencies into .venv-ci (Python 3.14)
  2) env-template audit
  3) ruff lint/format check
  4) ty type check
  5) targeted unit/integration regression tests

Exit codes:
  0 success
  1 runtime failure
  2 invalid usage
EOF
  exit 0
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
if [ -x ".venv-ci/bin/python3" ]; then
  if .venv-ci/bin/python3 - <<'PY'
import sys
raise SystemExit(0 if (sys.version_info.major, sys.version_info.minor) == (3, 14) else 1)
PY
  then
    : # Reuse the existing venv when it is already Python 3.14.x.
  else
    rm -rf .venv-ci
  fi
fi

if [ ! -x ".venv-ci/bin/python3" ]; then
  rm -rf .venv-ci
  uv venv --python 3.14 .venv-ci
fi
UV_PROJECT_ENVIRONMENT=.venv-ci uv sync --project morphio-io/backend --dev --frozen
.venv-ci/bin/python3 morphio-io/scripts/audit_env_template.py
UV_PROJECT_ENVIRONMENT=.venv-ci uv run --project morphio-io/backend ruff check morphio-io/backend
UV_PROJECT_ENVIRONMENT=.venv-ci uv run --project morphio-io/backend ruff format --check morphio-io/backend
cd "${ROOT_DIR}/morphio-io/backend"
UV_PROJECT_ENVIRONMENT=../../.venv-ci uv run ty check --exclude "worker_ml/" --exclude "crawler/" --exclude "app/services/diarization/" --exclude "tests/performance/"
UV_PROJECT_ENVIRONMENT=../../.venv-ci uv run pytest -q \
  tests/unit/test_stage_progression.py \
  tests/unit/test_config_production_secrets.py \
  tests/integration/test_user_credits_flow.py \
  tests/integration/test_logs_stage_progress_updates.py
