# Morphio Monorepo - Root-level Management
# Run everything from project root - no cd'ing needed!

.PHONY: help install install-backend install-frontend install-native dev dev-full dev-backend dev-frontend dev-worker-ml dev-crawler dev-docker dev-docker-build dev-docker-down dev-docker-clean dev-docker-logs dev-docker-logs-backend dev-docker-logs-frontend dev-docker-shell-backend dev-docker-shell-frontend dev-docker-restart-backend dev-docker-restart-frontend test test-backend test-frontend lint lint-backend lint-frontend format format-backend format-frontend clean clean-backend clean-frontend setup update update-backend update-frontend outdated outdated-backend outdated-frontend update-pkg type-check type-check-backend type-check-frontend build build-backend build-frontend check openapi openapi-export openapi-generate

help: ## Show this help message
	@echo "Morphio Monorepo Commands"
	@echo "========================="
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Initial setup: install deps, copy env files
	@echo "Setting up Morphio monorepo..."
	@$(MAKE) install
	@if [ ! -f backend/.env ]; then \
		echo "Copying backend/.env.example to backend/.env"; \
		cp backend/.env.example backend/.env || true; \
	fi
	@if [ ! -f frontend/.env.local ]; then \
		echo "Copying frontend/.env.example to frontend/.env.local"; \
		cp frontend/.env.example frontend/.env.local || true; \
	fi
	@echo "✅ Setup complete!"

install: install-backend install-frontend ## Install all dependencies

install-backend: ## Install backend dependencies
	@echo "📦 Installing backend dependencies..."
	@cd backend && uv sync --all-groups --upgrade --all-extras

install-frontend: ## Install frontend dependencies
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && corepack enable && pnpm install

install-native: ## Install all native dev dependencies (Apple Silicon)
	@echo "📦 Installing native dependencies..."
	@cd backend && uv sync --group ml-apple --group ml --group crawler --group dev
	@echo "🎭 Installing Playwright browsers..."
	@cd backend && uv run playwright install chromium
	@echo "✅ Native setup complete!"

dev: ## Start native dev servers (backend + frontend + Redis via Docker)
	@bash -c '\
	cleanup() { \
		echo ""; \
		echo "🛑 Stopping Redis..."; \
		docker compose -f docker-compose.watch.yml stop redis || true; \
		if [ -n "$$BACKEND_PID" ]; then kill $$BACKEND_PID 2>/dev/null || true; fi; \
		if [ -n "$$FRONTEND_PID" ]; then kill $$FRONTEND_PID 2>/dev/null || true; fi; \
		exit; \
	}; \
	trap cleanup INT TERM; \
	echo "🚀 Starting native dev servers..."; \
	docker compose -f docker-compose.watch.yml up -d redis; \
	PORT=$$(grep -E "^APP_PORT=" .env 2>/dev/null | cut -d "=" -f2 || echo "8005"); \
	echo "🚀 Starting backend on http://localhost:$$PORT..."; \
	cd backend && uv run uvicorn app.main:app --reload --port $$PORT & \
	BACKEND_PID=$$!; \
	echo "🚀 Starting frontend on http://localhost:3005..."; \
	cd frontend && pnpm dev & \
	FRONTEND_PID=$$!; \
	wait $$BACKEND_PID $$FRONTEND_PID 2>/dev/null || true; \
	cleanup'

dev-full: ## Start ALL services natively (Apple Silicon optimized)
	@./scripts/dev-native-full.sh

dev-docker: ## Start all services in Docker with hot reload
	@echo "🐳 Starting Docker development environment..."
	@docker compose -f docker-compose.watch.yml up --build --watch

dev-docker-build: ## Rebuild and start all Docker services
	@echo "🔨 Rebuilding Docker images..."
	@docker compose -f docker-compose.watch.yml build --no-cache
	@docker compose -f docker-compose.watch.yml up --watch

dev-docker-down: ## Stop all Docker services
	@echo "🛑 Stopping Docker services..."
	@docker compose -f docker-compose.watch.yml down

dev-docker-clean: ## Stop Docker services and remove volumes
	@echo "🧹 Cleaning Docker environment..."
	@docker compose -f docker-compose.watch.yml down -v --remove-orphans

dev-docker-logs: ## View all Docker service logs
	@docker compose -f docker-compose.watch.yml logs -f

dev-docker-logs-backend: ## View Docker backend logs only
	@docker compose -f docker-compose.watch.yml logs -f backend

dev-docker-logs-frontend: ## View Docker frontend logs only
	@docker compose -f docker-compose.watch.yml logs -f frontend

dev-docker-shell-backend: ## Open shell in Docker backend container
	@docker compose -f docker-compose.watch.yml exec backend bash

dev-docker-shell-frontend: ## Open shell in Docker frontend container
	@docker compose -f docker-compose.watch.yml exec frontend sh

dev-docker-restart-backend: ## Restart Docker backend only
	@docker compose -f docker-compose.watch.yml restart backend

dev-docker-restart-frontend: ## Restart Docker frontend only
	@docker compose -f docker-compose.watch.yml restart frontend

dev-worker-ml: ## Start worker-ml natively (MLX on Apple Silicon)
	@echo "🧠 Starting ML worker on http://localhost:8001..."
	@cd backend && USE_MLX=1 uv run uvicorn worker_ml.main:app --reload --port 8001

dev-crawler: ## Start crawler natively
	@echo "🕷️  Starting crawler on http://localhost:8002..."
	@cd backend && uv run uvicorn crawler.main:app --reload --port 8002

