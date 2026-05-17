#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python}"

export CUDA_HOME="${CUDA_HOME:-/usr/local/cuda}"
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH:-}:${CUDA_HOME}/lib64:${CUDA_HOME}/extras/CUPTI/lib64"
export PATH="${PATH}:${CUDA_HOME}/bin"

"$PYTHON_BIN" -m pip install --upgrade pip setuptools wheel
"$PYTHON_BIN" -m pip install --upgrade ninja
"$PYTHON_BIN" -m pip install --upgrade gsplat nerfstudio

if command -v ns-install-cli >/dev/null 2>&1; then
  ns-install-cli >/dev/null 2>&1 || true
fi

echo "installed nerfstudio and gsplat"
