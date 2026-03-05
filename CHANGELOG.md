# Changelog

All notable changes to this repository are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and this project uses semantic versioning intent.

## [Unreleased]

### Added
- `make env` + `scripts/bootstrap_env.sh` for secure local environment bootstrap.
- `scripts/audit_env_layout.sh` guardrail enforcing env file policy.
- `docs/architecture-overview.md` reviewer architecture summary.
- `docs/validation-commands.md` local CI-equivalent validation checklist.
- `docs/release-readiness-report.md` release hardening report.
- `SECURITY.md` and `CODE_OF_CONDUCT.md`.
- Nightly schedule for full-stack Docker smoke workflow.

### Changed
- Root `make ci` now runs the canonical full local CI runner (`scripts/ci/run.sh`).
- Added `make ci-fast` for fast PR-parity checks.
- PR CI workflow now runs fast deterministic checks automatically on PRs and main pushes.
- `.env.example` now uses generated secret sentinels instead of weak dev defaults.
- Onboarding/contributing/status/docs index updated for env bootstrap and CI strategy clarity.
- Standardized `ty` minimum version to `>=0.0.20` across workspace manifests (root, core, backend) to match validated latest stable toolchain.

### Security
- Tightened root env ignore policy and automated detection of forbidden tracked/nested env files.
