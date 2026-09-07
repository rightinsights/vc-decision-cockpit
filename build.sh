#!/usr/bin/env bash
# Build both halves. Used on the gateway box, on Replit, and locally.
set -euo pipefail
cd "$(dirname "$0")"

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

echo "== backend venv"
if [ ! -x backend/.venv/bin/python ] && [ ! -x backend/.venv/Scripts/python.exe ]; then
  if ! python3 -m venv backend/.venv; then
    echo "python3 -m venv failed. On Debian/Ubuntu: sudo apt install -y python3-venv   (then rerun build.sh)"
    exit 1
  fi
fi
PY=backend/.venv/bin/python
[ -x "$PY" ] || PY=backend/.venv/Scripts/python.exe

echo "== backend deps"
"$PY" -m pip install --quiet --upgrade pip
"$PY" -m pip install --quiet -r backend/requirements.txt

echo "== frontend build"
cd frontend
# npm install rather than npm ci: lockfiles drift across npm versions and platforms; a demo build must not block on that.
npm install --no-audit --no-fund
npm run build
echo "== build complete"
