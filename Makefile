.PHONY: help install lint format typecheck test check clean

help:
	@echo "install    Install dependencies from the lockfile"
	@echo "lint       Run ruff linting and format checking"
	@echo "format     Apply ruff formatting and safe fixes"
	@echo "typecheck  Run mypy in strict mode"
	@echo "test       Run the test suite with coverage"
	@echo "check      Run lint, typecheck and test"
	@echo "clean      Remove tool caches and build artefacts"

install:
	poetry install

lint:
	poetry run ruff check src tests jobs
	poetry run ruff format --check src tests jobs

format:
	poetry run ruff check --fix src tests jobs
	poetry run ruff format src tests jobs

typecheck:
	poetry run mypy

test:
	poetry run pytest --cov=player_availability --cov-report=term-missing

check: lint typecheck test

clean:
	rm -rf .mypy_cache .ruff_cache .pytest_cache .coverage htmlcov dist
	find . -type d -name __pycache__ -not -path "./.venv/*" -exec rm -rf {} +
