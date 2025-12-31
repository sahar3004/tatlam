# Copilot Instructions for Tatlam

## Project Context
Hebrew security scenario generation system. Trinity AI architecture (Writer→Judge→Simulator).

## Tech Stack
- Python 3.9+ with strict type hints
- SQLite with WAL mode
- Pydantic 2.0 for validation
- Streamlit for UI

## Coding Guidelines

- Always use `from __future__ import annotations`
- Use type hints on all public functions
- Follow Google/NumPy docstring format for public APIs
- Use `logging.getLogger(__name__)` for logs (never `print()`)
- Keep `core/` pure - no I/O imports from `infra/`

## Key Imports

```python
from tatlam.settings import get_settings
from tatlam.core.brain import TrinityBrain
from tatlam.core.categories import category_to_slug
from tatlam.infra.db import get_session
```

## Testing

- Use fixtures from `tests/conftest.py`: `in_memory_db`, `mock_brain`
- Mark slow tests with `@pytest.mark.slow`
- Coverage target: ≥85%
- Run tests: `pytest -m "not slow" -v`

## Error Handling

- Use custom exceptions from `core/brain.py`
- Map exceptions to appropriate exit codes
- Never use bare `except:` clauses

## Hebrew Content

- Category slugs use transliteration: `"חפץ חשוד"` → `"chefetz-chashud"`
- Normalize Hebrew input via `tatlam.core.categories`

---

## ⚠️ Critical Warnings

### Settings are CACHED
```python
# After changing .env, ALWAYS call:
get_settings.cache_clear()
```

### Database engine is CACHED
```python
# In tests, reset before switching DB:
from tatlam.infra.db import reset_engine
reset_engine()
```

### Never import infra in core
```python
# ❌ WRONG (in tatlam/core/*.py)
from tatlam.infra.db import get_session

# ✅ CORRECT - keep core pure, import infra only in entry points
```

### Trinity Brain needs mocking in tests
```python
# ❌ Will fail without API keys
brain = TrinityBrain()

# ✅ For tests
brain = TrinityBrain(auto_initialize=False)
```
