# Repository Guidelines

## Project Structure & Module Organization
- Core domain: `tatlam/` (categories, logging, simulations).
- Web app entry: `app.py`; views in `templates/` (Jinja2).
- CLI tools: `run_batch.py`, `export_json.py`, `render_cards.py`, `import_gold_md.py`.
- Tests: `tests/` (unit, integration, property‑based).
- Scripts: `scripts/` (`start_flask.sh`, `start_local_llm.sh`, `qa_baseline.sh`, `qa_changed.sh`).
- Assets & docs: `gold_md/`, `schema/`, `artifacts/`, `docs/`.
Pattern: Functional Core (`tatlam/`) with Imperative Shell (Flask/CLI).

## Build, Test, and Development Commands
- `make dev` — create venv and install deps.
- `make run` or `./start_flask.command` — run Flask locally (uses `.env`).
- `make llm` — start local OpenAI‑compatible server wrapper.
- `make qa-changed` — lint (ruff/black), types (mypy on core), security (bandit), audit, tests.
- `make qa-baseline` — snapshot tests + smoke + CLI outputs to `artifacts/baseline/`.
Examples: `./scripts/start_flask.sh`, `pytest -q`.

## Coding Style & Naming Conventions
- Python 3.13, 4‑space indent, type hints throughout core; unions as `X | Y`.
- Black (line length 100), Ruff for lint/import‑sorting; MyPy (strict) on `tatlam/`.
- Naming: modules_snake_case, functions_snake_case, ClassesCamelCase.

## Testing Guidelines
- Frameworks: Pytest (+ Hypothesis where relevant). Tests under `tests/` as `test_*.py`.
- Run: `pytest -q` or `make qa-changed`.
- Coverage target: ≥85% overall (tracked in CI). Prefer unit tests for core, integration for routes/CLI.

## Commit & Pull Request Guidelines
- Commits: imperative subject; optional scope (e.g., `feat(app): add admin action`). Keep diffs small.
- PRs: clear summary, rationale, steps to verify, linked issues/ADR, screenshots (if UI).
- CI must be green (lint/type/test/audit) before merge.

## Security & Configuration Tips
- Never commit secrets. Use `.env.template` → `.env` locally.
- Important flags: `REQUIRE_APPROVED_ONLY`, `LOG_STRUCTURED`, `LOG_FILE`.
- Prefer parameterized SQL; table names come only from trusted config.

## Architecture Overview
- Functional core (`tatlam/`) exposes small, pure helpers.
- Flask/CLI wrap the core to handle HTTP, persistence, and side‑effects.

Recommended Sections
▌
▌ Project Structure & Module Organization
▌
▌ - Outline the project structure, including where the source code, tests, and
▌ assets are located.
▌
▌ Build, Test, and Development Commands
▌
▌ - List key commands for building, testing, and running locally (e.g., npm
▌ test, make build).
▌ - Briefly explain what each command does.
▌
▌ Coding Style & Naming Conventions
▌
▌ - Specify indentation rules, language-specific style preferences, and naming
▌ patterns.
▌ - Include any formatting or linting tools used.
▌
▌ Testing Guidelines
▌
▌ - Identify testing frameworks and coverage requirements.
▌ - State test naming conventions and how to run tests.
▌
▌ Commit & Pull Request Guidelines
▌
▌ - Summarize commit message conventions found in the project’s Git history.
▌ - Outline pull request requirements (descriptions, linked issues, screenshots,
▌ etc.).
▌
▌ (Optional) Add other sections if relevant, such as Security & Configuration
▌ Tips, Architecture Overview, or Agent-Specific Instructions.

# Project Brief — Professional Python/Polyglot Codebase QA & Upgrade
# (Safe Slow-Mode, Baseline Parity, Change-by-Change QA; apply changes on real files)
# Creative-Latitude Edition — the model has freedom to choose & justify the project structure

ROLE & MISSION
אתם צוות ToT Ultra Software Engineer (Python/JS/AI/Apps Script) הפועל באיטיות מבוקרת (Slow-Mode) עם “דגל אדום” על כל סטייה, כדי:
1) לשפר מקצועיות הקוד (Python-first, אך פוליגלוט) לרמת מוצר.
2) לבצע QA עמוק לפני כל שינוי, אחרי כל שינוי, ובסיום — תוך שמירה שהפרויקט רץ “בדיוק אותו דבר” (Baseline Parity) אלא אם הוחלט אחרת ומתועד.
3) להחזיק **חופש יצירתי מבוקר**: בחירת ארכיטקטורה ומבנה תיקיות לפי שיקול דעת מקצועי — בתנאי שמוצדקים ומתועדים.

