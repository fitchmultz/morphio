# Developer Onboarding

Get up and running with the Morphio monorepo in under an hour.

## Prerequisites

Before starting, ensure you have:

- **macOS or Linux** (Windows WSL2 works but is untested)
- **Docker Desktop** running
- **Node.js 24+** (use `fnm` or `nvm`)
- **pnpm** (`corepack enable && corepack use pnpm@10.30.3`) (or run `pnpm` in repo to use the pinned `packageManager`)
- **Rust toolchain** (`curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh`)
- **uv** (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **GitHub CLI** (`brew install gh` then `gh auth login`)

## First Hour Setup

### 1. Clone and enter the repo

```bash
git clone https://github.com/fitchmultz/morphio-all.git
cd morphio-all
```

### 2. Bootstrap local environment

```bash
make env
```

This creates `/.env` from `/.env.example` (if missing) and generates strong local values for `SECRET_KEY` and `JWT_SECRET_KEY`.

Edit `.env` to add provider/API credentials as needed. See [Configuration Guide](./configuration.md) for details.

### 3. Install baseline dependencies

```bash
make install
```

This installs the public-safe baseline:
- Python workspace dependencies required for backend/core/native development
- Frontend dependencies (pnpm)

Optional heavy stacks are explicit opt-in:

```bash
make install-full      # all optional groups/extras
make install-ml        # backend ML stack
make install-ml-apple  # Apple-specific ML extras
```
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
- morphio-core checks (ruff, pytest)
- Backend checks (ruff, ty, targeted integration tests)
- Frontend checks (biome, tsc, jest)
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
| Create/refresh env | `make env` |
| Install baseline deps | `make install` |
| Install all optional deps | `make install-full` |
| Start dev servers | `make dev` |
| Fast PR-parity checks | `make ci-fast` |
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
make ci-fast
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
- **pnpm not found**: Run `corepack enable && corepack use pnpm@10.30.3`

## Next Steps

- Read [Architecture](./architecture.md) to understand the adapter boundary
- Read [Configuration](./configuration.md) for all environment variables
- Check [CONTRIBUTING.md](../CONTRIBUTING.md) for workflow rules and non-negotiables
