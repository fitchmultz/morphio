#!/usr/bin/env bash
# Purpose: Verify local toolchain prerequisites before running the full local CI gate.
# Responsibilities: Fail fast on missing runtime/tool dependencies with actionable fixes.
# Scope: Root env files, Python/Node/uv/Docker/Rust availability checks.
# Usage: bash scripts/ci/doctor.sh
# Invariants/Assumptions: make ci requires docker daemon and pinned toolchain minimums.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash scripts/ci/doctor.sh

Checks:
  - root env files and nested-env policy
  - uv + Python 3.14
  - Node >= 25 + corepack
  - Docker CLI + daemon reachability
  - Rust cargo toolchain

Exit codes:
  0 success
  1 runtime failure
  2 invalid usage
EOF
  exit 0
fi

fail() {
  echo "ERROR: $1"
  echo "Fix: $2"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found" "$2"
}

[[ -f ".env.example" ]] || fail ".env.example missing" "Restore .env.example at repo root"
[[ -f ".env" ]] || fail ".env missing" "make env"
[[ ! -f "morphio-io/.env" ]] || fail "Nested morphio-io/.env found" "Remove morphio-io/.env"

require_cmd uv "curl -LsSf https://astral.sh/uv/install.sh | sh"
PYTHON="$(uv python find 3.14 2>/dev/null || true)"
if [[ -z "${PYTHON}" ]]; then
  fail "Python 3.14 required" "uv python install 3.14"
fi
"${PYTHON}" -c 'import sys; assert sys.version_info[:2] >= (3, 14)' >/dev/null 2>&1 \
  || fail "Python 3.14 required" "uv python install 3.14"

require_cmd node "Install Node.js 25+ (https://nodejs.org)"
node -p "Number(process.versions.node.split('.')[0]) >= 25" | grep -q true \
  || fail "node >= 25 required" "Install Node.js 25+ (https://nodejs.org)"

require_cmd corepack "npm install -g corepack"
require_cmd docker "Install Docker Desktop/Engine and add docker to PATH"
docker info >/dev/null 2>&1 || fail "Docker daemon not reachable" "Start Docker daemon (e.g., open -a Docker)"

require_cmd cargo "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

echo "Doctor checks passed."
