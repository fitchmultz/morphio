#!/usr/bin/env bash
set -euo pipefail

fail() {
  echo "ERROR: $1"
  echo "Fix: $2"
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || fail "$1 not found" "$2"
}

require_cmd uv "curl -LsSf https://astral.sh/uv/install.sh | sh"
PYTHON="$(uv python find 3.13 2>/dev/null || true)"
if [[ -z "${PYTHON}" ]]; then
  fail "Python 3.13 required" "uv python install 3.13"
fi
"${PYTHON}" -c 'import sys; assert sys.version_info[:2] >= (3, 13)' >/dev/null 2>&1 \
  || fail "Python 3.13 required" "uv python install 3.13"

require_cmd node "brew install node"
node -p "Number(process.versions.node.split('.')[0]) >= 24" | grep -q true \
  || fail "node >= 24 required" "brew install node"

require_cmd corepack "npm install -g corepack"
require_cmd rg "brew install ripgrep"

require_cmd docker "brew install --cask docker"
docker info >/dev/null 2>&1 || fail "Docker daemon not reachable" "open -a Docker"

require_cmd cargo "curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh"

echo "Doctor checks passed."
