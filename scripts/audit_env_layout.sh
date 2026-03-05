#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "${ROOT_DIR}"

# .env may exist locally for Docker/dev, but it must never be tracked.
if git ls-files --error-unmatch .env >/dev/null 2>&1; then
  echo "❌ ERROR: /.env is tracked by git. Remove it from the index with: git rm --cached .env"
  exit 1
fi

# Enforce single env-file policy: only root /.env and /.env.example are allowed.
mapfile -t env_candidates < <(
  find . \
    \( -path '*/.git/*' -o -path '*/.venv/*' -o -path '*/.venv-ci/*' -o -path '*/node_modules/*' -o -path '*/.next/*' \) -prune \
    -o -type f \( -name '.env' -o -name '.env.*' \) -print
)

violations=()
for candidate in "${env_candidates[@]}"; do
  case "${candidate}" in
    ./.env|./.env.example)
      ;;
    *)
      violations+=("${candidate}")
      ;;
  esac
done

if [ ${#violations[@]} -gt 0 ]; then
  echo "❌ ERROR: forbidden env files found (only /.env and /.env.example are allowed):"
  printf '  - %s\n' "${violations[@]}"
  exit 1
fi

echo "✅ Env layout audit passed."
