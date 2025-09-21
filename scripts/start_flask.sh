#!/bin/bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

# Ensure venv exists
if [[ ! -d .venv ]]; then
  echo "Creating Python virtual environment (.venv)..."
  python3 -m venv .venv
fi

source .venv/bin/activate

# Upgrade pip quietly (first run only)
python -m pip install --upgrade pip >/dev/null 2>&1 || true

# Load environment variables if present
if [[ -f .env ]]; then
  set -a
  source .env
  set +a
fi

export FLASK_APP=app.py
export FLASK_ENV="${FLASK_ENV:-development}"
export TMPDIR="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPDIR"

python <<'PY'
import importlib.util
import sys

mods = ["flask", "sqlalchemy", "flask_admin", "wtforms"]
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    sys.exit(1)
PY

if [[ $? -ne 0 ]]; then
  echo "Installing project dependencies..."
  python -m pip install -r requirements.txt >/dev/null
fi

exec python -m flask run --reload "$@"
