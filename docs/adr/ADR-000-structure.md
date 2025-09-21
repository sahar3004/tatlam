# ADR-000 — Repository Structure & Evolution Plan

Status: Accepted
Date: 2025-09-20
Decision Category: Architecture / Structure

## Context

The project currently follows a Functional Core & Imperative Shell pattern:
- Core domain in `tatlam/` (e.g., `categories.py`, `simulate.py`, `logging_setup.py`).
- Flask app in `app.py` with templates in `templates/`.
- CLI tools at the repo root (`run_batch.py`, `export_json.py`, `render_cards.py`, `import_gold_md.py`).
- QA tooling in `scripts/` and tests under `tests/`.
- Assets and data under `gold_md/`, `schema/`, `db/`, and run outputs under `artifacts/`.

There is an unused `src/tatlam/` directory, and some generated folders exist in the tree. We need a professional, import-reliable, test‑friendly structure with safe, incremental evolution and Baseline Parity.

## Decision

We keep the Functional Core & Imperative Shell pattern and evolve the tree in 3 phases with gates:

### Phase 1 — Housekeeping & Guardrails (no behavior changes)
- Add a professional `.gitignore` (venv, caches, artifacts, local DBs, logs, etc.).
- Document the plan in this ADR and reference it in code reviews.
- Remove the empty `src/tatlam/` directory to avoid confusion (keep current on-root package layout).
- Keep all imports and entrypoints untouched to preserve Baseline Parity.

### Phase 2 — Incremental Modularization with Backward‑Compatible Shims
- Introduce structure inside `tatlam/` without breaking imports:
  - `tatlam/core/` (domain): move `tatlam/categories.py` -> `tatlam/core/categories.py`.
  - `tatlam/infra/` (platform): move `tatlam/logging_setup.py` -> `tatlam/infra/logging.py`.
  - `tatlam/sim/` (simulation): move `tatlam/simulate.py` -> `tatlam/sim/engine.py`.
- Keep thin re-export wrappers at original paths (`tatlam/categories.py`, `tatlam/logging_setup.py`, `tatlam/simulate.py`) for import compatibility.
- Keep top-level CLI files as shims to preserve current workflows; gradually shift logic into `tatlam/` modules.
- Gate each move with `make qa-changed` (ruff/black, mypy, bandit, tests) and raise a red flag if any delta is detected.

### Phase 3 — Entrypoints & Web Modularization (optional, post‑stabilization)
- Define `[project.scripts]` in `pyproject.toml` for stable CLI entrypoints (e.g., `tatlam-export-json`, `tatlam-run-batch`), with current root scripts kept as lightweight shims.
- Prepare for an app factory pattern under `tatlam/web/` and slim `app.py` to glue-only (blueprints, admin/view modules later as needed).
- Optionally migrate to a modern `src/` layout once wrappers are in place and editable installs are standard in dev (`pip install -e .`), guarded by QA gates.

## Consequences

- Phase 1 is risk-free and improves hygiene and clarity.
- Phase 2 yields a clearer separation (domain vs. infra vs. sim) without breaking imports or CLIs, at the cost of temporary wrappers during migration.
- Phase 3 formalizes entrypoints and prepares the web layer to scale while keeping Baseline Parity and test stability.

## Acceptance & QA

- Baseline Parity: no behavior changes in Phase 1. Each Phase 2 move gated by `qa-changed` and golden diffs where applicable.
- Type/lint/security remain green (`ruff`, `black`, `mypy --strict` on `tatlam/`, `bandit`, `pip-audit`).
- Tests continue to run under `pytest` with ≥85% overall coverage target.

## Target (end-of-Phase 3) Snapshot

```
tatlam/
  core/
    categories.py
  infra/
    logging.py
  sim/
    engine.py
  __init__.py
app.py
templates/
entrypoints/ (optional shims)
run_batch.py  (shim)
export_json.py (shim)
render_cards.py (shim)
import_gold_md.py (shim)
scripts/
tests/
docs/
  adr/
    ADR-000-structure.md
artifacts/ (ignored)
db/ (local sqlite, ignored)
```

## Notes

- This ADR is intentionally minimal and will be referenced by follow-up, narrower ADRs if deeper web modularization or `src/` migration is undertaken.

