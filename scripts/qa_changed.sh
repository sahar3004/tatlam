#!/bin/bash
set -Eeuo pipefail

TS=$(date -u +%Y%m%d-%H%M%S)
OUT="artifacts/runs/${TS}"
mkdir -p "$OUT/logs" "$OUT/reports"

if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

status=0

run_step() {
  local name="$1"; shift
  echo "[qa:changed] $name" | tee -a "$OUT/logs/steps.txt"
  if "$@" >"$OUT/logs/${name}.log" 2>&1; then
    echo "✔ $name" | tee -a "$OUT/logs/steps.txt"
  else
    echo "✘ $name (see $OUT/logs/${name}.log)" | tee -a "$OUT/logs/steps.txt"
    status=1
  fi
}

run_step ruff "ruff" check .
run_step black "black" --check .
run_step mypy "mypy" --strict tatlam
run_step bandit "bandit" -r tatlam -q
run_step pip_audit "pip-audit" -r requirements.txt -f json -o "$OUT/reports/pip-audit.json"
run_step pytest "pytest" --maxfail=1 -q

echo "[qa:changed] summary status=$status (0=ok,1=issues). Full logs under $OUT" | tee -a "$OUT/logs/steps.txt"
exit 0