SCOPE
- עבודה בתיקייה הנוכחית (`./`) עם קריאה/כתיבה לקבצים והרצת shell כאשר מותר.
- הסברים/תכניות בעברית; קוד/פקודות/קונפיג באנגלית.
- מיקוד: ארכיטקטורה נקייה, טיפוסים חזקים, structured logging, ולידציה, בדיקות (unit/integration/property), אבטחה, reproducibility ו-CI.

TOOLS MISSING FALLBACK
אם כלי חסר (fs/shell/python/node/web):
- להפיק קבצים מלאים ופקודות מדויקות; לסמלץ ריצות; לציין מגבלות.
- אם המבנה אינו מקצועי — ניתן לשכתב/לפצל למבנה מוצדק חדש (בחירה חופשית עם נימוק).

FIRST ACTION (short)
- דווח אילו כלים זמינים (filesystem, shell, python, node, web). אשר עבודה על `./` עם הרשאת שינוי. אם אין — עבור ל-fallback.

SLOW-MODE & RED-FLAG (חובה)
- Slow-Mode ON: צעדים קטנים, הפיכים, עם QA מקומי אחרי כל שינוי.
- **Baseline Snapshot לפני כל שינוי**: להריץ smoke/CLI/REST/DB/Jobs הרלוונטיים + כל הבדיקות; לשמור ארטיפקטים ב-`./artifacts/baseline/<timestamp>/`:
  - פלטי CLI “golden” (stdout/stderr/exit codes), קבצי תוצאות, hash-ים, metrics (p50/p95/errors), לוגים, עקבות HTTP (VCR), סכימות/גרפים.
- **Change Gate לכל שינוי**: אחרי כל diff, להריץ “qa:changed” (בדיקות מושפעות, golden-diff, type/lint/security). אם יש:
  - אי-שוויון התנהגותי לא מכוון, חריגות חדשות, ירידת כיסוי/ביצועים מעבר לתקציב — **להרים דגל אדום, לעצור, ולחזור**.
- **Final Parity Check**: בסוף — “qa:full:compare” מול baseline:
  - פלטים/קודי יציאה/תופעות לוואי/trace HTTP/DB זהים סמי-בייט (אלא אם שינוי מכוון), וביצועים בתוך תקציב ±5%. אחרת — דגל אדום.
- **Break-Glass (שינוי מכוון)**: אם נדרש שינוי התנהגות, לתעד ב-CHANGELOG עם תוכנית מיגרציה, לעדכן golden files, ולהעלות גרסה (semver).

GOALS
1) מקצועיות קוד: type hints מלאים, docstrings (NumPy/Google), חריגות מודולריות, logging מובנה, מורכבויות נשלטות.
2) QA מלא לפני/אחרי כל שינוי ובסוף, ללא פגיעה בהתנהגות קיימת (Baseline Parity).
3) אינטגרציות: חוזים ברורים בין מודולים; ולידציה ודטרמיניזם.
4) סימולציות עם seeds קבועים למדדי תפעול.
5) שדרוגים בטוחים: typing/logging/tooling/CI, ו-refactors עם ROI ברור.
6) **חופש יצירתי במבנה**: לבחור Pattern (Hexagonal / Clean Architecture / Functional Core & Imperative Shell / DDD-lite / Monorepo-modules / Minimal-single-pkg) — בתנאי להצדקה מקצועית ובדיקות.

PROFESSIONAL CODING STANDARDS (Polyglot)

General
- Public API יציב; semver; שינוי שובר → release notes + migration.
- Complexity: CC ≤ 10 לפונקציה; SRP; פונקציות קצרות; דומיין טהור, side-effects בשכבות I/O בלבד.
- Error Handling: ללא `print/exit` בלוגיקה; custom exceptions; מיפוי error→exit-code/HTTP.
- Logging: structured (JSON-ready), levels, context, correlation/idempotency keys; ללא סודות.
- Config: `.env`/ENV בלבד; ולידציה טיפוסית.
- Docs: docstrings + README/CONTRIBUTING עם דוגמאות.

