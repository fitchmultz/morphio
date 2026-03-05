#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"
ENV_EXAMPLE_FILE="${ROOT_DIR}/.env.example"

if [[ ! -f "${ENV_EXAMPLE_FILE}" ]]; then
  echo "❌ ERROR: .env.example not found at repo root."
  exit 1
fi

if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${ENV_EXAMPLE_FILE}" "${ENV_FILE}"
  echo "Created .env from .env.example"
fi

cd "${ROOT_DIR}"

python3 - <<'PY'
from pathlib import Path
import secrets

root = Path.cwd()
env_path = root / ".env"
lines = env_path.read_text(encoding="utf-8").splitlines()

seed_values = {
    "",
    '""',
    "dev_secret_key",
    "dev_jwt_secret_key",
    "__GENERATE_SECURE_VALUE__",
    "__CHANGE_ME__",
}
secret_keys = {"SECRET_KEY", "JWT_SECRET_KEY"}

updated = []
for line in lines:
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        updated.append(line)
        continue

    key, value = line.split("=", 1)
    if key in secret_keys and value.strip() in seed_values:
        value = secrets.token_urlsafe(48)
        updated.append(f"{key}={value}")
    else:
        updated.append(line)

env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
PY

chmod 600 "${ENV_FILE}" 2>/dev/null || true

echo "✅ .env is ready with strong local SECRET_KEY and JWT_SECRET_KEY values."
