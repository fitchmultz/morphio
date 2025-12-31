#!/usr/bin/env bash
set -e

if [ -z "${ADMIN_PASSWORD:-}" ]; then
    if [ -n "${ADMIN_PASSWORD_FILE:-}" ] && [ -f "$ADMIN_PASSWORD_FILE" ]; then
        export ADMIN_PASSWORD="$(cat "$ADMIN_PASSWORD_FILE")"
    elif [ -f /run/secrets/ADMIN_PASSWORD ]; then
        export ADMIN_PASSWORD="$(cat /run/secrets/ADMIN_PASSWORD)"
    fi
fi

# Check if admin password is set
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "WARNING: ADMIN_PASSWORD environment variable not set."
    echo "An admin user will NOT be automatically created."
    echo "To create an admin user, set ADMIN_PASSWORD (and optionally ADMIN_EMAIL and ADMIN_NAME)."
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${APP_PORT:-8005}" --workers "$UVICORN_WORKERS"
