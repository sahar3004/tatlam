PY := .venv/bin/python
PIP := .venv/bin/pip
PYTEST := .venv/bin/pytest

.PHONY: venv install dev qa-baseline qa-changed lint test mypy bandit audit run flask llm

venv:
	@python3 -m venv .venv
	@$(PIP) install --upgrade pip

install: venv
	@$(PIP) install -r requirements.txt

dev: install
	@$(PIP) install -r requirements-dev.txt

lint:
	@ruff check .
	@black --check .

test:
	@$(PYTEST)

mypy:
	@mypy --strict .

bandit:
	@bandit -r .

audit:
	@pip-audit -r requirements.txt

qa-baseline:
	@bash scripts/qa_baseline.sh

qa-changed:
	@bash scripts/qa_changed.sh

run:
	@bash scripts/start_flask.sh

flask:
	@bash scripts/start_flask.sh

llm:
	@bash scripts/start_local_llm.sh

