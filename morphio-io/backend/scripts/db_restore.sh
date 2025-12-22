#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/db_restore.sh backups/morphio_2025-09-01.dump

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <input_dump_file>"
  exit 1
fi

IN=$1

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required (e.g., postgresql://user:pass@host:5432/db)" >&2
  exit 2
fi

echo "Restoring from $IN to target database"
pg_restore --clean --if-exists --no-owner --no-privileges -d "$DATABASE_URL" "$IN"
echo "Restore completed"

