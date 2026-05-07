.DEFAULT_GOAL := help

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
BLACK := $(VENV)/bin/black
PYTEST := $(VENV)/bin/pytest
ALEMBIC := $(VENV)/bin/alembic
UVICORN := $(VENV)/bin/uvicorn

API_HOST := 0.0.0.0
API_PORT := 8004

.PHONY: help \
        install install-dev \
        dev test test-unit test-integration coverage \
        lint format check \
        docker-up docker-down docker-logs docker-restart \
        docker-build docker-rebuild docker-rebuild-nocache docker-ps \
        migrate migrate-create migrate-down \
        frontend-dev frontend-build frontend-lint frontend-test

help:  ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

# ---- Setup ----------------------------------------------------------------

install:  ## Install runtime dependencies
	$(PIP) install -r requirements.txt

install-dev: install  ## Install runtime + dev tools (ruff, black, pytest-cov)
	$(PIP) install ruff black pytest pytest-cov pytest-asyncio

# ---- Development ----------------------------------------------------------

dev:  ## Run FastAPI dev server with --reload
	$(UVICORN) app.main:app --reload --host $(API_HOST) --port $(API_PORT)

# ---- Testing --------------------------------------------------------------

test:  ## Run all tests with coverage
	$(PYTEST)

test-unit:  ## Run unit tests only
	$(PYTEST) tests/unit

test-integration:  ## Run integration tests only
	$(PYTEST) tests/integration

coverage:  ## Generate HTML coverage report
	$(PYTEST) --cov-report=html
	@echo "Open htmlcov/index.html in your browser"

# ---- Code quality ---------------------------------------------------------

lint:  ## Run ruff + black --check
	$(RUFF) check app/ tests/
	$(BLACK) --check app/ tests/

format:  ## Auto-fix with ruff and reformat with black
	$(RUFF) check --fix app/ tests/
	$(BLACK) app/ tests/

check: lint test  ## Run lint + tests (use as the local CI gate)

# ---- Docker ---------------------------------------------------------------

docker-up:  ## Start all services in the background
	docker compose up -d

docker-down:  ## Stop all services
	docker compose down

docker-restart:  ## Restart the api container
	docker compose restart api

docker-logs:  ## Tail the api container logs
	docker compose logs -f api

docker-build:  ## Rebuild api + frontend images (uses cache)
	docker compose build api frontend

docker-rebuild: docker-build docker-up  ## Build and roll services to the new images

docker-rebuild-nocache:  ## Full no-cache rebuild + roll (slow, use after deps changes)
	docker compose build --no-cache api frontend
	docker compose up -d

docker-ps:  ## Show service status
	docker compose ps

# ---- Database -------------------------------------------------------------

migrate:  ## Apply pending Alembic migrations
	$(ALEMBIC) upgrade head

migrate-create:  ## Create new migration; usage: make migrate-create M="message"
	@if [ -z "$(M)" ]; then \
		echo "Usage: make migrate-create M=\"description\""; exit 1; \
	fi
	$(ALEMBIC) revision --autogenerate -m "$(M)"

migrate-down:  ## Roll back the last migration
	$(ALEMBIC) downgrade -1

# ---- Frontend -------------------------------------------------------------

frontend-dev:  ## Run Vite dev server (port 5174)
	cd frontend && npm run dev

frontend-build:  ## Build frontend for production
	cd frontend && npm run build

frontend-lint:  ## Run eslint on the frontend
	cd frontend && npm run lint

frontend-test:  ## Run Playwright UI tests (requires Docker)
	cd frontend && npm run test:ui:line
