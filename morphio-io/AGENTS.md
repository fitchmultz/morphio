<!-- AGENTS ONLY: This file is exclusively for AI agents, not humans -->

**Keep this file updated** as you learn project patterns. Follow: concise, index-style, no duplication.

# morphio-io

## Goal
- Full-stack Morphio app: FastAPI backend + Next.js frontend within the `morphio-all` monorepo.

## Source Of Truth
- Root orchestration and CI: `/Users/mitchfultz/Projects/AI/morphio-all/Makefile`
- Service orchestration and OpenAPI generation: `/Users/mitchfultz/Projects/AI/morphio-all/morphio-io/Makefile`
- Backend config/runtime deps: `/Users/mitchfultz/Projects/AI/morphio-all/morphio-io/backend/pyproject.toml`
- Frontend deps/runtime: `/Users/mitchfultz/Projects/AI/morphio-all/morphio-io/frontend/package.json`
- Architecture and onboarding: `/Users/mitchfultz/Projects/AI/morphio-all/docs/`

## Runtime Notes
- Python floor is 3.14 across the workspace; local CI scripts and Dockerfiles assume that cutover.
- Frontend runtime target is Node 25 with pnpm from `packageManager`.
- The shared Python `.venv` lives at the monorepo root; prefer root `make` targets over ad hoc nested setup.

## Non-Obvious Patterns
- Rate-limited FastAPI routes must include `request: Request` so the decorator has context.
- Public product language uses “quota tiers”; avoid reviving legacy subscription/billing terminology in app code.
- OpenAPI client output under `frontend/src/client/**` is generated from `frontend/openapi-ts.config.ts`; never hand-edit generated files.
- Frontend tests use Jest + Testing Library, not Vitest.
- `scripts/ci/jobs/secrets-scan.sh` must keep its local-binary → Docker-if-available → cached-`gh` fallback flow; do not hard-require Docker for the fast gate.
- Compose-backed Docker builds use the monorepo root as build context, so ignore/exclude changes belong in the root `.dockerignore`.

## Constraints
- `worker-ml` stays `linux/amd64`; torchcodec does not provide ARM64 wheels.
