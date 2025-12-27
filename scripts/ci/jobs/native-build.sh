#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"

cd "${ROOT_DIR}/morphio-native"
PYTHON="$(uv python find 3.13)"
LIBDIR="$("${PYTHON}" -c 'import sysconfig; print(sysconfig.get_config_var("LIBDIR") or "")')"
INCLUDEDIR="$("${PYTHON}" -c 'import sysconfig; print(sysconfig.get_path("include") or "")')"
LDLIBRARY="$("${PYTHON}" -c 'import sysconfig; print(sysconfig.get_config_var("LDLIBRARY") or "")')"
PYLIB="${LDLIBRARY#lib}"; PYLIB="${PYLIB%.dylib}"; PYLIB="${PYLIB%.so}"; PYLIB="${PYLIB%.a}"

export PYO3_PYTHON="${PYTHON}"
export PYO3_LIB_DIR="${LIBDIR}"
export PYO3_INCLUDE_DIR="${INCLUDEDIR}"
export RUSTFLAGS="${RUSTFLAGS:-} -L${PYO3_LIB_DIR} -l${PYLIB}"
cargo fmt --check
cargo clippy -- -D warnings
cargo test
uv run --python 3.13 maturin build --release
