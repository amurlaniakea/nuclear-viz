#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip
fi

./.venv/bin/python -m pip install -e '.[dev]'
exec ./.venv/bin/python -m uvicorn backend.main:app --host "${HOST:-127.0.0.1}" --port "${PORT:-8000}" --reload
