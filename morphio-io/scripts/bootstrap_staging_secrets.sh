#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SECRETS_DIR="$ROOT/secrets"

umask 077
mkdir -p "$SECRETS_DIR"

created_admin_password=""

write_secret() {
  local path="$1"
  local value="$2"
  if [ ! -f "$path" ]; then
    printf '%s' "$value" > "$path"
  fi
}

read_secret() {
  local path="$1"
  if [ -f "$path" ]; then
    cat "$path"
  fi
}

if [ ! -f "$SECRETS_DIR/SECRET_KEY" ]; then
  write_secret "$SECRETS_DIR/SECRET_KEY" "$(openssl rand -base64 48)"
fi

if [ ! -f "$SECRETS_DIR/JWT_SECRET_KEY" ]; then
  write_secret "$SECRETS_DIR/JWT_SECRET_KEY" "$(openssl rand -base64 48)"
fi

if [ ! -f "$SECRETS_DIR/DB_PASSWORD" ]; then
  if [ -f "$SECRETS_DIR/DATABASE_URL" ]; then
    python3 - <<'PY' "$SECRETS_DIR/DATABASE_URL" "$SECRETS_DIR/DB_PASSWORD"
import sys
import urllib.parse

url_path = sys.argv[1]
out_path = sys.argv[2]
raw = open(url_path, "r", encoding="utf-8").read().strip()
raw = raw.replace("postgresql+asyncpg://", "postgresql://")
parsed = urllib.parse.urlparse(raw)
password = urllib.parse.unquote(parsed.password or "")
if not password:
    sys.exit("DATABASE_URL missing password; cannot derive DB_PASSWORD")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(password)
PY
  else
    write_secret "$SECRETS_DIR/DB_PASSWORD" "$(openssl rand -hex 24)"
  fi
fi

if [ ! -f "$SECRETS_DIR/DATABASE_URL" ]; then
  db_password="$(read_secret "$SECRETS_DIR/DB_PASSWORD")"
  write_secret "$SECRETS_DIR/DATABASE_URL" "postgresql+asyncpg://morphio:${db_password}@postgres:5432/morphio"
fi

if [ ! -f "$SECRETS_DIR/REDIS_PASSWORD" ]; then
  if [ -f "$SECRETS_DIR/REDIS_URL" ]; then
    python3 - <<'PY' "$SECRETS_DIR/REDIS_URL" "$SECRETS_DIR/REDIS_PASSWORD"
import sys
import urllib.parse

url_path = sys.argv[1]
out_path = sys.argv[2]
raw = open(url_path, "r", encoding="utf-8").read().strip()
parsed = urllib.parse.urlparse(raw)
password = urllib.parse.unquote(parsed.password or "")
if not password:
    sys.exit("REDIS_URL missing password; cannot derive REDIS_PASSWORD")
with open(out_path, "w", encoding="utf-8") as f:
    f.write(password)
PY
  else
    write_secret "$SECRETS_DIR/REDIS_PASSWORD" "$(openssl rand -hex 24)"
  fi
fi

if [ ! -f "$SECRETS_DIR/REDIS_URL" ]; then
  redis_password="$(read_secret "$SECRETS_DIR/REDIS_PASSWORD")"
  write_secret "$SECRETS_DIR/REDIS_URL" "redis://:${redis_password}@redis:6384/0"
fi

if [ ! -f "$SECRETS_DIR/ADMIN_PASSWORD" ]; then
  created_admin_password="$(openssl rand -base64 24)"
  write_secret "$SECRETS_DIR/ADMIN_PASSWORD" "$created_admin_password"
fi

if [ -n "$created_admin_password" ]; then
  echo "Staging admin password (store securely): $created_admin_password"
fi

echo "✅ Staging secrets ready in $SECRETS_DIR"
