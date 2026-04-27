#!/usr/bin/env bash
# Purpose: Build the local Docker images exercised by the full CI gate.
# Responsibilities: Build backend/crawler images with normal Docker layer-cache reuse and smoke-import backend code.
# Scope: Local Docker-only validation for morphio-io backend and crawler images.
# Usage: bash scripts/ci/jobs/docker-build.sh [--prune]
# Invariants/Assumptions: Docker's content-addressed cache is safe to reuse because build inputs include Dockerfiles, lockfiles, and copied source layers.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash scripts/ci/jobs/docker-build.sh [--prune]

Builds the Docker images used by the local CI gate.

Options:
  --prune  Reclaim unused Docker build cache and unused images before building.
            This is useful when debugging stale local Docker state, but it is not
            the default local CI path because it destroys valid build caches.

Exit codes:
  0 success
  1 runtime failure
  2 invalid usage
EOF
  exit 0
fi

PRUNE=0
if [[ "${1:-}" == "--prune" ]]; then
  PRUNE=1
elif [[ -n "${1:-}" ]]; then
  echo "ERROR: unknown argument: ${1}" >&2
  echo "Fix: use --prune or no arguments" >&2
  exit 2
fi

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"

if [[ "${PRUNE}" -eq 1 ]]; then
  echo "Reclaiming unused Docker build cache before CI image builds..."
  docker builder prune -af >/dev/null
  docker image prune -af >/dev/null
fi

docker image rm -f morphio-io-backend-api:local morphio-io-crawler:local >/dev/null 2>&1 || true

docker buildx build --load -f morphio-io/backend/Dockerfile.api -t morphio-io-backend-api:local .
docker run --rm --entrypoint python -e APP_ENV=development morphio-io-backend-api:local -c "import app.services.logs; print('ok')"
docker buildx build --load -f morphio-io/backend/Dockerfile.crawler -t morphio-io-crawler:local .
