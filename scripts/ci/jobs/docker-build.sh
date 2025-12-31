#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
docker buildx build --load -f morphio-io/backend/Dockerfile.api -t morphio-io-backend-api:local .
docker run --rm --entrypoint python -e APP_ENV=development morphio-io-backend-api:local -c "import app.services.logs; print('ok')"
docker buildx build --load -f morphio-io/backend/Dockerfile.crawler -t morphio-io-crawler:local .
