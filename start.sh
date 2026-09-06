#!/usr/bin/env bash
# Run FastAPI (internal, 8000) and Next.js (public, $PORT or 3000) together. Exits if either dies.
set -euo pipefail
cd "$(dirname "$0")"

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"
PORT="${PORT:-3000}"

if [ ! -d frontend/.next ]; then
  echo "frontend not built; running build.sh first"
  bash build.sh
fi

(cd backend && exec python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
BACK=$!
(cd frontend && exec npx next start -p "$PORT" -H 0.0.0.0) &
FRONT=$!

trap 'kill $BACK $FRONT 2>/dev/null || true' EXIT
wait -n
