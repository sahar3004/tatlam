#!/bin/bash
set -Eeuo pipefail

TS=$(date -u +%Y%m%d-%H%M%S)
OUT="artifacts/baseline/${TS}"
mkdir -p "$OUT/logs" "$OUT/coverage" "$OUT/http" "$OUT/cli"

if [[ -d .venv ]]; then
  source .venv/bin/activate
fi

echo "[qa:baseline] pytest + coverage"
pytest --cov=tatlam --cov=app --cov=run_batch \
  --cov-report=xml:"$OUT/coverage/coverage.xml" \
  --cov-report=term-missing | tee "$OUT/logs/pytest.txt" || true

echo "[qa:baseline] Flask smoke"
python - <<'PY'
import json
from pathlib import Path
from importlib import import_module
out=Path("$OUT/http"); out.mkdir(parents=True, exist_ok=True)
app_mod=import_module("app"); app=app_mod.app
cli=app.test_client()
for path in ["/health", "/healthz/ready"]:
    resp=cli.get(path)
    (out/f"{path.strip('/').replace('/', '_') or 'root'}.json").write_text(
        json.dumps({"status": resp.status_code, "json": resp.get_json(silent=True)}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
PY

echo "[qa:baseline] CLI goldens"
python export_json.py --out "$OUT/cli/export_all.json" | tee "$OUT/logs/export_json.stdout" || true
python tatlam/simulate.py --out "$OUT/cli/sim_results.json" | tee "$OUT/logs/sim.stdout" || true

echo "[qa:baseline] done -> $OUT"

