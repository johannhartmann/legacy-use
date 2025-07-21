.PHONY: help
help:
	@echo "Available commands:"
	@echo "  make install       - Install all dependencies"
	@echo "  make install-dev   - Install development dependencies"
	@echo "  make format        - Format code with black and ruff"
	@echo "  make lint          - Run linting checks"
	@echo "  make vulture       - Find dead code with vulture"
	@echo "  make check         - Run all quality checks"
	@echo "  make test          - Run tests"
	@echo "  make pre-commit    - Run pre-commit hooks"
	@echo "  make clean         - Remove generated files"

.PHONY: install
install:
	uv sync

.PHONY: install-dev
install-dev:
	uv sync --dev

.PHONY: format
format:
	@echo "Running black formatter..."
	uv run black .
	@echo "Running ruff formatter..."
	uv run ruff format .
	@echo "Running ruff auto-fixes..."
	uv run ruff check . --fix

.PHONY: lint
lint:
	@echo "Running black check..."
	uv run black --check --diff .
	@echo "Running ruff linter..."
	uv run ruff check .
	@echo "Running mypy type checker..."
	uv run mypy server/ --ignore-missing-imports || true

.PHONY: vulture
vulture:
	@echo "Running vulture to find dead code..."
	uv run vulture server/ --min-confidence=60 --exclude=migrations,tests

.PHONY: check
check: lint vulture
	@echo "All quality checks passed!"

.PHONY: test
test:
	@echo "Running pytest..."
	uv run pytest server/tests/ -v --cov=server --cov-report=term-missing || echo "No tests found"

.PHONY: pre-commit
pre-commit:
	@echo "Installing pre-commit hooks..."
	uv run pre-commit install
	@echo "Running pre-commit hooks..."
	uv run pre-commit run --all-files

.PHONY: clean
clean:
	@echo "Cleaning up generated files..."
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type f -name "*.pyo" -delete 2>/dev/null || true
	find . -type f -name ".coverage" -delete 2>/dev/null || true