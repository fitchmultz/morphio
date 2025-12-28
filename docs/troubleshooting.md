# Troubleshooting

## Doctor failures

```bash
bash scripts/ci/doctor.sh
```

## Python 3.13 missing

```bash
uv python install 3.13
```

## PyO3 "Python newer than supported"

```bash
bash scripts/ci/jobs/native-build.sh
```

This job sets `PYO3_PYTHON` automatically.

## Docker daemon not reachable

```bash
open -a Docker
```

## OpenAPI/client drift

```bash
make -C morphio-io openapi
make ci
```

## Env audit failures

```bash
python3 morphio-io/scripts/audit_env_template.py
# Fix missing keys in /.env.example, then re-run:
python3 morphio-io/scripts/audit_env_template.py
```
