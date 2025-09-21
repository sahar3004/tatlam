# ADR-000 — Project Structure and Architecture

Status: accepted

## Context

The codebase provides:

- A Flask web app (`app.py`) backed by SQLite.
- Batch/CLI tools for generating, validating, exporting, and rendering scenarios (`run_batch.py`, `export_json.py`, `render_cards.py`, `import_gold_md.py`).
- Shared helpers recently extracted into a Python package `tatlam/` (categories, logging, simulations).

We need a structure that enables:

- Clean separations between domain helpers and I/O glue (Flask/CLI).
- Reliable imports for tests/CI.
- Gradual hardening (typing, logging, validation) without breaking runtime parity.

## Decision

Adopt a Minimal Single-Package layout with a first-party package `tatlam` holding shared domain-oriented utilities (categories, logging, simulation), while keeping the Flask app and CLIs as entry-point modules at the repository root.

Pattern: “Functional core, imperative shell”

- Core: `tatlam` (pure helpers and DTOs). Small functions with full type hints and docstrings.
- Imperative shell: `app.py` (Flask + SQLAlchemy), CLIs (`run_batch.py`, `render_cards.py`, etc.).

Why not `src/`? The current code already runs in local environments and in editable installs. Adding a `src/` move would create churn with little ROI today. We keep `tatlam` as the shared package and ensure `pyproject.toml` declares it.

## Consequences

- Imports are stable (`tatlam.*`) and testable.
- We can steadily migrate more logic into `tatlam` over time (DTOs/validators), keeping the app thin.
- CI and QA scripts operate against this structure without path hacks.

## Alternatives considered

1) `src/` layout — Good isolation but requires broader moves. Deferred.
2) Hexagonal/Clean — Attractive for long-term; current scope doesn’t justify reshaping adapters/ports yet.
3) Multi-package monorepo — Overkill for a single service + tools.

