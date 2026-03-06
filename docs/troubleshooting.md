# Troubleshooting FAQ

Common issues and solutions for the Morphio monorepo.

## Doctor / Setup Failures

### Doctor script fails

```bash
bash scripts/ci/doctor.sh
```

This script checks for all required tools. If it fails, it will tell you exactly which tool is missing. Common missing tools:

| Tool | Install |
|------|---------|
| uv | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| pnpm | `corepack enable && corepack use pnpm@10.30.3` |
| cargo/rustc | `curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \| sh` |
| gh | `brew install gh` (macOS) or see [GitHub CLI docs](https://cli.github.com/) |
| docker | Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) |

### Python 3.13 not found

```bash
uv python install 3.13
```

Then restart your shell or run `hash -r` to refresh PATH.

### Python version mismatch warnings

If you see warnings about Python version mismatches:

```bash
# Ensure the correct Python is used
uv python pin 3.13
uv sync
```

## Docker Issues

### Docker daemon not reachable

```bash
# macOS
open -a Docker

# Linux
sudo systemctl start docker
```

Wait 30-60 seconds for Docker to fully initialize before running `make ci`.

### GHCR authentication failed

The default local compose/build path now uses local Dockerfiles and should not require GHCR auth.

If you are running release/publish flows that push or pull GHCR images, authenticate first:

```bash
# Option 1: Use gh CLI token
echo $(gh auth token) | docker login ghcr.io -u $(gh api user -q .login) --password-stdin

# Option 2: Use a PAT with read/write packages as required
export GITHUB_TOKEN=ghp_xxxx
echo $GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

### Docker build cache issues

If builds are stale or failing unexpectedly:

```bash
# Clear build cache
docker builder prune -f

# Full cleanup (removes all unused images)
docker system prune -a
```

### worker-ml build fails on ARM64 (Apple Silicon)

The ML worker requires x86_64 due to `torchcodec` dependencies. Build with:

```bash
DOCKER_DEFAULT_PLATFORM=linux/amd64 docker build -f morphio-io/backend/Dockerfile.worker-ml .
```

Docker Compose files already include `platform: linux/amd64` for worker-ml.

## Python / Dependencies

### "pip install" or "uv pip install" error

**Never use `pip install` or `uv pip install` directly.** This is a uv-managed workspace.

To add a dependency:
1. Edit the appropriate `pyproject.toml`
2. Run `make install` (or `uv sync`)

### Import errors after pulling

```bash
# Resync all dependencies
make install
```

### Rust extension (morphio-native) build errors

```bash
# Rebuild native extension
bash scripts/ci/jobs/native-build.sh
```

If you see "Python newer than supported" PyO3 errors, the build script sets `PYO3_PYTHON` automatically.

## Frontend Issues

### pnpm not found

```bash
corepack enable
corepack use pnpm@10.30.3
```

### TypeScript errors after backend changes

Regenerate the OpenAPI client:

```bash
make -C morphio-io openapi
```

### Biome lint errors

```bash
# Auto-fix what can be fixed
cd morphio-io/frontend && pnpm biome check --write .
```

## CI / Git Hooks

### pre-commit hook fails

The pre-commit hook runs linters and boundary audits. To see what's failing:

```bash
uv run pre-commit run --all-files
```

To skip once (not recommended):

```bash
git commit --no-verify -m "message"
```

### pre-push hook blocks push

The pre-push hook runs the fast PR-parity gate. To see what's failing:

```bash
make ci-fast
```

For the full local release gate, run:

```bash
make ci
```

To skip once (not recommended):

```bash
git push --no-verify
```

### OpenAPI drift detected

```bash
# Regenerate and check for changes
make -C morphio-io openapi

# If drift was legitimate (new/changed endpoints), commit the changes
git add morphio-io/frontend/openapi.json morphio-io/frontend/src/client/
git commit -am "chore: regenerate openapi client"
```

## Audit / Boundary Failures

### Env template audit fails

```bash
python3 morphio-io/scripts/audit_env_template.py
```

This checks that `.env.example` has all keys from `config.py`. Fix:
1. Add missing keys to `.env.example`
2. Document new keys in `docs/configuration.md`
3. Re-run the audit

### Provider SDK import audit fails

```
ERROR: morphio_core imports found outside adapters
```

The architecture requires that `morphio-core` is only imported in `app/adapters/`. Move the import to the appropriate adapter or create a new adapter.

See [Architecture](./architecture.md) for the adapter boundary documentation.

### morphio_core boundary audit fails

Provider SDKs (openai, anthropic, google.genai) should only be imported in `morphio-core`, not directly in `morphio-io/backend`.

Fix: Use the adapters in `app/adapters/` instead of direct SDK imports.

## Redis Issues

### Connection refused to Redis

For local development, Redis runs on port 6384 (not the default 6379):

```bash
# Check if Redis is running
docker ps | grep redis

# If using Docker Compose
cd morphio-io && docker compose up redis -d

# Direct Docker
docker run -d -p 6384:6379 redis:7-alpine
```

### Redis connection string format

Use URL format with database number:
```
REDIS_URL=redis://localhost:6384/0
```

## Performance Issues

### Slow `make ci`

The CI pipeline runs many checks. For faster iteration:

```bash
# Fast backend-only checks
bash scripts/ci/jobs/backend-checks.sh

# Fast frontend-only checks
bash scripts/ci/jobs/frontend-checks.sh

# Skip Docker builds (if not changing Docker files)
bash scripts/ci/jobs/guardrails.sh
```

### Slow Docker builds

Use BuildKit cache:

```bash
DOCKER_BUILDKIT=1 docker build ...
```

Or enable it globally in Docker Desktop settings.

## Getting More Help

1. Check the [Status](./status.md) page for known issues
2. Search existing [GitHub Issues](https://github.com/fitchmultz/morphio-all/issues)
3. Ask in the project's communication channels
