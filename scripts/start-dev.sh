#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_HOST="${BACKEND_HOST:-127.0.0.1}"
BACKEND_PORT="${BACKEND_PORT:-8010}"
FRONTEND_HOST="${FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  PYTHON=("${ROOT_DIR}/.venv/bin/python")
else
  PYTHON=(uv run python)
fi

port_in_use() {
  lsof -nP -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

if port_in_use "${BACKEND_PORT}"; then
  echo "Backend port ${BACKEND_PORT} is already in use. Stop the owning process or set BACKEND_PORT." >&2
  exit 1
fi
if port_in_use "${FRONTEND_PORT}"; then
  echo "Frontend port ${FRONTEND_PORT} is already in use. Stop the owning process or set FRONTEND_PORT." >&2
  exit 1
fi

cd "${ROOT_DIR}"
"${PYTHON[@]}" manage.py migrate --noinput

backend_pid=""
frontend_pid=""
cleanup() {
  trap - EXIT INT TERM
  [[ -n "${frontend_pid}" ]] && kill "${frontend_pid}" 2>/dev/null || true
  [[ -n "${backend_pid}" ]] && kill "${backend_pid}" 2>/dev/null || true
  wait 2>/dev/null || true
}
trap cleanup EXIT INT TERM

"${PYTHON[@]}" manage.py runserver "${BACKEND_HOST}:${BACKEND_PORT}" &
backend_pid=$!

(cd "${ROOT_DIR}/frontend" && pnpm --filter @vben/web-antd dev --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}") &
frontend_pid=$!

echo "Backend: http://${BACKEND_HOST}:${BACKEND_PORT}/"
echo "Frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}/"
echo "Press Ctrl-C to stop both services."

# macOS ships Bash 3.2, which does not provide `wait -n`. Poll both child
# processes so the first service exit still tears down the other one.
while kill -0 "${backend_pid}" 2>/dev/null && kill -0 "${frontend_pid}" 2>/dev/null; do
  sleep 1
done

if ! kill -0 "${backend_pid}" 2>/dev/null; then
  wait "${backend_pid}" || exit $?
fi
if ! kill -0 "${frontend_pid}" 2>/dev/null; then
  wait "${frontend_pid}" || exit $?
fi
