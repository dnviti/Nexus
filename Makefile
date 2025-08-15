# Nexus Framework Makefile
# Simplifies common Poetry commands and development tasks

# Variables
PYTHON := python3
POETRY := poetry
POETRY_VERSION := 1.7.1
PROJECT_NAME := nexus-framework
PLUGIN_DIR := app/plugins
EXAMPLE_DIR := examples

# Colors for output
RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[1;33m
BLUE := \033[0;34m
NC := \033[0m # No Color

# Default target
.DEFAULT_GOAL := help

# Phony targets
.PHONY: help install install-dev install-all clean test lint format security build publish \
        docker-build docker-run update deps tree outdated shell run migrate docs serve-docs \
        plugin-new plugin-install plugin-test plugin-build pre-commit ci

# ============================================================================
# HELP
# ============================================================================

help: ## Show this help message
	@echo "$(BLUE)Nexus Framework - Poetry-based Development Commands$(NC)"
	@echo ""
	@echo "$(GREEN)Available targets:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Plugin-specific targets:$(NC)"
	@echo "  $(YELLOW)plugin-new NAME=myplug$(NC)  Create new plugin from template"
	@echo "  $(YELLOW)plugin-install P=task$(NC)   Install plugin dependencies"
	@echo "  $(YELLOW)plugin-test P=task$(NC)      Test specific plugin"
	@echo "  $(YELLOW)plugin-build P=task$(NC)     Build specific plugin"
	@echo ""
	@echo "$(BLUE)Examples:$(NC)"
	@echo "  make install          # Install core dependencies"
	@echo "  make install-dev      # Install with dev dependencies"
	@echo "  make test            # Run all tests"
	@echo "  make run             # Run the application"
	@echo "  make plugin-new NAME=awesome  # Create new plugin"

# ============================================================================
# INSTALLATION
# ============================================================================

check-poetry: ## Check if Poetry is installed
	@command -v $(POETRY) >/dev/null 2>&1 || { \
		echo "$(RED)Poetry is not installed. Installing...$(NC)"; \
		curl -sSL https://install.python-poetry.org | $(PYTHON) -; \
	}
	@echo "$(GREEN)Poetry version: $$($(POETRY) --version)$(NC)"

install: check-poetry ## Install core dependencies
	@echo "$(BLUE)Installing core dependencies...$(NC)"
	$(POETRY) install
	@echo "$(GREEN)Installation complete!$(NC)"

install-dev: check-poetry ## Install with development dependencies
	@echo "$(BLUE)Installing with development dependencies...$(NC)"
	$(POETRY) install --with dev,test,docs
	@echo "$(GREEN)Development installation complete!$(NC)"

install-all: check-poetry ## Install all dependencies including extras
	@echo "$(BLUE)Installing all dependencies and extras...$(NC)"
	$(POETRY) install --with dev,test,docs,production --all-extras
	@echo "$(GREEN)Full installation complete!$(NC)"

install-prod: check-poetry ## Install production dependencies only
	@echo "$(BLUE)Installing production dependencies...$(NC)"
	$(POETRY) install --without dev,test,docs
	@echo "$(GREEN)Production installation complete!$(NC)"

# ============================================================================
# DEVELOPMENT
# ============================================================================

shell: ## Activate Poetry shell
	@echo "$(BLUE)Activating Poetry shell...$(NC)"
	$(POETRY) shell

run: ## Run the main application
	@echo "$(BLUE)Starting Nexus Framework...$(NC)"
	$(POETRY) run python app/main.py

run-example: ## Run example application
	@echo "$(BLUE)Starting example application...$(NC)"
	cd $(EXAMPLE_DIR) && $(POETRY) run python complete_app.py

dev: ## Run in development mode with auto-reload
	@echo "$(BLUE)Starting in development mode...$(NC)"
	$(POETRY) run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ============================================================================
# DEPENDENCY MANAGEMENT
# ============================================================================

deps: ## Show dependency tree
	@echo "$(BLUE)Dependency tree:$(NC)"
	$(POETRY) show --tree

outdated: ## Show outdated packages
	@echo "$(BLUE)Outdated packages:$(NC)"
	$(POETRY) show --outdated

update: ## Update all dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	$(POETRY) update
	@echo "$(GREEN)Dependencies updated!$(NC)"

update-lock: ## Update lock file without installing
	@echo "$(BLUE)Updating lock file...$(NC)"
	$(POETRY) lock --no-update
	@echo "$(GREEN)Lock file updated!$(NC)"

add: ## Add a dependency (usage: make add PKG=package-name)
	@if [ -z "$(PKG)" ]; then \
		echo "$(RED)Error: PKG is required. Usage: make add PKG=package-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Adding $(PKG)...$(NC)"
	$(POETRY) add $(PKG)

add-dev: ## Add a dev dependency (usage: make add-dev PKG=package-name)
	@if [ -z "$(PKG)" ]; then \
		echo "$(RED)Error: PKG is required. Usage: make add-dev PKG=package-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Adding $(PKG) to dev dependencies...$(NC)"
	$(POETRY) add --group dev $(PKG)

remove: ## Remove a dependency (usage: make remove PKG=package-name)
	@if [ -z "$(PKG)" ]; then \
		echo "$(RED)Error: PKG is required. Usage: make remove PKG=package-name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Removing $(PKG)...$(NC)"
	$(POETRY) remove $(PKG)

# ============================================================================
# TESTING
# ============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running tests...$(NC)"
	$(POETRY) run pytest

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	$(POETRY) run pytest tests/unit -v

test-integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	$(POETRY) run pytest tests/integration -v

test-cov: ## Run tests with coverage
	@echo "$(BLUE)Running tests with coverage...$(NC)"
	$(POETRY) run pytest --cov=nexus --cov-report=html --cov-report=term

test-watch: ## Run tests in watch mode
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	$(POETRY) run pytest-watch

test-fast: ## Run fast tests only
	@echo "$(BLUE)Running fast tests...$(NC)"
	$(POETRY) run pytest -m "not slow"

# ============================================================================
# CODE QUALITY
# ============================================================================

lint: ## Run all linters
	@echo "$(BLUE)Running linters...$(NC)"
	$(POETRY) run flake8 app/
	$(POETRY) run pylint app/
	$(POETRY) run mypy app/
	@echo "$(GREEN)Linting complete!$(NC)"

format: ## Format code with black and isort
	@echo "$(BLUE)Formatting code...$(NC)"
	$(POETRY) run black app/ tests/
	$(POETRY) run isort app/ tests/
	@echo "$(GREEN)Code formatted!$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code format...$(NC)"
	$(POETRY) run black --check app/ tests/
	$(POETRY) run isort --check-only app/ tests/

type-check: ## Run type checking with mypy
	@echo "$(BLUE)Running type checks...$(NC)"
	$(POETRY) run mypy app/

security: ## Run security checks
	@echo "$(BLUE)Running security checks...$(NC)"
	$(POETRY) run bandit -r app/
	$(POETRY) run safety check
	$(POETRY) run pip-audit
	@echo "$(GREEN)Security checks complete!$(NC)"

pre-commit: ## Run pre-commit hooks
	@echo "$(BLUE)Running pre-commit hooks...$(NC)"
	$(POETRY) run pre-commit run --all-files

# ============================================================================
# BUILD & PUBLISH
# ============================================================================

build: clean ## Build package
	@echo "$(BLUE)Building package...$(NC)"
	$(POETRY) build
	@echo "$(GREEN)Package built successfully!$(NC)"

publish-test: build ## Publish to TestPyPI
	@echo "$(BLUE)Publishing to TestPyPI...$(NC)"
	$(POETRY) config repositories.testpypi https://test.pypi.org/legacy/
	$(POETRY) publish -r testpypi

publish: build ## Publish to PyPI
	@echo "$(YELLOW)Publishing to PyPI...$(NC)"
	@echo "$(RED)Are you sure? This action cannot be undone! [y/N]$(NC)"
	@read -r REPLY; \
	if [ "$$REPLY" = "y" ] || [ "$$REPLY" = "Y" ]; then \
		$(POETRY) publish; \
		echo "$(GREEN)Published to PyPI!$(NC)"; \
	else \
		echo "$(YELLOW)Publication cancelled.$(NC)"; \
	fi

version: ## Show current version
	@echo "$(BLUE)Current version: $(NC)$$($(POETRY) version --short)"

version-patch: ## Bump patch version (x.x.1)
	@echo "$(BLUE)Bumping patch version...$(NC)"
	$(POETRY) version patch
	@echo "$(GREEN)New version: $$($(POETRY) version --short)$(NC)"

version-minor: ## Bump minor version (x.1.0)
	@echo "$(BLUE)Bumping minor version...$(NC)"
	$(POETRY) version minor
	@echo "$(GREEN)New version: $$($(POETRY) version --short)$(NC)"

version-major: ## Bump major version (1.0.0)
	@echo "$(BLUE)Bumping major version...$(NC)"
	$(POETRY) version major
	@echo "$(GREEN)New version: $$($(POETRY) version --short)$(NC)"

# ============================================================================
# PLUGIN MANAGEMENT
# ============================================================================

plugin-new: ## Create new plugin from template (usage: make plugin-new NAME=myplugin)
	@if [ -z "$(NAME)" ]; then \
		echo "$(RED)Error: NAME is required. Usage: make plugin-new NAME=myplugin$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating new plugin: $(NAME)...$(NC)"
	@cp -r plugin_template $(PLUGIN_DIR)/$(NAME)
	@echo "$(GREEN)Plugin $(NAME) created at $(PLUGIN_DIR)/$(NAME)$(NC)"
	@echo "$(YELLOW)Next steps:$(NC)"
	@echo "  1. Update $(PLUGIN_DIR)/$(NAME)/pyproject.toml"
	@echo "  2. Update $(PLUGIN_DIR)/$(NAME)/manifest.json"
	@echo "  3. Run: make plugin-install P=$(NAME)"

plugin-install: ## Install plugin dependencies (usage: make plugin-install P=task_manager)
	@if [ -z "$(P)" ]; then \
		echo "$(RED)Error: P is required. Usage: make plugin-install P=plugin_name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Installing dependencies for plugin: $(P)...$(NC)"
	@cd $(PLUGIN_DIR)/$(P) && $(POETRY) install
	@echo "$(GREEN)Plugin $(P) dependencies installed!$(NC)"

plugin-test: ## Test specific plugin (usage: make plugin-test P=task_manager)
	@if [ -z "$(P)" ]; then \
		echo "$(RED)Error: P is required. Usage: make plugin-test P=plugin_name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Testing plugin: $(P)...$(NC)"
	@cd $(PLUGIN_DIR)/$(P) && $(POETRY) run pytest tests/

plugin-build: ## Build specific plugin (usage: make plugin-build P=task_manager)
	@if [ -z "$(P)" ]; then \
		echo "$(RED)Error: P is required. Usage: make plugin-build P=plugin_name$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Building plugin: $(P)...$(NC)"
	@cd $(PLUGIN_DIR)/$(P) && $(POETRY) build
	@echo "$(GREEN)Plugin $(P) built successfully!$(NC)"

plugin-list: ## List all available plugins
	@echo "$(BLUE)Available plugins:$(NC)"
	@for plugin in $(PLUGIN_DIR)/*; do \
		if [ -d "$$plugin" ] && [ -f "$$plugin/manifest.json" ]; then \
			echo "  $(YELLOW)$$(basename $$plugin)$(NC)"; \
		fi \
	done

# ============================================================================
# DOCUMENTATION
# ============================================================================

docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	$(POETRY) run mkdocs build
	@echo "$(GREEN)Documentation built in site/ directory!$(NC)"

serve-docs: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation at http://localhost:8001...$(NC)"
	$(POETRY) run mkdocs serve --dev-addr localhost:8001

# ============================================================================
# DATABASE
# ============================================================================

migrate: ## Run database migrations
	@echo "$(BLUE)Running database migrations...$(NC)"
	$(POETRY) run alembic upgrade head
	@echo "$(GREEN)Migrations complete!$(NC)"

migrate-create: ## Create new migration (usage: make migrate-create MSG="add user table")
	@if [ -z "$(MSG)" ]; then \
		echo "$(RED)Error: MSG is required. Usage: make migrate-create MSG=\"description\"$(NC)"; \
		exit 1; \
	fi
	@echo "$(BLUE)Creating migration: $(MSG)...$(NC)"
	$(POETRY) run alembic revision --autogenerate -m "$(MSG)"

migrate-rollback: ## Rollback last migration
	@echo "$(YELLOW)Rolling back last migration...$(NC)"
	$(POETRY) run alembic downgrade -1

# ============================================================================
# DOCKER
# ============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	docker build -t $(PROJECT_NAME):latest .
	@echo "$(GREEN)Docker image built!$(NC)"

docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	docker run -p 8000:8000 --env-file .env $(PROJECT_NAME):latest

docker-compose-up: ## Start services with docker-compose
	@echo "$(BLUE)Starting services...$(NC)"
	docker-compose up -d

docker-compose-down: ## Stop services with docker-compose
	@echo "$(BLUE)Stopping services...$(NC)"
	docker-compose down

# ============================================================================
# UTILITIES
# ============================================================================

clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	@rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/ .mypy_cache/
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "$(GREEN)Cleaned!$(NC)"

clean-all: clean ## Clean everything including virtual environment
	@echo "$(RED)Removing virtual environment...$(NC)"
	$(POETRY) env remove python
	@rm -rf .venv/
	@echo "$(GREEN)All cleaned!$(NC)"

export-requirements: ## Export requirements.txt files
	@echo "$(BLUE)Exporting requirements files...$(NC)"
	$(POETRY) export -f requirements.txt --output requirements.txt
	$(POETRY) export -f requirements.txt --with dev --output dev-requirements.txt
	$(POETRY) export -f requirements.txt --with production --output production-requirements.txt
	@echo "$(GREEN)Requirements exported!$(NC)"

env-info: ## Show Poetry environment info
	@echo "$(BLUE)Poetry environment information:$(NC)"
	$(POETRY) env info

ci: lint test security ## Run CI pipeline locally
	@echo "$(GREEN)CI pipeline passed!$(NC)"

# ============================================================================
# GIT HOOKS
# ============================================================================

install-hooks: ## Install git hooks
	@echo "$(BLUE)Installing git hooks...$(NC)"
	$(POETRY) run pre-commit install
	@echo "$(GREEN)Git hooks installed!$(NC)"

# ============================================================================
# SHORTCUTS
# ============================================================================

i: install ## Shortcut for install
id: install-dev ## Shortcut for install-dev
t: test ## Shortcut for test
tc: test-cov ## Shortcut for test with coverage
f: format ## Shortcut for format
l: lint ## Shortcut for lint
r: run ## Shortcut for run
d: dev ## Shortcut for dev mode
b: build ## Shortcut for build
