#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

make -C "${ROOT_DIR}/morphio-io" openapi

cd "${ROOT_DIR}/morphio-io/frontend"
pnpm biome format --write openapi.json src/client

git -C "${ROOT_DIR}" diff --exit-code -- morphio-io/frontend/openapi.json morphio-io/frontend/src/client
