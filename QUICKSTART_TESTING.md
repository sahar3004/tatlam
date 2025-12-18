# TATLAM Testing Quick Start Guide

## 5-Minute Setup

### Step 1: Install Dependencies
```bash
pip install -r requirements-test.txt
```

### Step 2: Run Tests
```bash
# Option A: Use the test runner script
./run_tests.sh

# Option B: Use pytest directly
pytest tests/ -m "not slow" -v
```

### Step 3: View Results
Tests should complete in under 60 seconds (excluding slow LLM tests).

## Common Commands

### Fast Development Workflow
```bash
# Run only unit tests (< 5 seconds)
./run_tests.sh unit

# Run with coverage
./run_tests.sh coverage
```

### Before Committing
```bash
# Run fast tests (unit + integration)
./run_tests.sh fast
```

### Full Validation
```bash
# Run all tests except expensive LLM evals
./run_tests.sh all
```

## Test Output Example

```
========================================
TATLAM Test Suite
========================================

Running: Unit Tests
Command: pytest tests/unit/ -v -m unit

tests/unit/test_categories.py::TestCategories::test_cats_dictionary_exists PASSED
tests/unit/test_categories.py::TestCategories::test_cats_keys_are_hebrew PASSED
tests/unit/test_validators.py::TestValidators::test_validate_json_schema PASSED
...

✓ Unit Tests PASSED

Running: Integration Tests
...
```

## Troubleshooting

### "pytest: command not found"
```bash
pip install pytest
# or
pip install -r requirements-test.txt
```

### "ModuleNotFoundError: No module named 'tatlam'"
```bash
# Ensure you're in the project root
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

### "Database is locked"
Tests use in-memory databases. This error indicates a test didn't clean up properly.
Run tests individually to identify the culprit:
```bash
pytest tests/integration/infra/test_db_schema.py -v
```

## What Gets Tested

✅ **Unit Tests**: Core logic (validators, categories, utilities)
✅ **Integration Tests**: Database operations, bundling, exports
✅ **Security Tests**: SQL injection, secrets management
✅ **Performance Tests**: Concurrency, benchmarks

❌ **LLM Evals** (Skipped by default - requires API keys)

## File Structure Quick Reference

```
tests/
├── conftest.py          # Fixtures: in_memory_db, mock_brain
├── unit/                # Fast isolated tests
├── integration/         # Database + component tests
├── security/            # Security validation
├── performance/         # Benchmarks
└── llm_evals/          # LLM quality (expensive)
```

## Next Steps

1. ✅ Tests are installed and ready
2. 📊 Run `./run_tests.sh coverage` to see coverage report
3. 📝 Read `tests/README.md` for detailed documentation
4. 🚀 Enable LLM eval tests when you have API keys configured

## Quick Tips

- **Fast feedback**: Run `./run_tests.sh unit` during development
- **Before push**: Run `./run_tests.sh fast` to catch issues
- **CI/CD**: Use `./run_tests.sh ci` in pipelines
- **Deep dive**: Use `./run_tests.sh coverage` to find gaps

## Success Criteria

After running `./run_tests.sh`:
- All unit tests pass ✅
- All integration tests pass ✅
- All security tests pass ✅
- Total execution time < 60 seconds ✅

## Help

For detailed information:
- 📖 See `tests/README.md`
- 📋 See `TEST_SUITE_SUMMARY.md`
- 💻 Run `./run_tests.sh help`

Happy testing! 🎉
