# Upgrade Procedures

This guide outlines the required steps for common upgrade workflows. Follow the
sections in order and commit the artifacts called out in each step.

## Dependency upgrades

1. Run `make update`.
2. Run `make ci`.
3. Commit `uv.lock` and `pnpm-lock.yaml`.

## API or schema changes

1. Update backend schemas or route contracts.
2. Run `make generate` from the repo root.
3. Commit `morphio-io/frontend/openapi.json` and `morphio-io/frontend/src/client/**`.

## Database migrations

1. Create a revision: `make -C morphio-io db-revision MSG="describe change"`.
2. Run migrations: `make -C morphio-io db-migrate`.
3. Commit the new migration files.

## Node or Python version bumps

1. Update `.python-version` and the `packageManager` field in the relevant
   `package.json` files.
2. Run `make install`.
3. Run `make ci`.
4. Commit updated lockfiles and version files.

## Environment variable changes

1. Update backend configuration defaults and validation.
2. Update `/.env.example`.
3. Update `docs/configuration.md`.
4. Run the env audit script: `make -C morphio-io audit-env`.
