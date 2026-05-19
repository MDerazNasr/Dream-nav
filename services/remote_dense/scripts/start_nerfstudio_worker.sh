#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)"
cd "$ROOT_DIR"

export DREAMNAV_REMOTE_DENSE_BACKEND="${DREAMNAV_REMOTE_DENSE_BACKEND:-auto}"
export DREAMNAV_NERFSTUDIO_TRAIN_COMMAND="${DREAMNAV_NERFSTUDIO_TRAIN_COMMAND:-ns-train}"
export DREAMNAV_NERFSTUDIO_EXPORT_COMMAND="${DREAMNAV_NERFSTUDIO_EXPORT_COMMAND:-ns-export}"
export DREAMNAV_NERFSTUDIO_METHOD="${DREAMNAV_NERFSTUDIO_METHOD:-splatfacto}"

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8010}"
PYTHON_BIN="${PYTHON_BIN:-python}"
PYTHON_DIR="$(dirname "$PYTHON_BIN")"

if [[ -d "$PYTHON_DIR" ]]; then
  export PATH="$PYTHON_DIR:$PATH"
fi

exec "$PYTHON_BIN" -m uvicorn remote_dense_app.main:app --app-dir services/remote_dense --host "$HOST" --port "$PORT"
