#!/usr/bin/env bash
# Purpose: Orchestrate the repository's full local CI gate with safe concurrency.
# Responsibilities: Run all canonical validation jobs, fail with logs on any job failure, and detect CI-induced worktree drift.
# Scope: Local developer/agent CI only; hosted CI configuration is intentionally out of scope.
# Usage: bash scripts/ci/run.sh
# Invariants/Assumptions: Parallelized jobs are independent read-only, isolated-cache, or separate-image Docker checks; OpenAPI drift runs after frontend checks because it rewrites generated client files; pre-existing local edits are allowed but CI commands must not add new drift.

set -euo pipefail

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  cat <<'EOF'
Usage: bash scripts/ci/run.sh

Runs the full local CI gate in dependency-safe phases:
  1) doctor prerequisite checks
  2) independent native/core/backend/frontend/guardrail jobs in parallel
  3) OpenAPI drift check
  4) independent Docker image build and smoke checks in parallel
  5) worktree drift assertion and completion summary

Exit codes:
  0 success
  1 validation failure
  2 invalid usage
EOF
  exit 0
elif [[ -n "${1:-}" ]]; then
  echo "ERROR: unknown argument: ${1}" >&2
  echo "Fix: run with no arguments, or use -h/--help." >&2
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

run_step() {
  local label="$1"
  local script_path="$2"
  local start duration
  start=$SECONDS
  echo "▶ ${label}"
  bash "${script_path}"
  duration=$((SECONDS - start))
  echo "✓ ${label} (${duration}s)"
}

run_parallel_phase() {
  local phase_name="$1"
  shift
  local log_dir pids labels failures i pid label script_path start duration
  log_dir="$(mktemp -d "${TMPDIR:-/tmp}/morphio-ci-${phase_name// /-}.XXXXXX")"
  pids=""
  labels=""
  failures=0
  start=$SECONDS

  echo "▶ ${phase_name} (parallel)"
  while [[ "$#" -gt 0 ]]; do
    label="$1"
    script_path="$2"
    shift 2
    labels="${labels}${label}"$'\n'
    (
      echo "▶ ${label}"
      bash "${script_path}"
      echo "✓ ${label}"
    ) >"${log_dir}/${label}.log" 2>&1 &
    pids="${pids}$!"$'\n'
  done

  i=1
  while IFS= read -r pid; do
    [[ -n "${pid}" ]] || continue
    label="$(printf '%s' "${labels}" | sed -n "${i}p")"
    if wait "${pid}"; then
      cat "${log_dir}/${label}.log"
    else
      echo "✗ ${label} failed. Log follows:" >&2
      cat "${log_dir}/${label}.log" >&2
      failures=1
    fi
    i=$((i + 1))
  done <<<"${pids}"

  rm -rf "${log_dir}"
  duration=$((SECONDS - start))
  if [[ "${failures}" -ne 0 ]]; then
    echo "✗ ${phase_name} failed (${duration}s)" >&2
    return 1
  fi
  echo "✓ ${phase_name} (${duration}s)"
}

cat <<'EOF'
=========================================
Local CI Runner
=========================================
Will run dependency-safe phases:
  1) scripts/ci/doctor.sh
  2) Parallel: native-build, core-checks, backend-checks, frontend-checks, guardrails
  3) scripts/ci/jobs/openapi-drift.sh
  4) Parallel: docker-build, docker-smoke
  5) worktree drift assertion and completion summary
EOF
echo ""

BEFORE_STATUS="$(git -C "${ROOT_DIR}" status --porcelain=v1 --untracked-files=all)"

run_step "doctor" "${SCRIPT_DIR}/doctor.sh"
run_parallel_phase "static-and-test checks" \
  "native-build" "${SCRIPT_DIR}/jobs/native-build.sh" \
  "core-checks" "${SCRIPT_DIR}/jobs/core-checks.sh" \
  "backend-checks" "${SCRIPT_DIR}/jobs/backend-checks.sh" \
  "frontend-checks" "${SCRIPT_DIR}/jobs/frontend-checks.sh" \
  "guardrails" "${SCRIPT_DIR}/jobs/guardrails.sh"
run_step "openapi-drift" "${SCRIPT_DIR}/jobs/openapi-drift.sh"
run_parallel_phase "docker checks" \
  "docker-build" "${SCRIPT_DIR}/jobs/docker-build.sh" \
  "docker-smoke" "${SCRIPT_DIR}/jobs/docker-smoke.sh"

AFTER_STATUS="$(git -C "${ROOT_DIR}" status --porcelain=v1 --untracked-files=all)"
if [[ "${AFTER_STATUS}" != "${BEFORE_STATUS}" ]]; then
  echo "ERROR: local CI changed the worktree. Review generated or formatted file drift." >&2
  git -C "${ROOT_DIR}" status --short >&2
  exit 1
fi

echo "✅ Local CI runner passed."
