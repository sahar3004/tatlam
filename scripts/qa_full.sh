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
  echo "[qa:full] $name" | tee -a "$OUT/logs/steps.txt"
  if "$@" >"$OUT/logs/${name}.log" 2>&1; then
    echo "✔ $name" | tee -a "$OUT/logs/steps.txt"
  else
    echo "✘ $name (see $OUT/logs/${name}.log)" | tee -a "$OUT/logs/steps.txt"
    status=1
  fi
}

# Static quality gates
run_step ruff "ruff" check .
run_step black "black" --check .
run_step mypy "mypy" --strict tatlam
run_step bandit "bandit" -r tatlam -q

# Tests + coverage
run_step pytest "pytest" -q --maxfail=1 \
  --cov=tatlam --cov=app --cov=run_batch \
  --cov-report=xml:"$OUT/reports/coverage.xml" \
  --cov-report=term-missing

# Dependency audit (may require network; tolerated failures)
run_step pip_audit "pip-audit" -r requirements.txt -f json -o "$OUT/reports/pip-audit.json"

# Repo sanity scan (untracked backups/temp)
python - <<'PY'
import json, os, subprocess
root = os.getcwd()
def list_paths(glob):
    try:
        out = subprocess.check_output(["bash","-lc",f"rg --files -uu -g '{glob}'"], text=True)
        return [x for x in out.splitlines() if x and not x.startswith("backups/") and not x.startswith(".venv/")]
    except subprocess.CalledProcessError:
        return []

report = {
  "ds_store": list_paths("**/.DS_Store"),
  "pycache": list_paths("**/__pycache__/**"),
  "pyc": list_paths("**/*.py[co]"),
  "backups_outside_backups_dir": [p for p in list_paths("**/*.{bak,backup,save}") if ".venv/" not in p],
}
out = os.path.join("$OUT","reports","repo_sanity.json")
os.makedirs(os.path.dirname(out), exist_ok=True)
with open(out, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)
print(json.dumps({k: len(v) for k,v in report.items()}, ensure_ascii=False))
PY

echo "[qa:full] summary status=$status (0=ok,1=issues). Logs at $OUT" | tee -a "$OUT/logs/steps.txt"
exit 0

