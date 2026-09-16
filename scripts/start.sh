#!/usr/bin/env sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_root"
if [ ! -x .venv/bin/python ]; then
  if command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 .venv
  else
    python3 -m venv .venv
  fi
fi
if command -v uv >/dev/null 2>&1; then
  uv pip install --python .venv/bin/python -r backend/requirements-lock.txt
else
  .venv/bin/python -m pip install -r backend/requirements-lock.txt
fi
.venv/bin/python scripts/make_samples.py
(cd web && npm ci --no-fund --no-audit && npm run build)
printf '\nShiye: http://127.0.0.1:8765 — Ctrl+C to stop.\n'
cd backend
exec "$project_root/.venv/bin/python" -m uvicorn shiye.main:app --host 127.0.0.1 --port 8765 --workers 1
