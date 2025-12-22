# CLAUDE.md - AI Agent Guidelines for Tatlam

## Project Overview

**Tatlam** is a QA and scenario generation system for security training. It uses a "Trinity Architecture" with three AI models (Writer/Claude, Judge/Gemini, Simulator/Local Llama) to generate, validate, and simulate realistic Hebrew-language security scenarios.

## Quick Commands

```bash
# Setup
make venv && source .venv/bin/activate
make dev                    # Install all dependencies

# Running
make run                    # Start Flask server
make llm                    # Start local LLM server

# Testing
make test                   # Run unit tests (fast, <5s)
./run_tests.sh coverage     # Tests with coverage report

# Quality
make qa-changed             # Full QA: lint, types, security, tests
make lint                   # Ruff linting
make mypy                   # Type checking (strict)
```

## Architecture

```
tatlam/
├── core/          # Business logic (pure functions, no side effects)
│   ├── brain.py   # TrinityBrain AI orchestrator
│   ├── interfaces.py  # Protocol definitions
│   └── validators.py  # JSON schema validation
├── infra/         # Infrastructure (DB, I/O, side effects)
│   ├── db.py      # SQLAlchemy engine, sessions
│   ├── models.py  # ORM models (Scenario)
│   └── repo.py    # Repository pattern (CRUD)
├── cli/           # Command-line tools
└── sim/           # Simulation engine
```

**Pattern**: Functional core + imperative shell. Core functions have no side effects; infra handles I/O.

## Code Conventions

- **Python 3.9+** with full type hints
- **Formatter**: Black (line length: 100)
- **Linter**: Ruff with isort
- **Type checker**: MyPy strict mode
- **Naming**: `snake_case` for functions/variables, `CamelCase` for classes

### Key Patterns

1. **Dependency Injection**: Core classes accept optional clients for testability
2. **Pydantic Settings**: All config via `tatlam/settings.py` (env-driven)
3. **Protocol-based typing**: Interfaces defined as `Protocol` classes
4. **Context managers**: Always use `with get_session()` for DB access

### Hebrew Language Support

- UTF-8 with NFC normalization
- RTL rendering: `dir="rtl"` in HTML
- JSON: `json.dumps(..., ensure_ascii=False)`

## Testing

```
tests/
├── unit/           # Fast, isolated (no DB)
├── integration/    # Component + DB tests
├── security/       # Security-specific
├── performance/    # Benchmarks
└── llm_evals/      # API calls (marked @pytest.mark.slow)
```

Key fixtures in `conftest.py`: `in_memory_db`, `mock_brain`

## Configuration

Copy `.env.template` to `.env` and set API keys:
- `ANTHROPIC_API_KEY` - for Writer (Claude)
- `GOOGLE_API_KEY` - for Judge (Gemini)
- Local LLM runs on `http://localhost:8080`

## Important Files

- `tatlam/settings.py` - Unified Pydantic configuration
- `tatlam/core/brain.py` - Trinity AI orchestrator
- `tatlam/infra/models.py` - SQLAlchemy ORM models
- `run_batch_new.py` - Batch scenario generation entry point
