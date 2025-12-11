.PHONY: help install dev lint format type-check test run build docker-build docker-run clean

# Default target
help:
	@echo "Mattermost MCP Server - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install     Install dependencies"
	@echo "  make dev         Install with dev dependencies"
	@echo ""
	@echo "Development:"
	@echo "  make run         Run the server locally"
	@echo "  make lint        Run linting (ruff)"
	@echo "  make format      Format code (ruff)"
	@echo "  make type-check  Run type checking (mypy)"
	@echo "  make test        Run tests"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build  Build Docker image"
	@echo "  make docker-run    Run Docker container"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean       Remove build artifacts"

# Install dependencies
install:
	pip install -e .

# Install with dev dependencies
dev:
	pip install -e ".[dev]"
	pre-commit install

# Run the server
run:
	python -m mattermost_mcp.main

# Linting
lint:
	ruff check src/ tests/

# Format code
format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

# Type checking
type-check:
	mypy src/

# Run tests
test:
	pytest tests/ -v --cov=mattermost_mcp --cov-report=term-missing

# Build package
build:
	pip install build
	python -m build

# Docker build
docker-build:
	docker build -f infra/docker/Dockerfile -t mattermost-mcp:latest .

# Docker run (requires .env file)
docker-run:
	docker run --rm -it \
		--env-file .env \
		-p 8000:8000 \
		-v mattermost-mcp-data:/data/mattermost-mcp \
		mattermost-mcp:latest

# Clean build artifacts
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
