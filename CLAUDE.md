# Project Context: Tatlam

> Hebrew security scenario generation system. Trinity AI architecture (Writer→Judge→Simulator).

## 1. Commands

```bash
# Env
source .venv/bin/activate

# Install
pip install -r requirements.txt          # prod
pip install -r requirements-dev.txt      # dev
pip install -e .                         # editable (enables CLI)

# Run
streamlit run main_ui.py                 # Primary UI
python run_batch.py --category "חפץ חשוד ומטען" --async

# Test
pytest -m "not slow" -v                  # fast tests
pytest tests/unit/                       # unit only
pytest --cov=tatlam --cov-report=html    # coverage

# Lint/Type
ruff check . && black --check .          # lint
mypy --strict tatlam/                    # type check
bandit -r tatlam/                        # security
make qa-changed                          # all checks

# CLI (after pip install -e .)
tatlam-export-json --category "X" --out out.json
tatlam-render-cards --category "X" --out ./cards/
tatlam-sim payload.json --out results.json
```

## 2. Architecture

```
tatlam/
├── settings.py      # Pydantic config (SINGLE SOURCE OF TRUTH)
├── core/            # Pure logic (NO I/O) ← NEVER import infra here
│   ├── brain.py     # TrinityBrain orchestration
│   ├── llm_factory.py  # Client protocols + DI
│   ├── categories.py   # Hebrew normalization
│   └── validators.py
├── infra/           # I/O layer
│   ├── db.py        # SQLAlchemy engine (WAL mode)
│   ├── models.py    # Scenario ORM
│   └── repo.py      # CRUD
├── cli/             # Entry points
└── sim/             # Simulation engine

tests/
├── conftest.py      # Fixtures: in_memory_db, mock_brain
├── unit/            # Fast, isolated
├── integration/     # DB tests
├── llm_evals/       # @pytest.mark.slow
└── security/        # Injection tests
```

**Stack:** Python 3.9+ | SQLite+WAL | SQLAlchemy 2.0 | Pydantic 2.0 | Streamlit | Tenacity | Structlog

**AI:** Claude (Writer) → Gemini (Judge) → Local LLM/llama.cpp (Simulator)

## 3. Coding Standards

| Rule | Spec |
|------|------|
| Types | `from __future__ import annotations` + `mypy --strict` |
| Imports | `ruff` isort, `tatlam` as first-party |
| Format | `black` line-length=100 |
| Docstrings | Google/NumPy style, public APIs only |
| Errors | Custom exceptions in `core/brain.py` → map to exit codes |
| Logging | `logging.getLogger(__name__)` + structlog context |
| Tests | Fixtures from `conftest.py`, mark slow with `@pytest.mark.slow` |
| Coverage | ≥85% or documented exception |

**Naming:** `snake_case` functions, `PascalCase` classes, `SCREAMING_SNAKE` constants

**Never:**
- Import `infra/` in `core/` (except `interfaces.py`)
- Hardcode secrets (use `.env`)
- Use `print()` in business logic
- Skip type hints on public APIs

## 4. Key Patterns

```python
# Config access
from tatlam.settings import get_settings
settings = get_settings()

# Trinity Brain
from tatlam.core.brain import TrinityBrain
brain = TrinityBrain()  # auto-init
brain = TrinityBrain(writer_client=mock, auto_initialize=False)  # testing

# Categories (Hebrew normalization)
from tatlam.core.categories import category_to_slug, CATS
slug = category_to_slug("חפץ חשוד ומטען")  # → "chefetz-chashud"

# Database
from tatlam.infra.db import get_session
from tatlam.infra.models import Scenario
with get_session() as session:
    rows = session.scalars(select(Scenario)).all()
    data = rows[0].to_dict()  # parses JSON fields
```

## 5. Categories (Valid Slugs)

| Slug | Hebrew |
|------|--------|
| `piguim-peshutim` | פיגועים פשוטים |
| `ezrahi-murkav` | אזרחי מורכב |
| `hadira-razishim` | חדירה לחדרים רגישים |
| `tachanot-iliyot` | תחנות עיליות |
| `iyumim-tech` | איומים טכנולוגיים |
| `eiroa-kimi` | אירוע כימי |
| `bnei-aruba` | בני ערובה |
| `chefetz-chashud` | חפץ חשוד ומטען |
| `uncategorized` | לא מסווג |

## 6. Database Schema

**Table: `scenarios`** (SQLite + WAL)

| Column | Type | Index |
|--------|------|-------|
| id | INTEGER PK | - |
| title | TEXT UNIQUE | - |
| category | TEXT | ✓ |
| threat_level | TEXT | ✓ |
| status | TEXT | ✓ |
| steps | TEXT (JSON) | - |
| created_at | TEXT (ISO) | ✓ |

JSON fields: `steps`, `required_response`, `debrief_points`, `comms`, `decision_points`, `escalation_conditions`, `lessons_learned`, `variations`, `validation`

## 7. Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=       # Writer
GOOGLE_API_KEY=          # Judge

# Database
DB_PATH=db/tatlam.db

# Models
WRITER_MODEL_NAME=claude-sonnet-4-20250514
JUDGE_MODEL_NAME=gemini-2.0-flash
LOCAL_MODEL=qwen-2.5-32b-instruct
LOCAL_BASE_URL=http://127.0.0.1:8000/v1
```

## 8. Test Fixtures

```python
def test_db(in_memory_db):       # isolated SQLite
    ...

def test_ai(mock_brain):         # no API calls
    ...

@pytest.mark.slow
def test_real_api():             # skipped by default
    ...
```

## 9. Common Tasks

**Add category:** `tatlam/core/categories.py` → add to `CATS` dict + aliases

**Add endpoint:** `main_ui.py` → use DI for brain, Pydantic validation

**Schema change:** `tatlam/infra/models.py` → update `to_dict()` if JSON field

**Clear settings cache:** `get_settings.cache_clear()`

**Reset DB engine:** `from tatlam.infra.db import reset_engine; reset_engine()`

## 10. Troubleshooting

```bash
# Apple Silicon Metal GPU
CMAKE_ARGS="-DGGML_METAL=on" pip install --force-reinstall llama-cpp-python

# Verify Metal
python scripts/verify_metal.py
```

## 11. File Quick Reference

| Need | File |
|------|------|
| Config | `tatlam/settings.py` |
| AI | `tatlam/core/brain.py` |
| ORM | `tatlam/infra/models.py` |
| CRUD | `tatlam/infra/repo.py` |
| Hebrew | `tatlam/core/categories.py` |
| Fixtures | `tests/conftest.py` |
| UI | `main_ui.py` |
| Batch | `run_batch.py` |
