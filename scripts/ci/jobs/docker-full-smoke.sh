#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
docker compose -f morphio-io/docker-compose.watch.yml --profile full down -v --remove-orphans
docker compose -f morphio-io/docker-compose.watch.yml --profile full up -d --build
docker compose -f morphio-io/docker-compose.watch.yml ps
docker compose -f morphio-io/docker-compose.watch.yml exec -T worker-ml curl -fsS http://localhost:8001/health/
docker compose -f morphio-io/docker-compose.watch.yml exec -T crawler curl -fsS http://localhost:8002/health/
docker compose -f morphio-io/docker-compose.watch.yml --profile full down -v --remove-orphans
