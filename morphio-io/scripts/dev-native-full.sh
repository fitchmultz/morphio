#!/usr/bin/env bash
set -euo pipefail

cleanup() {
    echo "🛑 Stopping all services..."
    docker compose -f docker-compose.watch.yml stop redis 2>/dev/null || true
    pkill -f "uvicorn app.main:app" 2>/dev/null || true
    pkill -f "uvicorn worker_ml.main:app" 2>/dev/null || true
    pkill -f "uvicorn crawler.main:app" 2>/dev/null || true
    pkill -f "next dev" 2>/dev/null || true
}

trap cleanup INT TERM EXIT

echo "🚀 Starting full native dev environment (Apple Silicon)..."

docker compose -f docker-compose.watch.yml up -d redis
sleep 2

echo "🧠 Starting worker-ml (MLX)..."
(cd backend && USE_MLX=1 uv run uvicorn worker_ml.main:app --port 8001 --reload) &

echo "🕷️  Starting crawler..."
(cd backend && uv run uvicorn crawler.main:app --port 8002 --reload) &

echo "🔌 Starting backend..."
(cd backend && uv run uvicorn app.main:app --port 8005 --reload) &

echo "🎨 Starting frontend..."
(cd frontend && pnpm dev) &

echo ""
echo "==========================================="
echo "Native dev environment running:"
echo "  Frontend:  http://localhost:3005"
echo "  Backend:   http://localhost:8005"
echo "  Worker-ML: http://localhost:8001 (MLX)"
echo "  Crawler:   http://localhost:8002"
echo "  Redis:     localhost:6384"
echo "==========================================="

wait
