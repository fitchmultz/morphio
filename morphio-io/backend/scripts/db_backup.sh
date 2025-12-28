#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   ./scripts/db_backup.sh backups/morphio_$(date +%F).dump

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <output_dump_file>"
  exit 1
fi

OUT=$1

if [[ -z "${DATABASE_URL:-}" ]]; then
  echo "DATABASE_URL is required (e.g., postgresql://user:pass@host:5432/db)" >&2
  exit 2
fi

mkdir -p "$(dirname "$OUT")"

echo "Creating compressed backup to $OUT"
pg_dump --no-owner --format=custom "$DATABASE_URL" -f "$OUT"
echo "Backup completed: $OUT"
