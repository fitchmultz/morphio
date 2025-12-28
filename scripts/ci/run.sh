#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "========================================="
echo "Local CI Runner"
echo "========================================="
echo "Will run in order:"
echo "  1) scripts/ci/doctor.sh"
echo "  2) scripts/ci/jobs/native-build.sh"
echo "  3) scripts/ci/jobs/backend-checks.sh"
echo "  4) scripts/ci/jobs/frontend-checks.sh"
echo "  5) scripts/ci/jobs/openapi-drift.sh"
echo "  6) scripts/ci/jobs/docker-build.sh"
echo "  7) scripts/ci/jobs/docker-smoke.sh"
echo "  8) scripts/ci/jobs/guardrails.sh"
echo ""

bash "${SCRIPT_DIR}/doctor.sh"
bash "${SCRIPT_DIR}/jobs/native-build.sh"
bash "${SCRIPT_DIR}/jobs/backend-checks.sh"
bash "${SCRIPT_DIR}/jobs/frontend-checks.sh"
bash "${SCRIPT_DIR}/jobs/openapi-drift.sh"
bash "${SCRIPT_DIR}/jobs/docker-build.sh"
bash "${SCRIPT_DIR}/jobs/docker-smoke.sh"
bash "${SCRIPT_DIR}/jobs/guardrails.sh"

git -C "${ROOT_DIR}" diff --exit-code
