#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${ROOT_DIR}/scripts/git-hooks"
GIT_HOOKS_DIR="${ROOT_DIR}/.git/hooks"

for hook in pre-commit pre-push; do
  cp "${HOOKS_DIR}/${hook}" "${GIT_HOOKS_DIR}/${hook}"
  chmod +x "${GIT_HOOKS_DIR}/${hook}"
done

echo "Git hooks installed."
echo "To bypass once: git push --no-verify"
