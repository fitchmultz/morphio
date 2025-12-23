# Morphio Monorepo - Root-level Commands
# ======================================
# This monorepo contains:
#   - morphio-io: Full-stack web application (FastAPI + Next.js)
#   - morphio-core: Standalone Python library for audio/LLM/security

.PHONY: help install install-backend install-frontend update update-backend update-frontend dev test lint format check clean

# Default target
help: ## Show this help message
	@echo "Morphio Monorepo - Unified Commands"
	@echo "===================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make install  - Install all dependencies (dev + optional)"
	@echo "  make update   - Update all dependencies to latest"
	@echo "  make dev      - Start morphio-io dev servers"
	@echo "  make test     - Run all tests (core + io)"
	@echo "  make check    - Full CI check (required before commits)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Installation (uses uv workspaces - single .venv at root)
# ============================================================================

install: install-backend install-frontend ## Install all dependencies (dev + optional)
	@echo "✅ All dependencies installed!"

install-backend: ## Install Python dependencies (morphio-core + morphio-io/backend)
	@echo "📦 Installing Python dependencies (workspace)..."
	@uv sync --package morphio-core --package morphio-backend --all-groups --all-extras

install-frontend: ## Install frontend dependencies
	@echo "📦 Installing frontend dependencies..."
	@cd morphio-io/frontend && corepack enable && pnpm install

update: update-backend update-frontend ## Update all dependencies to latest versions
	@echo "✅ All dependencies updated!"

update-backend: ## Update Python dependencies to latest
	@echo "⬆️  Updating Python dependencies..."
	@uv sync --package morphio-core --package morphio-backend --all-groups --all-extras --upgrade

update-frontend: ## Update frontend dependencies to latest
	@echo "⬆️  Updating frontend dependencies..."
	@cd morphio-io/frontend && pnpm update

# ============================================================================
# Development
# ============================================================================

dev: ## Start morphio-io dev environment (backend + frontend)
	@cd morphio-io && $(MAKE) dev

dev-full: ## Start ALL morphio-io services natively (Apple Silicon)
	@cd morphio-io && $(MAKE) dev-full

dev-docker: ## Start morphio-io in Docker with hot reload
	@cd morphio-io && $(MAKE) dev-docker

# ============================================================================
# Testing
# ============================================================================

test: test-core test-io ## Run all tests (morphio-core + morphio-io)
	@echo "✅ All tests passed!"

test-core: ## Run morphio-core tests (133 tests)
	@echo "🧪 Running morphio-core tests..."
	@cd morphio-core && uv run pytest -q

test-io: ## Run morphio-io tests (backend + frontend)
	@echo "🧪 Running morphio-io tests..."
	@cd morphio-io && $(MAKE) test

# ============================================================================
# Linting & Formatting
# ============================================================================

lint: lint-core lint-io ## Lint everything
	@echo "✅ All lint checks passed!"

lint-core: ## Lint morphio-core
	@echo "🔍 Linting morphio-core..."
	@cd morphio-core && uv run ruff check .

lint-io: ## Lint morphio-io
	@echo "🔍 Linting morphio-io..."
	@cd morphio-io && $(MAKE) lint

format: format-core format-io ## Format all code
	@echo "✅ All code formatted!"

format-core: ## Format morphio-core
	@echo "✨ Formatting morphio-core..."
	@cd morphio-core && uv run ruff format .

format-io: ## Format morphio-io
	@echo "✨ Formatting morphio-io..."
	@cd morphio-io && $(MAKE) format

# ============================================================================
# Full Check (CI/Pre-commit)
# ============================================================================

check: check-core check-io ## Full CI check for both projects (required before commits)
	@echo ""
	@echo "============================================"
	@echo "✅ All checks passed for entire monorepo!"
	@echo "============================================"

check-core: ## Full check for morphio-core
	@echo "🔎 Checking morphio-core..."
	@cd morphio-core && uv run ruff check . && uv run pytest -q
	@echo "✅ morphio-core checks passed!"

check-io: ## Full check for morphio-io
	@echo "🔎 Checking morphio-io..."
	@cd morphio-io && $(MAKE) check
	@echo "✅ morphio-io checks passed!"

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean all build artifacts
	@echo "🧹 Cleaning morphio-core..."
	@rm -rf morphio-core/.venv morphio-core/__pycache__ morphio-core/.pytest_cache morphio-core/.ruff_cache
	@echo "🧹 Cleaning morphio-io..."
	@cd morphio-io && $(MAKE) clean
	@echo "✅ Clean complete!"

# ============================================================================
# Project-specific commands (pass-through)
# ============================================================================

io-%: ## Run any morphio-io command (e.g., make io-db-migrate)
	@cd morphio-io && $(MAKE) $(subst io-,,$@)
