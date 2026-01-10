# Critical Wormhole Tools - Makefile
# Common development tasks

.PHONY: help install install-dev test test-unit test-integration test-coverage lint format clean build publish extension-test extension-build docker-build docker-run

# Default target
help:
	@echo "Critical Wormhole Tools - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install package in production mode"
	@echo "  make install-dev      Install package with dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  make test             Run all Python tests"
	@echo "  make test-unit        Run unit tests only"
	@echo "  make test-integration Run integration tests only"
	@echo "  make test-coverage    Run tests with coverage report"
	@echo "  make extension-test   Run browser extension tests"
	@echo ""
	@echo "Code Quality:"
	@echo "  make lint             Run linting checks"
	@echo "  make format           Auto-fix linting issues"
	@echo ""
	@echo "Build:"
	@echo "  make build            Build Python package"
	@echo "  make extension-build  Build browser extension"
	@echo "  make docker-build     Build Docker image"
	@echo ""
	@echo "Other:"
	@echo "  make clean            Remove build artifacts"
	@echo "  make docker-run       Run wh in Docker"

# Installation
install:
	pip install -e .

install-dev:
	pip install -e ".[dev,relay]"

# Testing
test:
	pytest tests/ -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v -m integration

test-coverage:
	pytest tests/ --cov=wh --cov-report=html --cov-report=term-missing
	@echo "Coverage report: htmlcov/index.html"

extension-test:
	cd browser-extension && npm test

# Code Quality
lint:
	ruff check src/ tests/
	@echo "Linting passed!"

format:
	ruff check src/ tests/ --fix
	@echo "Formatting complete!"

# Build
build:
	python -m build
	@echo "Package built in dist/"

extension-build:
	cd browser-extension && npm run build
	@echo "Extension built in browser-extension/dist/"

docker-build:
	docker build -t wormhole-tools:latest .
	@echo "Docker image built: wormhole-tools:latest"

docker-run:
	docker run --rm -it wormhole-tools:latest $(ARGS)

# Clean
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf src/*.egg-info/
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "Cleaned build artifacts"

# Publish (requires PyPI credentials)
publish: clean build
	twine check dist/*
	twine upload dist/*
