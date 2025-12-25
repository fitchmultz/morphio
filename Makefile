# Morphio Monorepo - Root-level Commands
# ======================================
# This monorepo contains:
#   - morphio-native: Rust native extension (PyO3/maturin)
#   - morphio-core: Standalone Python library for audio/LLM/security
#   - morphio-io: Full-stack web application (FastAPI + Next.js)

.PHONY: help \
	install install-backend install-frontend update update-backend update-frontend \
	dev dev-full dev-docker \
	test test-native test-core test-io \
	lint lint-native lint-core lint-io \
	format format-native format-core format-io \
	check check-native check-core check-io audit-imports \
	clean check-rust rmds

# Default target
help: ## Show this help message
	@echo "Morphio Monorepo - Unified Commands"
	@echo "===================================="
	@echo ""
	@echo "Quick Start:"
	@echo "  make install  - Install all dependencies (dev + optional)"
	@echo "  make update   - Update all dependencies to latest"
	@echo "  make dev      - Start morphio-io dev servers"
	@echo "  make test     - Run all tests (native + core + io)"
	@echo "  make check    - Full CI check (required before commits)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

# ============================================================================
# Prerequisites
# ============================================================================

# Use venv Python for PyO3 builds (system Python may be newer than PyO3 supports)
export PYO3_PYTHON := $(shell pwd)/.venv/bin/python

check-rust: ## Verify Rust toolchain is installed
	@command -v rustc >/dev/null 2>&1 || (echo "❌ ERROR: Rust not found. Install from https://rustup.rs" && exit 1)
	@echo "✅ Rust toolchain found: $$(rustc --version)"

# ============================================================================
# Installation (uses uv workspaces - single .venv at root)
# ============================================================================

install: check-rust install-backend install-frontend ## Install all dependencies (dev + optional)
	@echo "✅ All dependencies installed!"

install-backend: ## Install Python + Rust dependencies (morphio-native + morphio-core + morphio-io/backend)
	@echo "📦 Installing Python dependencies (workspace)..."
	@uv sync --package morphio-core --package morphio-backend --package morphio-native --all-groups --all-extras

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

test: test-native test-core test-io ## Run all tests (morphio-native + morphio-core + morphio-io)
	@echo "✅ All tests passed!"

test-native: check-rust ## Build and verify morphio-native extension
	@echo "🧪 Building morphio-native..."
	@cd morphio-native && uv run maturin develop --release
	@echo "🧪 Testing morphio-native via Python integration..."
	@uv run python -c "from morphio_native import anonymize, align_speakers_to_words; print('✅ morphio-native import OK')"
	@echo "✅ morphio-native verified! (Full tests run via morphio-core)"

test-core: ## Run morphio-core tests (175+ tests)
	@echo "🧪 Running morphio-core tests..."
	@cd morphio-core && uv run pytest -q

test-io: ## Run morphio-io tests (backend + frontend)
	@echo "🧪 Running morphio-io tests..."
	@cd morphio-io && $(MAKE) test

# ============================================================================
# Linting
# ============================================================================

lint: lint-native lint-core lint-io ## Lint everything
	@echo "✅ All lint checks passed!"

lint-native: check-rust ## Lint morphio-native (cargo fmt + clippy)
	@echo "🔍 Linting morphio-native..."
	@cd morphio-native && cargo fmt --check
	@cd morphio-native && cargo clippy -- -D warnings
	@echo "✅ morphio-native lint passed!"

lint-core: ## Lint morphio-core (ruff)
	@echo "🔍 Linting morphio-core..."
	@cd morphio-core && uv run ruff check .

lint-io: ## Lint morphio-io (backend + frontend)
	@echo "🔍 Linting morphio-io..."
	@cd morphio-io && $(MAKE) lint

# ============================================================================
# Formatting
# ============================================================================

format: format-native format-core format-io ## Format all code
	@echo "✅ All code formatted!"

format-native: check-rust ## Format morphio-native Rust code
	@echo "✨ Formatting morphio-native..."
	@cd morphio-native && cargo fmt

format-core: ## Format morphio-core Python code
	@echo "✨ Formatting morphio-core..."
	@cd morphio-core && uv run ruff format .

format-io: ## Format morphio-io (backend + frontend)
	@echo "✨ Formatting morphio-io..."
	@cd morphio-io && $(MAKE) format

# ============================================================================
# Full Check (CI/Pre-commit)
# ============================================================================

check: rmds check-native check-core check-io audit-imports ## Full CI check for entire monorepo (required before commits)
	@echo ""
	@echo "============================================"
	@echo "✅ All checks passed for entire monorepo!"
	@echo "============================================"

check-native: check-rust ## Full check for morphio-native (fmt + clippy + build + verify)
	@echo "🔎 Checking morphio-native..."
	@cd morphio-native && cargo fmt --check
	@cd morphio-native && cargo clippy -- -D warnings
	@cd morphio-native && uv run maturin develop --release
	@uv run python -c "from morphio_native import anonymize, align_speakers_to_words; print('✅ morphio-native import OK')"
	@echo "✅ morphio-native checks passed!"

check-core: ## Full check for morphio-core (lint + tests)
	@echo "🔎 Checking morphio-core..."
	@cd morphio-core && uv run ruff check . && uv run pytest -q
	@echo "✅ morphio-core checks passed!"

check-io: ## Full check for morphio-io (lint + type-check + tests)
	@echo "🔎 Checking morphio-io..."
	@cd morphio-io && $(MAKE) check
	@echo "✅ morphio-io checks passed!"

audit-imports: ## Verify no direct provider SDK imports in morphio-io/backend/app
	@echo "🔍 Auditing provider SDK imports..."
	@./scripts/audit_imports.sh

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean all build artifacts
	@echo "🧹 Cleaning morphio-native..."
	@rm -rf morphio-native/target
	@echo "🧹 Cleaning morphio-core..."
	@rm -rf morphio-core/.venv morphio-core/__pycache__ morphio-core/.pytest_cache morphio-core/.ruff_cache
	@echo "🧹 Cleaning morphio-io..."
	@cd morphio-io && $(MAKE) clean
	@echo "✅ Clean complete!"

rmds: ## Remove .DS_Store files
	find . -name .DS_Store -type f -print -delete

# ============================================================================
# Project-specific commands (pass-through)
# ============================================================================

io-%: ## Run any morphio-io command (e.g., make io-db-migrate)
	@cd morphio-io && $(MAKE) $(subst io-,,$@)
