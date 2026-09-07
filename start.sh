#!/usr/bin/env bash
# Run FastAPI (internal, 8000) and Next.js (public, $PORT or 3000) together. Exits if either dies.
set -euo pipefail
cd "$(dirname "$0")"

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
PORT="${PORT:-3000}"

PY=backend/.venv/bin/python
[ -x "$PY" ] || PY=backend/.venv/Scripts/python.exe
if [ ! -x "$PY" ] || [ ! -d frontend/.next ]; then
  echo "not built yet; running build.sh first"
  bash build.sh
fi
PY="$(cd "$(dirname "$PY")" && pwd)/$(basename "$PY")"

(cd backend && exec "$PY" -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACK=$!
(cd frontend && exec npx next start -p "$PORT" -H 0.0.0.0) &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null || true' EXIT
wait -n
