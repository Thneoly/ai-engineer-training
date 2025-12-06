#!/usr/bin/env bash
set -euo pipefail

UV_CMD=${UV_CMD:-uv}
HOST=${SMART_CS_HOST:-0.0.0.0}
PORT=${SMART_CS_PORT:-8000}
BACKEND_URL=${SMART_CS_GRADIO_BACKEND:-http://127.0.0.1:${PORT}}
HEALTH_URL=${BACKEND_URL%/}/health
PID_FILE=${SMART_CS_BACKEND_PID_FILE:-/tmp/smart_cs_backend.pid}

cleanup() {
  if [[ -n "${SERVER_PID:-}" ]] && kill -0 "$SERVER_PID" 2>/dev/null; then
    echo "[gradio] stopping backend (PID $SERVER_PID)"
    kill "$SERVER_PID"
    wait "$SERVER_PID" || true
  fi
  rm -f "$PID_FILE"
}

ensure_port_free() {
  if command -v lsof >/dev/null 2>&1; then
    if lsof -i ":${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
      echo "[gradio] port ${PORT} already in use, attempting to stop previous backend"
      if [[ -f "$PID_FILE" ]]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
          kill "$OLD_PID"
          sleep 1
        fi
      fi
      if lsof -i ":${PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
        echo "[gradio] port ${PORT} is still occupied, please free it and retry" >&2
        exit 1
      fi
    fi
  fi
}

wait_for_health() {
  local retries=20
  until curl -sf "$HEALTH_URL" >/dev/null 2>&1; do
    retries=$((retries - 1))
    if [[ $retries -le 0 ]]; then
      echo "[gradio] backend failed to pass health check at $HEALTH_URL" >&2
      exit 1
    fi
    sleep 0.5
  done
}

trap cleanup EXIT

ensure_port_free

echo "[gradio] starting backend on ${HOST}:${PORT}"
$UV_CMD run python -m smart_customer_service.main &
SERVER_PID=$!
echo "$SERVER_PID" > "$PID_FILE"

wait_for_health
echo "[gradio] backend healthy, launching Gradio UI"

SMART_CS_GRADIO_BACKEND="$BACKEND_URL" $UV_CMD run python -m smart_customer_service.gradio_ui