dev-backend: ## Start backend dev server (native)
	@PORT=$$(grep -E '^APP_PORT=' .env 2>/dev/null | cut -d '=' -f2 || echo "8005"); \
	echo "🚀 Starting backend on http://localhost:$$PORT..."; \
	cd backend && uv run uvicorn app.main:app --reload --port $$PORT

dev-frontend: ## Start frontend dev server (native)
	@echo "🚀 Starting frontend on http://localhost:3005..."
	@cd frontend && pnpm dev

test: test-backend test-frontend ## Run all tests

test-backend: ## Run backend tests
	@echo "🧪 Running backend tests..."
	@cd backend && uv run pytest -q

test-frontend: ## Run frontend tests
	@echo "🧪 Running frontend tests..."
	@cd frontend && pnpm test

lint: lint-backend lint-frontend ## Lint everything

lint-backend: ## Lint backend (style and code quality)
	@echo "🔍 Linting backend..."
	@cd backend && uv run ruff check .

lint-frontend: ## Lint frontend
	@echo "🔍 Linting frontend..."
	@cd frontend && pnpm biome check .

format: format-backend format-frontend ## Format all code

format-backend: ## Format backend code
	@echo "✨ Formatting backend..."
	@cd backend && uv run ruff format .

format-frontend: ## Format frontend code
	@echo "✨ Formatting frontend..."
	@cd frontend && pnpm biome format --write .

type-check: type-check-backend type-check-frontend ## Run type checkers

type-check-backend: ## Type check backend
	@echo "🔷 Type checking backend..."
	@cd backend && uv run ty check --exclude "worker_ml/" --exclude "tests/performance/"

type-check-frontend: ## Type check frontend
	@echo "🔷 Type checking frontend..."
	@cd frontend && pnpm type-check

check: openapi format type-check lint build-frontend test ## Run openapi, format, type check, lint, build, and tests (full pre-commit check)
	@echo "✅ All checks passed!"

openapi: openapi-export openapi-generate ## Regenerate frontend API types from backend (no server needed)

openapi-export: ## Export OpenAPI schema from backend (offline)
	@echo "📄 Exporting OpenAPI schema..."
	@cd backend && PYTHONPATH=. uv run python scripts/export_openapi.py --output ../frontend/openapi.json

openapi-generate: ## Generate frontend TypeScript types from OpenAPI schema
	@echo "🔧 Generating frontend API types..."
	@cd frontend && pnpm openapi:generate

build: build-backend build-frontend ## Build everything

build-backend: ## Build backend (currently no-op, but placeholder for future)
	@echo "🔨 Building backend..."
	@echo "✅ Backend build complete (no build step needed)"

build-frontend: ## Build frontend
	@echo "🔨 Building frontend..."
	@cd frontend && pnpm build

clean: clean-backend clean-frontend ## Clean all build artifacts

clean-backend: ## Clean backend artifacts
	@echo "🧹 Cleaning backend..."
	@rm -rf backend/.venv backend/__pycache__ backend/**/__pycache__ backend/.pytest_cache

clean-frontend: ## Clean frontend artifacts
	@echo "🧹 Cleaning frontend..."
	@rm -rf frontend/node_modules frontend/.next frontend/.turbo

db-migrate: ## Run database migrations
	@echo "🗄️  Running database migrations..."
	@cd backend && uv run alembic upgrade head

db-revision: ## Create new database migration (usage: make db-revision MSG="description")
	@cd backend && uv run alembic revision --autogenerate -m "$(MSG)"

backend-shell: ## Open Python shell with backend context
	@cd backend && uv run python

frontend-shell: ## Open Node shell (not really useful, but here for symmetry)
	@cd frontend && node

# Dependency Update Commands
.PHONY: update update-backend update-frontend outdated outdated-backend outdated-frontend

outdated: outdated-backend outdated-frontend ## Show all outdated dependencies

outdated-backend: ## Show outdated Python dependencies
	@echo "🐍 Checking for outdated Python packages..."
	@cd backend && echo "Backend dependencies are managed via uv.lock." && \
	echo "Run 'make update-backend' to upgrade all dependencies, or:" && \
	echo "  cd backend && uv pip list --outdated" || true

outdated-frontend: ## Show outdated Node.js dependencies
	@echo "📦 Checking for outdated Node.js packages..."
	@cd frontend && pnpm outdated || true

update: ## Update all dependencies (interactive when possible)
	@echo "🔄 Updating all dependencies..."
	@$(MAKE) update-backend
	@$(MAKE) update-frontend
	@echo "✅ All dependencies updated!"

update-backend: ## Update backend dependencies (shows outdated, then upgrades)
	@echo "🐍 Updating backend dependencies..."
	@cd backend && \
	echo "📋 Showing outdated packages..." && \
	(uv pip list --outdated 2>/dev/null | head -20 || echo "Note: Some packages may not show as outdated.") && \
	echo "" && \
	echo "🔄 Updating all dependencies (including dev groups and extras)..." && \
	uv sync --all-groups --upgrade --all-extras && \
	echo "✅ Backend dependencies updated!"

update-frontend: ## Update frontend dependencies interactively
	@echo "📦 Updating frontend dependencies interactively..."
	@cd frontend && pnpm update --interactive

# Individual package updates (for interactive selection)
update-pkg: ## Update a specific package (usage: make update-pkg PKG=fastapi)
	@if [ -z "$(PKG)" ]; then \
		echo "❌ Usage: make update-pkg PKG=package-name"; \
		echo "Example: make update-pkg PKG=fastapi"; \
		exit 1; \
	fi
	@echo "🔄 Updating $(PKG)..."
	@cd backend && uv lock --upgrade-package $(PKG) && uv sync --dev
	@echo "✅ $(PKG) updated!"
