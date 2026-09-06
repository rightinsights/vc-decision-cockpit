#!/usr/bin/env bash
# Build both halves. Used by Replit deployments and usable locally.
set -euo pipefail
cd "$(dirname "$0")"

export BACKEND_URL="${BACKEND_URL:-http://127.0.0.1:8000}"

echo "== backend deps"
python3 -m pip install --quiet -r backend/requirements.txt

echo "== frontend build"
cd frontend
npm ci --no-audit --no-fund
npm run build
