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
	@echo ""
	@echo "Kind/Kubernetes commands:"
	@echo "  make kind-setup    - Set up Kind cluster with KubeVirt and local registry"
	@echo "  make kind-teardown - Tear down Kind cluster and registry"
	@echo "  make kind-status   - Check Kind cluster and KubeVirt status"
	@echo ""
	@echo "Tilt commands:"
	@echo "  make tilt-up       - Start Tilt (development mode with auto-reload)"
	@echo "  make tilt-down     - Stop Tilt (preserves Kind cluster and VM images)"
	@echo "  make tilt-clean    - Stop Tilt and remove all resources including VM images"
	@echo "  make tilt-status   - Show Tilt status"
	@echo "  make vm-preload    - Pre-load VM container images to prevent re-downloading"
	@echo ""
	@echo "Docker commands:"
	@echo "  make build         - Build all Docker images"
	@echo "  make build-push    - Build and push images to registry"

.PHONY: install
install:
	uv sync

.PHONY: install-dev
install-dev:
	uv sync --dev

.PHONY: server-tests
server-tests:
	uv run pytest

.PHONY: setup
setup:
	touch .env.local
	uv run python generate_api_key.py

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

# Kind/Kubernetes commands
.PHONY: kind-setup
kind-setup:
	@echo "Setting up Kind cluster with KubeVirt and local registry..."
	./scripts/kind-setup.sh

.PHONY: kind-teardown
kind-teardown:
	@echo "Tearing down Kind cluster and registry..."
	./scripts/kind-teardown.sh

.PHONY: kind-status
kind-status:
	@echo "Checking Kind cluster status..."
	@kubectl cluster-info --context kind-kind 2>/dev/null || echo "Kind cluster not running"
	@echo ""
	@echo "Checking KubeVirt status..."
	@kubectl get kubevirt -n kubevirt 2>/dev/null || echo "KubeVirt not installed"
	@echo ""
	@echo "Checking nodes..."
	@kubectl get nodes 2>/dev/null || true

# Tilt commands
.PHONY: tilt-up
tilt-up:
	@echo "Starting Tilt in background..."
	./scripts/tilt-up.sh

.PHONY: tilt-down
tilt-down:
	@echo "Stopping Tilt (preserving VM images)..."
	./scripts/tilt-down.sh

.PHONY: tilt-clean
tilt-clean:
	@echo "Stopping Tilt and removing all resources including VM images..."
	./scripts/tilt-down.sh --clean-all

.PHONY: tilt-status
tilt-status:
	@echo "Checking Tilt status..."
	@tilt get session 2>/dev/null || echo "Tilt not running"

.PHONY: vm-preload
vm-preload:
	@echo "Pre-loading VM container images..."
	./scripts/preload-vm-images.sh

# Docker commands
.PHONY: build
build:
	@echo "Building all Docker images..."
	./build_docker.sh

.PHONY: build-push
build-push:
	@echo "Building and pushing images to registry..."
	./scripts/build-and-push.sh

# Combined development commands
.PHONY: dev-setup
dev-setup: kind-setup
	@echo "Development environment setup complete!"
	@echo "Run 'make tilt-up' to start development"

.PHONY: dev-teardown
dev-teardown: tilt-down kind-teardown
	@echo "Development environment torn down"