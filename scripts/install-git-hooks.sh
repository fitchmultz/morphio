#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOOKS_DIR="${ROOT_DIR}/scripts/git-hooks"
GIT_HOOKS_DIR="${ROOT_DIR}/.git/hooks"

# Install pre-commit hook via pre-commit framework
echo "Installing pre-commit hook..."
uv run pre-commit install --hook-type pre-commit

# Install custom pre-push hook (runs full CI gate)
echo "Installing pre-push hook..."
cp "${HOOKS_DIR}/pre-push" "${GIT_HOOKS_DIR}/pre-push"
chmod +x "${GIT_HOOKS_DIR}/pre-push"

echo ""
echo "Git hooks installed:"
echo "  - pre-commit: managed by pre-commit framework"
echo "  - pre-push: runs make ci (full local CI gate)"
echo ""
echo "To bypass once: git commit --no-verify / git push --no-verify"
