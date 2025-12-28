# Contributing

## Non-negotiables

- Only `/.env` and `/.env.example` are allowed. No nested `.env*` files anywhere.
- Non-standard ports only: frontend 3005, backend 8005, redis 6384 (never introduce 3000/8000/6379).
- No PR without `make ci` passing locally.

## One-time setup

```bash
cp .env.example .env
bash scripts/install-git-hooks.sh
bash scripts/ci/doctor.sh
```

## Daily workflow (exact protocol)

```bash
git checkout -b <type>/<slug>
# make changes
make ci
```

```bash
git status --porcelain=v1 -b
```

```bash
git commit -am "<message>"
git push -u origin <type>/<slug>
gh pr create --fill --base main --head <type>/<slug>
gh pr merge --merge --delete-branch --admin
git push origin --delete <type>/<slug>
git checkout main
git pull --ff-only origin main
git status --porcelain=v1 -b
```

## Fast inner-loop checks (before full CI)

```bash
bash scripts/ci/jobs/backend-checks.sh
bash scripts/ci/jobs/frontend-checks.sh
bash morphio-io/scripts/smoke_docker.sh
```

## Changing env vars (required steps, in order)

1. Update `morphio-io/backend/app/config.py`.
2. Update `/.env.example`.
3. Update `docs/configuration.md`.
4. Run `python3 morphio-io/scripts/audit_env_template.py`.

## Changing backend API / schemas

1. Run `make -C morphio-io openapi`.
2. Commit `morphio-io/frontend/openapi.json` and `morphio-io/frontend/src/client/**`.
3. Never hand-edit generated client files.
