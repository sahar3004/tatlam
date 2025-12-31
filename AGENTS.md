# AGENTS.md — Tatlam Project

> Hebrew security scenario generation system using Trinity AI architecture (Writer→Judge→Simulator).

## Stack
- **Core**: Python 3.9+ | SQLite+WAL | Pydantic 2.0 | SQLAlchemy 2.0
- **UI**: Streamlit
- **AI**: Claude (Writer) → Gemini (Judge) → Local LLM/llama.cpp (Simulator)

## Commands

| Action | Command |
|--------|---------|
| Install | `pip install -e .` |
| Test (fast) | `pytest -m "not slow" -v` |
| Test (unit) | `pytest tests/unit/` |
| Coverage | `pytest --cov=tatlam --cov-report=html` |
| Lint | `ruff check . && black --check .` |
| Type check | `mypy --strict tatlam/` |
| Security | `bandit -r tatlam/` |
| All QA | `make qa-changed` |
| Run UI | `streamlit run main_ui.py` |
| Run batch | `python run_batch.py --category "חפץ חשוד ומטען" --async` |

## Project Structure

```
tatlam/
├── settings.py      # Pydantic config (SINGLE SOURCE OF TRUTH)
├── core/            # Pure logic (NO I/O) ← NEVER import infra here
│   ├── brain.py     # TrinityBrain orchestration
│   ├── llm_factory.py  # Client protocols + DI
│   └── categories.py   # Hebrew normalization
├── infra/           # I/O layer
│   ├── db.py        # SQLAlchemy engine (WAL mode)
│   ├── models.py    # Scenario ORM
│   └── repo.py      # CRUD
└── cli/             # Entry points

tests/
├── conftest.py      # Fixtures: in_memory_db, mock_brain
├── unit/            # Fast, isolated
├── integration/     # DB tests
└── llm_evals/       # @pytest.mark.slow
```

## Code Style

| Rule | Spec |
|------|------|
| Types | `from __future__ import annotations` + `mypy --strict` |
| Format | `black` line-length=100, `ruff` for linting |
| Docstrings | Google/NumPy style, public APIs only |
| Naming | `snake_case` functions, `PascalCase` classes, `SCREAMING_SNAKE` constants |
| Logging | `logging.getLogger(__name__)` + structlog context |
| Coverage | ≥85% or documented exception |

## Key Patterns

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
with get_session() as session:
    rows = session.scalars(select(Scenario)).all()
```

## Never Do

- Import `infra/` in `core/` (except `interfaces.py`)
- Hardcode secrets (use `.env`)
- Use `print()` in business logic
- Skip type hints on public APIs
- Commit without running `make qa-changed`

## Environment

```bash
ANTHROPIC_API_KEY=       # Writer
GOOGLE_API_KEY=          # Judge
DB_PATH=db/tatlam.db
WRITER_MODEL_NAME=claude-sonnet-4-20250514
JUDGE_MODEL_NAME=gemini-2.0-flash
LOCAL_MODEL=qwen-2.5-32b-instruct
LOCAL_BASE_URL=http://127.0.0.1:8000/v1
```

---

## ⚠️ Common Gotchas (CRITICAL)

### 1. Settings Cache
Settings are cached! After changing `.env`, call:
```python
from tatlam.settings import get_settings
get_settings.cache_clear()  # Required after env changes
```

### 2. Database Engine Cache
Tests may fail if engine isn't reset:
```python
from tatlam.infra.db import reset_engine
reset_engine()  # Call before switching DB paths
```

### 3. Trinity Brain Initialization
```python
# ❌ WRONG - will fail if API keys missing
brain = TrinityBrain()

# ✅ CORRECT - for tests without real API
brain = TrinityBrain(auto_initialize=False)
brain = TrinityBrain(writer_client=mock_client, auto_initialize=False)
```

### 4. Hebrew Categories
Always use the normalization function:
```python
# ❌ WRONG - string comparison fails
if category == "חפץ חשוד":

# ✅ CORRECT - use slug
from tatlam.core.categories import category_to_slug
slug = category_to_slug(category)
if slug == "chefetz-chashud":
```

### 5. Import Rules
```python
# ❌ NEVER do this in tatlam/core/*.py
from tatlam.infra.db import get_session

# ✅ Core must stay pure - infra imports only in entry points
```

---

## Testing Patterns

### Required Fixtures (from `tests/conftest.py`)

```python
def test_with_db(in_memory_db):
    """Use for any DB-related test."""
    pass

def test_with_brain(mock_brain):
    """Use for tests involving TrinityBrain without API calls."""
    pass

@pytest.mark.slow
def test_real_api():
    """Mark tests that hit real APIs - skipped by default."""
    pass
```

### Test File Naming
- Unit tests: `tests/unit/test_<module>.py`
- Integration tests: `tests/integration/test_<feature>.py`
- LLM evals: `tests/llm_evals/test_<eval>.py`

---

## Error Handling

### Custom Exceptions (from `tatlam.core.brain`)
```python
WriterUnavailableError   # Claude not configured
JudgeUnavailableError    # Gemini not configured
SimulatorUnavailableError  # Local LLM offline
APICallError             # API call failed after retries
```

### Configuration Errors (from `tatlam.settings`)
```python
ConfigurationError  # Missing required API keys when STRICT_API_VALIDATION=True
```

---

## Common Tasks

### Add a New Category
1. Edit `tatlam/core/categories.py`
2. Add to `CATS` dict with Hebrew name and slug
3. Add aliases if needed

### Add a New Endpoint (UI)
1. Edit `main_ui.py`
2. Use dependency injection for `TrinityBrain`
3. Validate input with Pydantic

### Modify Database Schema
1. Edit `tatlam/infra/models.py`
2. Update `to_dict()` method if JSON field
3. Add migration if production data exists

### Clear All Caches
```python
from tatlam.settings import get_settings
from tatlam.infra.db import reset_engine
get_settings.cache_clear()
reset_engine()
```
