#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}"
bash morphio-io/scripts/preflight.sh
bash scripts/audit_imports.sh
bash scripts/audit_morphio_core_boundary.sh