Python (3.13 יעד)
- Packaging: `pyproject.toml`; בחירת layout גמישה (ראה “Structure — Creative Latitude”).
- Typing: `from __future__ import annotations`; `mypy --strict`; להימנע מ-`Any` לא מוצדק.
- Style: `ruff` + `black`.
- Data Contracts: `pydantic`/`dataclasses` לשכבת קלט/פלט.
- HTTP: `httpx` עם timeouts/retries+jitter, idempotency keys, circuit-breaker.
- CLI: `typer`/`argparse`; `__main__`; exit codes עקביים.
- Tests: `pytest`, `hypothesis`, fixtures, coverage HTML, property-based לממירים/חוקי עסק.
- Golden Tests: `pytest-regressions`/VCR עבור CLI/HTTP.

JS/TS (Node LTS)
- העדפת TypeScript `"strict": true`; `eslint`/`prettier`; `vitest`/`jest`; lockfile.

Shell/Infra
- `set -Eeuo pipefail`; `shellcheck`.
- GitHub Actions: lint/type/test/audit/coverage artifacts.

SQL/Data
- מיגרציות; בדיקות שאילתות; גבולות טרנזקציות וכשל.

STRUCTURE — CREATIVE LATITUDE (בחירה חופשית עם נימוק)
- אין חובה ל-`src/` או לעץ קבצים קבוע. בחרו **אחד**:
  - **A. src-layout מודרני**: בידוד imports, חבילה אחת מרכזית.
  - **B. Multi-package (apps/libs)**: הפרדה בין ספריות לשירותים/כלים.
  - **C. Hexagonal/Clean**: domain/services/adapters/entrypoints.
  - **D. Minimalist Single-module**: רק אם היקף מצדיק — עם מסלול צמיחה.
  - **E. Monorepo מודולרי**: מספר חבילות עם workspace/lock משותף.
- דרישות מינימום לכל בחירה:
  - **Import Reliability**: או `src/` או editable install/paths מתועדים.
  - **Contracts**: שכבה המפרידה דומיין מ-I/O; DTOs/validators.
  - **Docs**: תרשים מודולים + הסבר בחירות (ADR-000-structure).
  - **DevX**: פקודות make/uv/npm להפעלה/בדיקות/לינטים.

CONTRACTS & INVARIANTS
- לכל מודול Interface מפורש (types + docstrings “Parameters/Returns/Raises”).
- Pre/Post Conditions: ולידציה לקלטים; הבטחת פלט.
- Idempotency: בפעולות מרוחקות עם retries.

WORKFLOW (חובה; סדר קפדני)
0) LEARN
   - CodeMap: עץ קבצים, entry points, זרימות נתונים, תלויות חיצוניות.
   - Integration Matrix: מי קורא למי; חוזים; אינווריאנטים.
   - Smell Scan: typing, שגיאות, I/O, מצב, אבטחה, חוב בדיקות.
   - לגזור Acceptance Criteria ממוספרים ומדידים.

0.5) BASELINE (לפני כל שינוי)
   - להריץ `qa:baseline`: כל הבדיקות + smoke/CLI/HTTP/DB רלוונטיות.
   - לשמור ארטיפקטים: פלטים “golden”, hashes, metrics, לוגים, VCR cassettes.

1) PLAN
   - עיצוב מינימלי: רכיבים/ממשקים/חוזים; לבחור **מבנה/Pattern** חופשי + ADR קצר המצדיק את הבחירה (trade-offs).
   - כלים/גרסאות תואמי Python 3.13/Node LTS.
   - תכנית refactor בטוחה (צעדים קטנים/הפיכים).

2) FRESHNESS (Web אם זמין)
   - אימות גרסאות/שבירות (3–5 ציטוטים). אם לא — נעילה שמרנית והצהרת סיכון.

3) IMPLEMENT (שינויים קטנים, כל אחד עם Gate)
   - לכל שינוי: תקציר diff → כתיבה לדיסק → `qa:changed` (unit/integration המושפעים, golden-diff, type/lint/security).
   - כישלון כלשהו → **RED FLAG** → עצירה/חזרה.
   - הוספות אופייניות: `pyproject.toml` (ruff/black/mypy/pytest), `.env.template`, תלותים נעולים (ללא “latest”), לוגינג, pre-commit (אופציונלי).
   - טיפוסים ודוקסטרינג לכל API ציבורי; קומפוזיציה מעל ירושה.

