.PHONY: help install dev-install test lint format type-check clean run-ollama

# Use UV wrapper script
UV := ./run-uv.sh

help:
	@echo "Available commands:"
	@echo "  make install        - Install production dependencies"
	@echo "  make dev-install    - Install all dependencies including dev tools"
	@echo "  make test          - Run tests"
	@echo "  make lint          - Run linting"
	@echo "  make format        - Format code"
	@echo "  make type-check    - Run type checking"
	@echo "  make clean         - Clean cache and temporary files"
	@echo "  make run-ollama    - Start Ollama server"

install:
	$(UV) sync

dev-install:
	$(UV) sync --extra dev

test:
	$(UV) run pytest tests/

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff format .

type-check:
	$(UV) run mypy pdf_translator/ main.py

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	rm -rf dist/
	rm -rf *.egg-info

run-ollama:
	@echo "Starting Ollama server..."
	@ollama serve &
	@sleep 2
	@echo "Ollama server started. Checking model availability..."
	@ollama list | grep -q "gemma3:12b" || ollama pull gemma3:12b
	@echo "Gemma3:12b model is ready."

# Development shortcuts
dev: dev-install
	@echo "Development environment ready!"

check: lint type-check test
	@echo "All checks passed!"

# Quick translation test
test-translate:
	@echo "Running quick translation test..."
	$(UV) run python main.py tests/fixtures/sample_english.pdf --dry-run