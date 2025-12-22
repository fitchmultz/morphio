#!/usr/bin/env bash
set -e

# Check if admin password is set
if [ -z "$ADMIN_PASSWORD" ]; then
    echo "WARNING: ADMIN_PASSWORD environment variable not set."
    echo "An admin user will NOT be automatically created."
    echo "To create an admin user, set ADMIN_PASSWORD (and optionally ADMIN_EMAIL and ADMIN_NAME)."
fi

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "$UVICORN_WORKERS"
