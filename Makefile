# Nexus Framework - Development Makefile
# ============================================================================
# Common development commands for the Nexus Framework project.
#
# Usage:
#   make help          Show available commands
#   make install       Install dependencies
#   make test          Run all tests
#   make check         Run all quality checks
#   make fix           Auto-fix code issues
#   make build         Build the package
#   make clean         Clean build artifacts
# ============================================================================

.PHONY: help install test check fix build clean lint format type-check security docs serve-docs lint-docs check-links pre-push fast-check coverage integration unit

# Default target
.DEFAULT_GOAL := help

# Colors for output
BLUE := \033[34m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
BOLD := \033[1m
NC := \033[0m

# Project configuration
PYTHON_DIRS := nexus tests scripts
PACKAGE_NAME := nexus-platform

help: ## Show this help message
	@echo "$(BOLD)$(BLUE)Nexus Framework - Development Commands$(NC)"
	@echo ""
	@echo "$(BOLD)Usage:$(NC)"
	@echo "  make <command>"
	@echo ""
	@echo "$(BOLD)Available commands:$(NC)"
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  $(BLUE)%-15s$(NC) %s\n", $$1, $$2}' $(MAKEFILE_LIST)
	@echo ""
	@echo "$(BOLD)Examples:$(NC)"
	@echo "  make install          # Install all dependencies"
	@echo "  make test             # Run complete test suite"
	@echo "  make fix              # Auto-fix formatting and imports"
	@echo "  make pre-push         # Run all checks before push"

# ============================================================================
# Setup and Installation
# ============================================================================

install: ## Install all dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	poetry install --no-interaction --with dev,test,docs
	@echo "$(GREEN)✅ Dependencies installed$(NC)"

install-ci: ## Install CI dependencies only
	@echo "$(BLUE)Installing CI dependencies...$(NC)"
	poetry install --no-interaction --with dev,test --no-root
	@echo "$(GREEN)✅ CI dependencies installed$(NC)"

update: ## Update dependencies
	@echo "$(BLUE)Updating dependencies...$(NC)"
	poetry update
	@echo "$(GREEN)✅ Dependencies updated$(NC)"

# ============================================================================
# Code Quality
# ============================================================================

format: ## Format code with Black
	@echo "$(BLUE)Formatting code...$(NC)"
	poetry run black $(PYTHON_DIRS)
	@echo "$(GREEN)✅ Code formatted$(NC)"

format-check: ## Check code formatting
	@echo "$(BLUE)Checking code formatting...$(NC)"
	poetry run black --check --diff $(PYTHON_DIRS)

sort-imports: ## Sort imports with isort
	@echo "$(BLUE)Sorting imports...$(NC)"
	poetry run isort $(PYTHON_DIRS)
	@echo "$(GREEN)✅ Imports sorted$(NC)"

sort-imports-check: ## Check import sorting
	@echo "$(BLUE)Checking import sorting...$(NC)"
	poetry run isort --check-only --diff $(PYTHON_DIRS)

lint: ## Lint code with Flake8
	@echo "$(BLUE)Linting code...$(NC)"
	poetry run flake8 $(PYTHON_DIRS) --count --select=E9,F63,F7,F82 --show-source --statistics

type-check: ## Run type checking with MyPy
	@echo "$(BLUE)Type checking...$(NC)"
	poetry run mypy nexus/

security: ## Run security scan with Bandit
	@echo "$(BLUE)Running security scan...$(NC)"
	poetry run bandit -r nexus/ -f json -o bandit-report.json
	@echo "$(GREEN)✅ Security scan complete (check bandit-report.json)$(NC)"

fix: format sort-imports ## Auto-fix formatting and import issues
	@echo "$(GREEN)✅ Code formatting and imports fixed$(NC)"

check: format-check sort-imports-check lint type-check security lint-docs ## Run all quality checks
	@echo "$(GREEN)✅ All quality checks passed$(NC)"

# ============================================================================
# Testing
# ============================================================================

unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	poetry run pytest tests/unit/ --tb=short --disable-warnings

integration: ## Run integration tests only
	@echo "$(BLUE)Running integration tests...$(NC)"
	poetry run pytest tests/integration/ --tb=short --disable-warnings

test: ## Run all tests with coverage
	@echo "$(BLUE)Running complete test suite...$(NC)"
	poetry run pytest tests/ \
		--cov=nexus \
		--cov-branch \
		--cov-report=xml \
		--cov-report=html \
		--cov-report=term-missing \
		--cov-fail-under=20 \
		--tb=short \
		--asyncio-mode=auto \
		--disable-warnings

test-fast: ## Run tests without coverage (faster)
	@echo "$(BLUE)Running fast test suite...$(NC)"
	poetry run pytest tests/ --tb=short --disable-warnings --maxfail=5

coverage: ## Generate coverage report
	@echo "$(BLUE)Generating coverage report...$(NC)"
	poetry run pytest tests/unit/ \
		--cov=nexus \
		--cov-branch \
		--cov-report=html \
		--cov-report=term-missing \
		--disable-warnings
	@echo "$(GREEN)✅ Coverage report generated in htmlcov/$(NC)"

# ============================================================================
# Build and Package
# ============================================================================

build: clean ## Build the package
	@echo "$(BLUE)Building package...$(NC)"
	poetry build
	@echo "$(GREEN)✅ Package built in dist/$(NC)"

build-check: build ## Build and validate package
	@echo "$(BLUE)Validating package...$(NC)"
	poetry run twine check dist/*
	@echo "$(GREEN)✅ Package validation passed$(NC)"

install-local: build ## Install package locally
	@echo "$(BLUE)Installing package locally...$(NC)"
	pip install dist/$(PACKAGE_NAME)-*.whl --force-reinstall
	@echo "$(GREEN)✅ Package installed locally$(NC)"

# ============================================================================
# Documentation
# ============================================================================

docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	poetry run mkdocs build
	@echo "$(GREEN)✅ Documentation built in site/$(NC)"

serve-docs: ## Serve documentation locally
	@echo "$(BLUE)Serving documentation at http://localhost:8000$(NC)"
	poetry run mkdocs serve

lint-docs: ## Lint documentation (links and structure)
	@echo "$(BLUE)Linting documentation...$(NC)"
	@if command -v markdown-link-check >/dev/null 2>&1; then \
		echo "$(BLUE)Checking markdown links...$(NC)"; \
		find docs -name "*.md" -type f -exec markdown-link-check -c .github/markdown-link-check.json {} \; || exit 1; \
		echo "$(GREEN)✅ Link check passed$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  markdown-link-check not found. Install with: npm install -g markdown-link-check$(NC)"; \
	fi
	@echo "$(BLUE)Verifying documentation structure...$(NC)"
	@if [ ! -d "docs" ]; then \
		echo "$(RED)❌ docs/ directory not found!$(NC)"; \
		exit 1; \
	fi
	@if [ ! -f "docs/index.md" ]; then \
		echo "$(RED)❌ Missing required file: docs/index.md$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Documentation structure verified - $$(find docs -name "*.md" -type f | wc -l) markdown files found$(NC)"

check-links: ## Check markdown links only
	@echo "$(BLUE)Checking markdown links...$(NC)"
	@if command -v markdown-link-check >/dev/null 2>&1; then \
		find docs -name "*.md" -type f -exec markdown-link-check -c .github/markdown-link-check.json {} \; || exit 1; \
		echo "$(GREEN)✅ All links are valid$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  markdown-link-check not found. Install with: npm install -g markdown-link-check$(NC)"; \
		exit 1; \
	fi

# ============================================================================
# Cleanup
# ============================================================================

clean: ## Clean build artifacts and cache
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -rf dist/ build/ *.egg-info/
	rm -rf .pytest_cache/ .coverage htmlcov/ coverage.xml
	rm -rf .mypy_cache/ .ruff_cache/
	rm -rf site/ bandit-report.json
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✅ Build artifacts cleaned$(NC)"

clean-all: clean ## Clean everything including Poetry cache
	@echo "$(BLUE)Cleaning Poetry cache...$(NC)"
	poetry cache clear --all pypi -n 2>/dev/null || true
	@echo "$(GREEN)✅ All artifacts cleaned$(NC)"

# ============================================================================
# Development Workflow
# ============================================================================

dev-setup: install ## Complete development setup
	@echo "$(BLUE)Setting up development environment...$(NC)"
	@echo "$(BLUE)Installing pre-commit hooks...$(NC)"
	@if [ -f scripts/pre_push_check.py ]; then \
		python scripts/pre_push_check.py --fast; \
	fi
	@echo "$(GREEN)✅ Development environment ready$(NC)"

pre-push: ## Run comprehensive pre-push checks
	@echo "$(BLUE)Running pre-push validation...$(NC)"
	@if [ -f scripts/pre_push_check.py ]; then \
		python scripts/pre_push_check.py; \
	elif [ -f scripts/pre-push-check.sh ]; then \
		./scripts/pre-push-check.sh; \
	else \
		$(MAKE) check test build-check; \
	fi

fast-check: ## Quick validation check
	@echo "$(BLUE)Running quick validation...$(NC)"
	@if [ -f scripts/pre_push_check.py ]; then \
		python scripts/pre_push_check.py --fast; \
	else \
		$(MAKE) format-check sort-imports-check lint test-fast; \
	fi

# ============================================================================
# Git Workflow
# ============================================================================

git-setup: ## Setup git hooks and configuration
	@echo "$(BLUE)Setting up git hooks...$(NC)"
	@if [ -d .git ]; then \
		echo "#!/bin/bash" > .git/hooks/pre-commit; \
		echo "make fast-check" >> .git/hooks/pre-commit; \
		chmod +x .git/hooks/pre-commit; \
		echo "$(GREEN)✅ Git hooks configured$(NC)"; \
	else \
		echo "$(YELLOW)⚠️  Not a git repository$(NC)"; \
	fi

# ============================================================================
# Utilities
# ============================================================================

info: ## Show project information
	@echo "$(BOLD)$(BLUE)Nexus Framework Project Information$(NC)"
	@echo ""
	@echo "$(BOLD)Project:$(NC)"
	@poetry version 2>/dev/null || echo "  Version: Unknown"
	@echo "  Python: $(shell python --version 2>/dev/null || echo 'Not found')"
	@echo "  Poetry: $(shell poetry --version 2>/dev/null || echo 'Not found')"
	@echo ""
	@echo "$(BOLD)Directories:$(NC)"
	@echo "  Source: nexus/"
	@echo "  Tests: tests/"
	@echo "  Scripts: scripts/"
	@echo "  Docs: docs/"
	@echo ""
	@echo "$(BOLD)Files:$(NC)"
	@echo "  Source files: $(shell find nexus -name "*.py" | wc -l 2>/dev/null || echo '0')"
	@echo "  Test files: $(shell find tests -name "*.py" | wc -l 2>/dev/null || echo '0')"
	@echo "  Total lines: $(shell find nexus tests -name "*.py" -exec wc -l {} + 2>/dev/null | tail -1 | awk '{print $$1}' || echo '0')"

deps-tree: ## Show dependency tree
	@echo "$(BLUE)Dependency tree:$(NC)"
	poetry show --tree

deps-outdated: ## Show outdated dependencies
	@echo "$(BLUE)Outdated dependencies:$(NC)"
	poetry show --outdated

# ============================================================================
# CI/CD Simulation
# ============================================================================

ci-test: install-ci ## Simulate CI test pipeline
	@echo "$(BLUE)Simulating CI test pipeline...$(NC)"
	$(MAKE) check
	$(MAKE) test
	$(MAKE) build-check
	@echo "$(GREEN)✅ CI simulation completed$(NC)"

# ============================================================================
# Troubleshooting
# ============================================================================

doctor: ## Run project health check
	@echo "$(BOLD)$(BLUE)Nexus Framework Health Check$(NC)"
	@echo ""
	@echo "$(BOLD)Environment:$(NC)"
	@python --version 2>/dev/null && echo "$(GREEN)✅ Python available$(NC)" || echo "$(RED)❌ Python not found$(NC)"
	@poetry --version 2>/dev/null && echo "$(GREEN)✅ Poetry available$(NC)" || echo "$(RED)❌ Poetry not found$(NC)"
	@git --version 2>/dev/null && echo "$(GREEN)✅ Git available$(NC)" || echo "$(RED)❌ Git not found$(NC)"
	@echo ""
	@echo "$(BOLD)Project:$(NC)"
	@[ -f pyproject.toml ] && echo "$(GREEN)✅ pyproject.toml found$(NC)" || echo "$(RED)❌ pyproject.toml missing$(NC)"
	@[ -f poetry.lock ] && echo "$(GREEN)✅ poetry.lock found$(NC)" || echo "$(YELLOW)⚠️  poetry.lock missing$(NC)"
	@[ -d nexus ] && echo "$(GREEN)✅ Source directory exists$(NC)" || echo "$(RED)❌ Source directory missing$(NC)"
	@[ -d tests ] && echo "$(GREEN)✅ Tests directory exists$(NC)" || echo "$(RED)❌ Tests directory missing$(NC)"
	@echo ""
	@echo "$(BOLD)Dependencies:$(NC)"
	@poetry check 2>/dev/null && echo "$(GREEN)✅ Poetry configuration valid$(NC)" || echo "$(RED)❌ Poetry configuration invalid$(NC)"

# ============================================================================
# Help for specific workflows
# ============================================================================

help-dev: ## Show development workflow help
	@echo "$(BOLD)$(BLUE)Development Workflow$(NC)"
	@echo ""
	@echo "$(BOLD)Initial setup:$(NC)"
	@echo "  make dev-setup        # Complete development environment setup"
	@echo ""
	@echo "$(BOLD)Daily development:$(NC)"
	@echo "  make fix              # Auto-fix code issues"
	@echo "  make test-fast        # Quick test run"
	@echo "  make fast-check       # Quick validation"
	@echo ""
	@echo "$(BOLD)Before committing:$(NC)"
	@echo "  make pre-push         # Comprehensive validation"
	@echo "  make check            # Quality checks only"
	@echo "  make test             # Full test suite"
	@echo ""
	@echo "$(BOLD)Troubleshooting:$(NC)"
	@echo "  make doctor           # Health check"
	@echo "  make clean            # Clean artifacts"
	@echo "  make install          # Reinstall dependencies"
