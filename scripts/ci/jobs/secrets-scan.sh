#!/usr/bin/env bash
# Purpose: Detect potential secrets before merge or release.
# Responsibilities: Execute gitleaks in deterministic modes for working-tree or history scans.
# Scope: Repository secret scanning for CI guardrails and release readiness checks.
# Usage: bash scripts/ci/jobs/secrets-scan.sh [--working-tree|--history]
# Invariants/Assumptions: The repository allowlist lives in .gitleaks.toml and the scanner must run without requiring a Docker daemon.

set -euo pipefail

usage() {
  cat <<'EOF'
Usage: bash scripts/ci/jobs/secrets-scan.sh [OPTION]

Options:
  --working-tree   Scan current filesystem content only (default, fast CI mode)
  --history        Scan git history as well (release readiness mode)
  -h, --help       Show this help message

Examples:
  bash scripts/ci/jobs/secrets-scan.sh
  bash scripts/ci/jobs/secrets-scan.sh --working-tree
  bash scripts/ci/jobs/secrets-scan.sh --history

Exit codes:
  0 success (no leaks found)
  1 runtime failure or leaks detected
  2 usage error
EOF
}

mode="working-tree"
case "${1:-}" in
  ""|--working-tree)
    mode="working-tree"
    ;;
  --history)
    mode="history"
    ;;
  -h|--help)
    usage
    exit 0
    ;;
  *)
    echo "Unknown option: ${1}" >&2
    usage >&2
    exit 2
    ;;
esac

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
readonly GITLEAKS_VERSION="${GITLEAKS_VERSION:-v8.30.0}"
readonly GITLEAKS_VERSION_NUMBER="${GITLEAKS_VERSION#v}"
readonly GITLEAKS_IMAGE="${GITLEAKS_IMAGE:-ghcr.io/gitleaks/gitleaks:${GITLEAKS_VERSION}}"
readonly GITLEAKS_CACHE_DIR="${XDG_CACHE_HOME:-${HOME}/.cache}/morphio-all/tools/gitleaks/${GITLEAKS_VERSION}"
readonly GITLEAKS_CACHE_BIN="${GITLEAKS_CACHE_DIR}/gitleaks"

common_scan_args=(
  --config="${ROOT_DIR}/.gitleaks.toml"
  --redact
  --exit-code=1
  --log-level=error
  --max-target-megabytes=5
  --no-banner
)

local_scan_args=("${common_scan_args[@]}")
docker_scan_args=(
  --config=/repo/.gitleaks.toml
  --redact
  --exit-code=1
  --log-level=error
  --max-target-megabytes=5
  --no-banner
)

resolve_release_asset() {
  local os arch
  os="$(uname -s)"
  arch="$(uname -m)"

  case "${os}:${arch}" in
    Darwin:arm64)
      echo "gitleaks_${GITLEAKS_VERSION_NUMBER}_darwin_arm64.tar.gz"
      ;;
    Darwin:x86_64)
      echo "gitleaks_${GITLEAKS_VERSION_NUMBER}_darwin_x64.tar.gz"
      ;;
    Linux:arm64|Linux:aarch64)
      echo "gitleaks_${GITLEAKS_VERSION_NUMBER}_linux_arm64.tar.gz"
      ;;
    Linux:x86_64)
      echo "gitleaks_${GITLEAKS_VERSION_NUMBER}_linux_x64.tar.gz"
      ;;
    *)
      echo "ERROR: unsupported platform for auto-downloaded gitleaks (${os}/${arch})" >&2
      return 1
      ;;
  esac
}

verify_checksum() {
  local checksum_file asset
  checksum_file="$1"
  asset="$2"

  if command -v sha256sum >/dev/null 2>&1; then
    grep "  ${asset}\$" "${checksum_file}" | sha256sum -c -
    return 0
  fi

  if command -v shasum >/dev/null 2>&1; then
    grep "  ${asset}\$" "${checksum_file}" | shasum -a 256 -c -
    return 0
  fi

  echo "ERROR: sha256sum or shasum is required to verify downloaded gitleaks archives" >&2
  return 1
}

download_gitleaks() {
  local asset checksum_file tmp_dir
  asset="$(resolve_release_asset)"
  checksum_file="gitleaks_${GITLEAKS_VERSION_NUMBER}_checksums.txt"

  mkdir -p "${GITLEAKS_CACHE_DIR}"
  if [[ -x "${GITLEAKS_CACHE_BIN}" ]]; then
    echo "${GITLEAKS_CACHE_BIN}"
    return 0
  fi

  if ! command -v gh >/dev/null 2>&1; then
    echo "ERROR: gh CLI is required to auto-download gitleaks ${GITLEAKS_VERSION}" >&2
    return 1
  fi

  tmp_dir="$(mktemp -d)"
  trap 'rm -rf "${tmp_dir}"' RETURN

  echo "⬇️  Downloading gitleaks ${GITLEAKS_VERSION} (${asset})..." >&2
  gh release download "${GITLEAKS_VERSION}" \
    --repo gitleaks/gitleaks \
    --pattern "${asset}" \
    --pattern "${checksum_file}" \
    --dir "${tmp_dir}" >/dev/null

  (
    cd "${tmp_dir}"
    verify_checksum "${checksum_file}" "${asset}"
  ) >&2

  tar -xzf "${tmp_dir}/${asset}" -C "${tmp_dir}"
  install -m 0755 "${tmp_dir}/gitleaks" "${GITLEAKS_CACHE_BIN}"
  echo "${GITLEAKS_CACHE_BIN}"
}

run_gitleaks() {
  local local_command docker_command
  if [[ "${mode}" == "working-tree" ]]; then
    local_command=(dir "${local_scan_args[@]}" "${ROOT_DIR}")
    docker_command=(dir "${docker_scan_args[@]}" /repo)
  else
    local_command=(git "${local_scan_args[@]}" "${ROOT_DIR}")
    docker_command=(git "${docker_scan_args[@]}" /repo)
  fi

  if command -v gitleaks >/dev/null 2>&1; then
    echo "🔐 Running secrets scan (${mode}) with local gitleaks..."
    gitleaks "${local_command[@]}"
    return 0
  fi

  if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    echo "🔐 Running secrets scan (${mode}) with Docker image ${GITLEAKS_IMAGE}..."
    docker run --rm -v "${ROOT_DIR}:/repo" "${GITLEAKS_IMAGE}" "${docker_command[@]}"
    return 0
  fi

  echo "🔐 Running secrets scan (${mode}) with cached gitleaks ${GITLEAKS_VERSION}..."
  "$(download_gitleaks)" "${local_command[@]}"
}

run_gitleaks
echo "✅ Secrets scan passed (${mode})."
