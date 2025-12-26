#!/usr/bin/env bash
set -e

echo "🗄️  Running database migrations..."
timeout 30 alembic upgrade head || echo "⚠️ Alembic timed out or failed, continuing..."

echo "🚀 Starting development server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
