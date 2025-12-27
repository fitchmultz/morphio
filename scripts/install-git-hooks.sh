#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOK_SOURCE="${ROOT_DIR}/scripts/git-hooks/pre-push"
HOOK_DEST="${ROOT_DIR}/.git/hooks/pre-push"

cp "${HOOK_SOURCE}" "${HOOK_DEST}"
chmod +x "${HOOK_DEST}"

echo "Git hooks installed."
echo "To bypass once: git push --no-verify"
