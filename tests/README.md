# TATLAM Test Suite Documentation

## Overview
Comprehensive pytest suite for the TATLAM QA scenario generation system.

## Structure

```
tests/
├── conftest.py              # Global fixtures (mock_brain, in_memory_db)
│
├── unit/                    # Fast, isolated tests (no I/O)
│   ├── test_validators.py
│   ├── test_categories.py
│   ├── test_doctrine.py
│   ├── test_brain_mock.py
│   ├── test_utils.py
│   └── test_render_cards.py
│
├── integration/             # Database and multi-component tests
│   ├── infra/
│   │   ├── test_db_schema.py
│   │   ├── test_repo_crud.py
│   │   └── test_migrations.py
│   └── core/
│       ├── test_bundle_flow.py
│       └── test_export.py
│
├── llm_evals/              # LLM quality tests (expensive)
│   ├── test_prompt_injection.py
│   ├── test_hebrew_quality.py
│   ├── test_json_robustness.py
│   └── test_hallucinations.py
│
├── security/               # Security and vulnerability tests
│   ├── test_secrets.py
│   └── test_sql_injection.py
│
└── performance/            # Performance and benchmark tests
    ├── test_db_lock.py
    └── benchmark_generation.py
```

## Installation

```bash
# Install test dependencies
pip install -r requirements-test.txt
```

## Running Tests

### Run All Tests
```bash
pytest
```

### Run Specific Test Categories
```bash
# Unit tests only (fast)
pytest tests/unit/ -m unit

# Integration tests
pytest tests/integration/ -m integration

# Exclude slow tests (LLM evals)
pytest -m "not slow"

# Run only slow tests (requires API keys)
pytest -m slow
```

### Run Specific Test Files
```bash
# Test categories
pytest tests/unit/test_categories.py -v

# Test database schema
pytest tests/integration/infra/test_db_schema.py -v

# Test SQL injection prevention
pytest tests/security/test_sql_injection.py -v
```

### Coverage Report
```bash
# Generate HTML coverage report
pytest --cov=tatlam --cov-report=html

# Open coverage report
open htmlcov/index.html
```

### Parallel Execution
```bash
# Run tests in parallel (faster)
pytest -n auto
```

## Test Markers

Tests are marked with the following markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests (database access)
- `@pytest.mark.slow` - Expensive tests (real API calls)

## Global Fixtures

### `in_memory_db`
Provides an isolated SQLite database for testing.

```python
def test_database_operation(in_memory_db):
    # Use in_memory_db for database tests
    cursor = in_memory_db.cursor()
    cursor.execute("SELECT * FROM scenarios")
```

### `mock_brain`
Provides a mocked TrinityBrain instance (no real API calls).

```python
def test_brain_function(mock_brain):
    # Use mock_brain for testing without API calls
    assert mock_brain.writer_client is not None
```

### `sample_scenario_data`
Provides a valid scenario dictionary for testing.

```python
def test_scenario_processing(sample_scenario_data):
    # Use sample_scenario_data as test input
    assert sample_scenario_data["title"] is not None
```

## Writing New Tests

### Unit Test Example
```python
import pytest
from tatlam.core.categories import CATS

@pytest.mark.unit
class TestCategories:
    def test_cats_exist(self):
        assert len(CATS) > 0
```

### Integration Test Example
```python
import pytest
from tatlam.infra.repo import insert_scenario

@pytest.mark.integration
class TestRepository:
    def test_insert(self, in_memory_db):
        scenario_id = insert_scenario({"title": "Test"})
        assert scenario_id is not None
```

### LLM Evaluation Test Example (Expensive)
```python
import pytest

@pytest.mark.slow
@pytest.mark.skipif(True, reason="Requires API keys")
class TestLLMQuality:
    def test_hebrew_quality(self, mock_brain):
        # Test with real API in production
        pass
```

## Test Organization Principles

1. **Unit Tests**: No I/O, no network, no database. Pure logic testing.
2. **Integration Tests**: Test component interactions, use `in_memory_db`.
3. **LLM Evals**: Expensive, require API keys, marked as `@slow`.
4. **Security Tests**: Static analysis, injection prevention.
5. **Performance Tests**: Benchmarks, concurrency tests.

## Continuous Integration

### Pre-commit Hook
```bash
# Run fast tests before commit
pytest tests/unit/ -m unit
```

### CI Pipeline
```yaml
# Run full test suite (excluding slow tests)
pytest -m "not slow" --cov=tatlam
```

## Troubleshooting

### ModuleNotFoundError
```bash
# Ensure TATLAM package is in PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### Database Locked Errors
The `in_memory_db` fixture uses a temporary database. If you encounter locking issues, ensure tests properly close connections.

### API Key Required
LLM evaluation tests require API keys. Set environment variables:
```bash
export ANTHROPIC_API_KEY="your-key"
export GOOGLE_API_KEY="your-key"
export OPENAI_API_KEY="your-key"
```

Or create `.env` file:
```
ANTHROPIC_API_KEY=your-key
GOOGLE_API_KEY=your-key
OPENAI_API_KEY=your-key
```

## Coverage Goals

- **Overall**: 80%+ code coverage
- **Unit Tests**: 90%+ coverage of core logic
- **Integration Tests**: Cover all database operations
- **Security Tests**: Cover all input validation

## Contributing

When adding new functionality:

1. Write unit tests first (TDD)
2. Add integration tests for database/file operations
3. Add security tests for user input handling
4. Update this README if adding new test categories

## Performance Baselines

### Unit Tests
- Should complete in < 5 seconds

### Integration Tests
- Should complete in < 30 seconds

### Full Suite (excluding slow tests)
- Should complete in < 60 seconds

## Contact

For questions about the test suite, consult the QA Lead or review the test files directly.
