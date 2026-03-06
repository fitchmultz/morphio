# Verification Checklist

Use this exact sequence from a fresh clone.

## 1) Bootstrap

```bash
make env
make install
```

Expected:
- `/.env` created (if missing)
- baseline dependencies install without pulling optional heavy ML groups

## 2) Fast PR-equivalent confidence

```bash
make ci-fast
```

Expected:
- backend checks pass
- frontend checks pass
- guardrails pass (including working-tree secrets scan)

## 3) Full local release parity

```bash
make ci
```

Expected:
- all nine CI runner stages pass
- no git drift introduced by checks/generation

## 4) Optional heavy smoke

```bash
bash scripts/ci/jobs/docker-full-smoke.sh
```

Expected:
- full-stack docker smoke passes

## 5) Security release check (history)

```bash
bash scripts/ci/jobs/secrets-scan.sh --history
```

Expected:
- no historical secret findings

## 6) Spot-check key hardening behavior

- Confirm `morphio-io/backend/tests/unit/test_config_production_secrets.py` exists and passes.
- Confirm `.github/workflows/ci-cd.yml` runs backend/frontend/guardrails as separate jobs.
- Confirm `morphio-io/docker-compose.yml` frontend uses local `build` instead of GHCR-only pull.