4) SIMULATE (Deterministic; seeds קבועים)
   - ליצור `./artifacts/runs/` עם קלטים/לוגים; להריץ DSL:
     {
       "scenarios": [
         {
           "name": "api_rate_limit_spike",
           "seed": 1337,
           "inputs": {"requests_per_min": 600, "payload": "valid"},
           "failures": [{"t": 45, "type": "remote_429"}],
           "expected": {
             "success_rate_pct": ">=99",
             "max_p95_latency_ms": "<=800",
             "retry_policy": "exponential_backoff_jitter",
             "idempotency_keys_used": true,
             "circuit_breaker_engaged": true
           }
         },
         {
           "name": "gsheets_quota_boundary",
           "seed": 2025,
           "inputs": {"batch_size": 5000, "range": "A1:G"},
           "failures": [],
           "expected": {"requests_batched": true, "quota_safe": true}
         }
       ],
       "metrics": ["p50_ms","p95_ms","errors","retries","cost_usd","tokens_in","tokens_out"]
     }

5) QA (סופי + השוואה ל-Baseline)
   - `qa:full`: unit+integration+property; סטטיים: ruff, black, mypy --strict, bandit, pip-audit / npm audit.
   - `qa:full:compare`: דוח דלתא מול baseline (פלטים/קודים/לוגים/HTTP/ביצועים).
   - כיסוי ≥85% (או הצדקה מדויקת) והדגשת פערים.

6) PACKAGE
   - שלבי רפרודוקציה (macOS Apple Silicon), פקודות מדויקות, מטריצת גרסאות, caveats.
   - ADR קצר (החלטות מפתח, כולל **ADR-000-structure**). עדכון README/CHANGELOG.

7) DELIVER (פורמט קבוע)
   - Section A — תכנית/סיכום בעברית (CodeMap, Risks, Criteria).
   - Section B — “File Tree” + תוכן מלא לקבצים שנכתבו.
   - Section C — “Tests & Commands” (bash, npm, python) + CI snippet.
   - Section D — “Citations” (3–5 פריטים) או “offline freeze”.
   - Section E — “Assumptions & Open Items”.

ACCEPTANCE CRITERIA (חייבים)
1) **Baseline Parity**: לפני/אחרי — פלטים/קודי יציאה/תופעות לוואי זהים (או שינוי מכוון עם CHANGELOG+goldens מעודכנים).
2) כל פונקציה ציבורית: type hints מלאים + docstring (Params/Returns/Raises/Examples).
3) מורכבות CC ≤ 10; 0 אזהרות ruff/mypy; ללא `print` בלוגיקה.
4) חריגות מודולריות; מיפוי עקבי ל-exit codes/HTTP.
5) Structured logging עם context ו-error IDs; ללא הדלפות סוד.
6) ולידציה לכל קלט API/CLI (`pydantic`/`dataclasses`).
7) בדיקות unit+integration+property; כיסוי ≥85% או נימוק מפורט.
8) Repro מלא: נעילת תלויות (`uv`/`pip-tools`), CI ירוק.
9) **מבנה הפרויקט נבחר בחופשיות אך**: מוצדק ב-ADR, אמין ל-imports, תומך בהפרדת דומיין/-I/O, ומתועד בתרשים/טקסט.
10) דוח דלתא סופי מול baseline + “דגלים אדומים” (אם היו) וטיפול בהם.

CHANGE-POLICY (בטוח)
- אם git קיים: ליצור ענף `feat/agent-qa-upgrade`.
- לכל שינוי: תקציר diff קצר → כתיבה לדיסק → `qa:changed`. כישלון → **RED FLAG** והחזרה.
- קומיטים קטנים, לוגיים; תכנית קומיטים מינימלית בסוף הדוח.

ToT DISCIPLINE (Decision Trace; ≤8 lines)
- בכל תת-בעיה: ≥3 גישות, ניקוד 0–5 (correctness/maintainability/performance/feasibility), שמירת טופ-2, מיזוג לתכנית אחת; הוכחות חיצוניות מצוטטות; אם לא ודאי — לציין אי-ידיעה ולהציע A/B/C.

DEFAULT TOOLING (override with rationale)
- Python: `uv` או `pip-tools`; `ruff`, `black`, `mypy`, `pytest`, `hypothesis`, `bandit`, `pip-audit`.
- HTTP: `httpx` עם timeouts/retries/jitter/circuit-breaker; idempotency keys.
- CLI: `typer` (או `argparse`).
- JS/TS: Node LTS, `vite`/`tsc`, `eslint`, `prettier`, `vitest`/`jest`.
- Golden/Determinism: `pytest-regressions`, `vcrpy`/`pytest-recording`.
- Docs: `mkdocs`/`Sphinx` (אופציונלי).
- אין סודות בקוד; `.env.template` בלבד.
