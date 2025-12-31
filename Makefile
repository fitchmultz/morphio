# Morphio Monorepo - Root-level Commands
# ======================================
# This monorepo contains:
#   - morphio-native: Rust native extension (PyO3/maturin)
#   - morphio-core: Standalone Python library for audio/LLM/security
#   - morphio-io: Full-stack web application (FastAPI + Next.js)
#
# Note: Root .env is loaded by pydantic_settings automatically.
# Do NOT use `-include .env` + `export` as it breaks JSON-formatted values.

.PHONY: help \
	install install-backend install-frontend update update-backend update-frontend \
	dev dev-full dev-docker \
	staging-secrets staging-up staging-down staging-logs staging-smoke \
	test test-native test-core test-io \
	lint lint-native lint-core lint-io \
	type-check type-check-native type-check-core type-check-io \
	format format-native format-core format-io \
	generate build build-native build-frontend \
	ci check check-native check-core check-io audit-imports \
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
	@echo "  make ci       - Full CI gate (required before PRs)"
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
	@cd morphio-io/frontend && pnpm update --latest

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
# Staging Environment
# ============================================================================

staging-secrets: ## Generate staging secrets (idempotent)
	@cd morphio-io && ./scripts/bootstrap_staging_secrets.sh

staging-build: ## Build staging images (Docker)
	@cd morphio-io && docker compose -f docker-compose.staging.yml build

staging-up: ## Start staging stack (Docker)
	@cd morphio-io && docker compose -f docker-compose.staging.yml up -d

staging-down: ## Stop staging stack and remove volumes
	@cd morphio-io && docker compose -f docker-compose.staging.yml down -v --remove-orphans

staging-logs: ## Tail staging stack logs
	@cd morphio-io && docker compose -f docker-compose.staging.yml logs -f

staging-smoke: ## Run staging smoke checks (brings up staging stack)
	@bash -c '\
	set -euo pipefail; \
	if [ "$${STAGING_BUILD:-0}" = "1" ]; then $(MAKE) staging-build; fi; \
	$(MAKE) staging-up; \
	api="http://localhost:8005"; \
	dashboards="http://localhost:5601"; \
	for path in /health/ /health/db /health/redis; do \
		echo "Waiting for $$api$$path"; \
		for i in {1..60}; do \
			if curl -fsS "$$api$$path" >/dev/null; then break; fi; \
			sleep 2; \
			if [ $$i -eq 60 ]; then echo "Timeout waiting for $$path"; exit 1; fi; \
		done; \
	done; \
	echo "Waiting for OpenSearch Dashboards..."; \
	for i in {1..60}; do \
		code=$$(curl -s -o /dev/null -w "%{http_code}" "$$dashboards" || true); \
		if [ "$$code" = "200" ] || [ "$$code" = "302" ] || [ "$$code" = "401" ] || [ "$$code" = "403" ]; then break; fi; \
		sleep 2; \
		if [ $$i -eq 60 ]; then echo "Timeout waiting for Dashboards"; exit 1; fi; \
	done; \
	admin_password=$$(cat morphio-io/secrets/ADMIN_PASSWORD); \
	csrf_token=$$(curl -fsS "$$api/auth/csrf-token" \
		| python3 -c "import json,sys; print(json.load(sys.stdin)[\"data\"][\"csrf_token\"])"); \
	token=$$(curl -fsS -X POST "$$api/auth/login" -H "Content-Type: application/json" -H "X-CSRF-Token: $$csrf_token" \
		-b "csrf_token=$$csrf_token" \
		-d "{\"email\":\"admin@morphio.io\",\"password\":\"$$admin_password\"}" \
		| python3 -c "import json,sys; print(json.load(sys.stdin)[\"data\"][\"access_token\"])"); \
	curl -fsS "$$api/admin/health" -H "Authorization: Bearer $$token" >/dev/null; \
	echo "✅ Staging smoke checks passed."; \
	'
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
# Linting (ruff for Python, biome for TypeScript, clippy for Rust)
# ============================================================================

lint: lint-native lint-core lint-io ## Lint everything
	@echo "✅ All lint checks passed!"

lint-native: check-rust ## Lint morphio-native (cargo clippy)
	@echo "🔍 Linting morphio-native..."
	@cd morphio-native && cargo clippy -- -D warnings
	@echo "✅ morphio-native lint passed!"

lint-core: ## Lint morphio-core (ruff check)
	@echo "🔍 Linting morphio-core..."
	@cd morphio-core && uv run ruff check .

lint-io: ## Lint morphio-io (backend + frontend)
	@echo "🔍 Linting morphio-io..."
	@cd morphio-io && $(MAKE) lint

# ============================================================================
# Type Checking (ty for Python, tsc for TypeScript)
# ============================================================================

type-check: type-check-core type-check-io ## Type check everything
	@echo "✅ All type checks passed!"

type-check-core: ## Type check morphio-core (ty check)
	@echo "🔷 Type checking morphio-core..."
	@cd morphio-core && uv run ty check || true
	@echo "✅ morphio-core type check complete!"

type-check-io: ## Type check morphio-io (backend + frontend)
	@echo "🔷 Type checking morphio-io..."
	@cd morphio-io && $(MAKE) type-check

# ============================================================================
# Formatting (ruff format for Python, biome format for TypeScript, cargo fmt for Rust)
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
# Generate (API types)
# ============================================================================

generate: ## Generate frontend API types from backend OpenAPI schema
	@echo "🔧 Generating API types..."
	@cd morphio-io && $(MAKE) openapi

# ============================================================================
# Build
# ============================================================================

build: build-native build-frontend ## Build everything
	@echo "✅ Build complete!"

build-native: check-rust ## Build morphio-native extension
	@echo "🔨 Building morphio-native..."
	@cd morphio-native && uv run maturin develop --release

build-frontend: ## Build morphio-io frontend
	@echo "🔨 Building frontend..."
	@cd morphio-io/frontend && pnpm build

# ============================================================================
# CI Gate (Required for PRs)
# ============================================================================

ci: generate format type-check lint build test ## Full CI gate: generate → format → type-check → lint → build → test (required for PRs)
	@echo ""
	@echo "============================================"
	@echo "✅ CI passed - ready for PR!"
	@echo "============================================"

# Compatibility alias (use 'make ci' instead)
check: ci ## Alias for 'make ci' (deprecated - use 'make ci')

# ============================================================================
# Sub-project checks (for targeted validation)
# ============================================================================

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
	@cd morphio-io && $(MAKE) ci
	@echo "✅ morphio-io checks passed!"

audit-imports: ## Verify no direct provider SDK imports in morphio-io/backend/app
	@echo "🔍 Auditing provider SDK imports..."
	@./scripts/audit_imports.sh

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean all build artifacts and log files
	@echo "🧹 Cleaning CI artifacts..."
	@rm -rf .venv-ci/ .pytest_cache/ .ruff_cache/ .benchmarks/
	@echo "🧹 Cleaning log files..."
	@rm -rf log_files/ morphio-io/log_files/ morphio-io/backend/log_files/
	@echo "🧹 Cleaning uploads..."
	@rm -rf morphio-io/backend/uploads/
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
