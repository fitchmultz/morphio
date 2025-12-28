# Developer Onboarding

Get up and running with the Morphio monorepo in under an hour.

## Prerequisites

Before starting, ensure you have:

- **macOS or Linux** (Windows WSL2 works but is untested)
- **Docker Desktop** running
- **Node.js 20+** (use `fnm` or `nvm`)
- **pnpm** (`corepack enable && corepack prepare pnpm@latest --activate`)
- **Rust toolchain** (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **ripgrep** (`brew install ripgrep` or `apt install ripgrep`)
- **GitHub CLI** (`brew install gh` then `gh auth login`)

## First Hour Setup

### 1. Clone and enter the repo

```bash
git clone https://github.com/fitchmultz/morphio-all.git
cd morphio-all
```

### 2. Copy environment template

```bash
cp .env.example .env
```

Edit `.env` to add required secrets (API keys, etc.). See [Configuration Guide](./configuration.md) for details.

### 3. Install all dependencies

```bash
make install
```

This installs:
- Python dependencies (all workspace members via uv)
- Frontend dependencies (pnpm)
- Native Rust extension (morphio-native)

### 4. Install git hooks

```bash
bash scripts/install-git-hooks.sh
```

This sets up:
- **pre-commit**: Runs linters, formatters, and boundary audits via pre-commit framework
- **pre-push**: Runs full CI gate (`make ci`) before push

### 5. Verify everything works

```bash
make ci
```

This runs the complete local CI pipeline:
- Doctor checks (dependencies, tools)
- Native build (Rust extension)
- Backend checks (ruff, pytest)
- Frontend checks (biome, tsc)
- OpenAPI drift detection
- Docker builds and smoke tests
- Guardrails (env audit, import boundary checks)

All jobs should pass with green checkmarks.

### 6. Start development servers

```bash
make dev
```

This starts:
- Backend API: http://localhost:8005
- Frontend: http://localhost:3005
- Redis: localhost:6384

## Quick Reference

| Task | Command |
|------|---------|
| Install all deps | `make install` |
| Start dev servers | `make dev` |
| Run full CI | `make ci` |
| Run tests only | `make test` |
| Fast backend checks | `bash scripts/ci/jobs/backend-checks.sh` |
| Fast frontend checks | `bash scripts/ci/jobs/frontend-checks.sh` |
| Regenerate OpenAPI client | `make -C morphio-io openapi` |

## Project Structure

```
morphio-all/
  .venv/                  # Single venv for all Python
  morphio-core/           # Standalone library (audio, LLM, security)
  morphio-io/
    backend/              # FastAPI application
    frontend/             # Next.js application
  morphio-native/         # Rust native extension
  docs/                   # Shared documentation
```

## Daily Workflow

```bash
# Create feature branch
git checkout -b feat/my-feature

# Make changes, then validate
make ci

# Commit and push
git commit -am "feat: add my feature"
git push -u origin feat/my-feature

# Create and merge PR
gh pr create --fill --base main
gh pr merge --merge --delete-branch --admin

# Return to main
git checkout main && git pull --ff-only origin main
```

## Troubleshooting

If something doesn't work, see [Troubleshooting FAQ](./troubleshooting.md).

Common first-time issues:
- **Doctor fails**: Run `bash scripts/ci/doctor.sh` to see which tool is missing
- **Docker not found**: Start Docker Desktop and wait for it to initialize
- **Python 3.13 missing**: Run `uv python install 3.13`
- **pnpm not found**: Run `corepack enable && corepack prepare pnpm@latest --activate`

## Next Steps

- Read [Architecture](./architecture.md) to understand the adapter boundary
- Read [Configuration](./configuration.md) for all environment variables
- Check [CONTRIBUTING.md](../CONTRIBUTING.md) for workflow rules and non-negotiables
