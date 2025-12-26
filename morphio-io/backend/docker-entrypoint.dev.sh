#!/usr/bin/env bash
set -e

echo "🗄️  Running database migrations..."
alembic upgrade head

echo "🚀 Starting development server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8005 --reload
