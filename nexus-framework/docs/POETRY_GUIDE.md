# Poetry Dependency Management Guide for Nexus Framework

## Table of Contents
- [Introduction](#introduction)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Core Framework Setup](#core-framework-setup)
- [Plugin Development](#plugin-development)
- [Dependency Management](#dependency-management)
- [Development Workflow](#development-workflow)
- [Publishing Packages](#publishing-packages)
- [Best Practices](#best-practices)
- [Common Commands](#common-commands)
- [Troubleshooting](#troubleshooting)

## Introduction

The Nexus Framework uses [Poetry](https://python-poetry.org/) for modern dependency management. Poetry provides:

- **Dependency Resolution** - Automatic conflict resolution
- **Lock Files** - Reproducible builds with `poetry.lock`
- **Virtual Environments** - Automatic venv management
- **Package Building** - Simple packaging and publishing
- **Version Management** - Semantic versioning support
- **Dependency Groups** - Separate dev, test, and optional dependencies

### Why Poetry?

Unlike `pip` and `requirements.txt`, Poetry:
- Resolves dependency conflicts automatically
- Maintains a lock file for exact reproducibility
- Manages virtual environments seamlessly
- Provides a single tool for the entire workflow
- Supports dependency groups and extras
- Handles both library and application dependencies

## Installation

### Installing Poetry

#### Official Installer (Recommended)
```bash
# Linux/macOS/WSL
curl -sSL https://install.python-poetry.org | python3 -

# Windows PowerShell
(Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
```

#### Via pip (Alternative)
```bash
pip install --user poetry
```

#### Verify Installation
```bash
poetry --version
# Poetry (version 1.7.1)
```

### Configure Poetry

```bash
# Set virtual environment in project directory
poetry config virtualenvs.in-project true

# Use system Python by default
poetry config virtualenvs.prefer-active-python true

# Show more verbose output
poetry config virtualenvs.verbose true
```

## Project Structure

### Nexus Framework with Poetry

```
Nexus/
├── pyproject.toml           # Main framework configuration
├── poetry.lock             # Lock file (auto-generated)
├── app/
│   ├── nexus/             # Core framework code
│   └── plugins/           # Plugin directory
│       ├── task_manager/
│       │   ├── pyproject.toml  # Plugin-specific config
│       │   ├── poetry.lock     # Plugin lock file
│       │   └── ...
│       └── auth_advanced/
│           ├── pyproject.toml  # Plugin-specific config
│           ├── poetry.lock     # Plugin lock file
│           └── ...
├── examples/
│   ├── pyproject.toml     # Examples configuration
│   └── poetry.lock
└── plugin_template/
    └── pyproject.toml     # Template for new plugins
```

## Core Framework Setup

### Installing Nexus Framework

#### For Users
```bash
# Install from PyPI
poetry add nexus-framework

# Or install with specific database support
poetry add nexus-framework[postgresql]
poetry add nexus-framework[mysql]
poetry add nexus-framework[mongodb]

# Install with all database drivers
poetry add nexus-framework[all-databases]
```

#### For Development
```bash
# Clone the repository
git clone https://github.com/nexus-framework/nexus.git
cd nexus

# Install dependencies
poetry install

# Install with dev dependencies
poetry install --with dev

# Install with all optional groups
poetry install --with dev,docs,test,production
```

### Using Virtual Environment

```bash
# Activate virtual environment
poetry shell

# Run commands in virtual environment
poetry run python app/main.py
poetry run pytest
poetry run black .
```

## Plugin Development

### Creating a New Plugin

#### Step 1: Copy Template
```bash
cp -r plugin_template my_plugin
cd my_plugin
```

#### Step 2: Update pyproject.toml
```toml
[tool.poetry]
name = "nexus-plugin-my-plugin"
version = "1.0.0"
description = "My awesome Nexus plugin"
authors = ["Your Name <you@example.com>"]

[tool.poetry.dependencies]
python = "^3.11"
# Add your plugin-specific dependencies here
# DO NOT include nexus-framework as a dependency

[tool.poetry.group.dev.dependencies]
pytest = "^7.4.4"
black = "^23.12.1"
```

#### Step 3: Initialize Poetry
```bash
# Initialize poetry in plugin directory
poetry install

# Add dependencies as needed
poetry add redis
poetry add httpx
poetry add --group dev pytest-asyncio
```

### Plugin Dependency Management

#### Core Dependencies Only
```toml
# Basic plugin with no extra dependencies
[tool.poetry.dependencies]
python = "^3.11"
# Nexus provides: fastapi, pydantic, sqlalchemy, etc.
```

#### With Database Support
```toml
[tool.poetry.dependencies]
python = "^3.11"

[tool.poetry.group.database]
optional = true

[tool.poetry.group.database.dependencies]
asyncpg = { version = "^0.29.0", optional = true }
aiomysql = { version = "^0.2.0", optional = true }
motor = { version = "^3.3.2", optional = true }

[tool.poetry.extras]
postgresql = ["asyncpg"]
mysql = ["aiomysql"]
mongodb = ["motor"]
```

#### With Optional Features
```toml
[tool.poetry.dependencies]
python = "^3.11"
# Required dependencies
redis = "^5.0.1"

[tool.poetry.group.export]
optional = true

[tool.poetry.group.export.dependencies]
openpyxl = "^3.1.2"
reportlab = "^4.0.8"

[tool.poetry.extras]
export = ["openpyxl", "reportlab"]
full = ["openpyxl", "reportlab", "redis"]
```

### Installing Plugin Dependencies

```bash
# Install basic dependencies
poetry install

# Install with optional group
poetry install --with export

# Install with extras
poetry install -E postgresql
poetry install -E export
poetry install -E full

# Install all extras
poetry install --all-extras
```

## Dependency Management

### Adding Dependencies

```bash
# Add a production dependency
poetry add fastapi

# Add with version constraint
poetry add "fastapi>=0.100,<0.110"

# Add latest version
poetry add fastapi@latest

# Add from git
poetry add git+https://github.com/user/repo.git

# Add local package
poetry add --editable ../my-local-package

# Add to specific group
poetry add --group dev pytest
poetry add --group test factory-boy
poetry add --group docs mkdocs
```

### Updating Dependencies

```bash
# Update all dependencies
poetry update

# Update specific package
poetry update fastapi

# Update to latest version ignoring constraints
poetry add fastapi@latest

# Show outdated packages
poetry show --outdated

# Show dependency tree
poetry show --tree
```

### Removing Dependencies

```bash
# Remove a dependency
poetry remove requests

# Remove from specific group
poetry remove --group dev pytest-mock
```

### Lock File Management

```bash
# Generate/update lock file
poetry lock

# Install from lock file (exact versions)
poetry install

# Don't update lock file
poetry install --no-update

# Export to requirements.txt (if needed)
poetry export -f requirements.txt --output requirements.txt
poetry export -f requirements.txt --dev --output dev-requirements.txt
```

## Development Workflow

### Initial Setup

```bash
# 1. Clone repository
git clone https://github.com/nexus-framework/nexus.git
cd nexus

# 2. Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# 3. Configure Poetry
poetry config virtualenvs.in-project true

# 4. Install dependencies
poetry install --with dev,test,docs

# 5. Activate environment
poetry shell
```

### Daily Development

```bash
# Start your day
cd nexus
poetry shell  # or use 'poetry run' prefix

# Run the application
poetry run python app/main.py

# Run tests
poetry run pytest
poetry run pytest --cov

# Format code
poetry run black .
poetry run isort .

# Type checking
poetry run mypy app/

# Run pre-commit hooks
poetry run pre-commit run --all-files
```

### Plugin Development

```bash
# Navigate to plugin
cd app/plugins/my_plugin

# Install plugin dependencies
poetry install

# Add new dependency
poetry add aiohttp

# Test plugin
poetry run pytest tests/

# Build plugin
poetry build
```

### Version Management

```bash
# Bump version (patch)
poetry version patch  # 1.0.0 -> 1.0.1

# Bump version (minor)
poetry version minor  # 1.0.0 -> 1.1.0

# Bump version (major)
poetry version major  # 1.0.0 -> 2.0.0

# Set specific version
poetry version 2.1.0

# Show current version
poetry version --short
```

## Publishing Packages

### Publishing to PyPI

#### Configure Credentials
```bash
# Configure PyPI token
poetry config pypi-token.pypi your-token-here

# Or use username/password (not recommended)
poetry config http-basic.pypi username password
```

#### Build and Publish
```bash
# Build package
poetry build

# Publish to PyPI
poetry publish

# Build and publish in one command
poetry publish --build

# Dry run (test without publishing)
poetry publish --dry-run
```

### Publishing to Private Repository

```bash
# Add private repository
poetry config repositories.private https://private.pypi.org/simple/

# Configure credentials
poetry config http-basic.private username password

# Publish to private repository
poetry publish -r private
```

## Best Practices

### 1. Lock File Management

**Always commit `poetry.lock`**:
```bash
# After adding/updating dependencies
git add poetry.lock pyproject.toml
git commit -m "chore: update dependencies"
```

**Keep lock file updated**:
```bash
# Regularly update dependencies
poetry update
poetry show --outdated
```

### 2. Dependency Groups

**Organize dependencies logically**:
```toml
[tool.poetry.dependencies]
# Core dependencies only

[tool.poetry.group.dev.dependencies]
# Development tools

[tool.poetry.group.test.dependencies]
# Testing tools

[tool.poetry.group.docs.dependencies]
# Documentation tools

[tool.poetry.extras]
# Optional features
```

### 3. Version Constraints

**Use appropriate constraints**:
```toml
# Caret: Allow minor updates
fastapi = "^0.109.0"  # >=0.109.0, <0.110.0

# Tilde: Allow patch updates
pydantic = "~2.5.3"  # >=2.5.3, <2.6.0

# Exact: Pin specific version
critical-package = "==1.2.3"

# Range: Custom range
sqlalchemy = ">=2.0,<3.0"
```

### 4. Plugin Independence

**Plugins should not depend on nexus-framework**:
```toml
# ❌ Wrong
[tool.poetry.dependencies]
nexus-framework = "^2.0.0"

# ✅ Correct - Nexus is expected to be installed separately
[tool.poetry.dependencies]
# Plugin-specific dependencies only
redis = "^5.0.1"
```

### 5. CI/CD Integration

**GitHub Actions example**:
```yaml
- name: Install Poetry
  uses: snok/install-poetry@v1
  with:
    virtualenvs-in-project: true

- name: Load cached venv
  uses: actions/cache@v3
  with:
    path: .venv
    key: venv-${{ runner.os }}-${{ hashFiles('**/poetry.lock') }}

- name: Install dependencies
  run: poetry install --no-interaction --no-root

- name: Run tests
  run: poetry run pytest
```

## Common Commands

### Essential Commands

```bash
# Project setup
poetry new project-name       # Create new project
poetry init                   # Initialize in existing project
poetry install               # Install dependencies
poetry shell                 # Activate virtual environment

# Dependency management
poetry add package           # Add dependency
poetry remove package        # Remove dependency
poetry update               # Update all dependencies
poetry lock                 # Update lock file
poetry show                 # Show installed packages
poetry show --tree          # Show dependency tree
poetry show --outdated      # Show outdated packages

# Running commands
poetry run python script.py  # Run Python script
poetry run pytest           # Run tests
poetry run command          # Run any command

# Building and publishing
poetry build                # Build package
poetry publish              # Publish to PyPI
poetry version             # Show/update version

# Configuration
poetry config --list        # Show configuration
poetry env info            # Show environment info
poetry env list            # List environments
poetry env remove python   # Remove environment
```

### Useful Aliases

Add to your shell configuration:
```bash
alias poa='poetry add'
alias por='poetry remove'
alias pou='poetry update'
alias pos='poetry show'
alias posh='poetry shell'
alias por='poetry run'
alias pot='poetry run pytest'
alias pob='poetry build'
```

## Troubleshooting

### Common Issues

#### 1. Virtual Environment Not Found
```bash
# Recreate virtual environment
poetry env remove python
poetry install
```

#### 2. Dependency Conflicts
```bash
# Clear cache and reinstall
poetry cache clear --all pypi
poetry lock --no-update
poetry install
```

#### 3. Lock File Out of Sync
```bash
# Regenerate lock file
rm poetry.lock
poetry lock
poetry install
```

#### 4. SSL Certificate Issues
```bash
# Temporary workaround (not for production)
poetry config certificates.insecure-host.pypi.org true
```

#### 5. Permission Errors
```bash
# Install to user directory
curl -sSL https://install.python-poetry.org | python3 - --git https://github.com/python-poetry/poetry.git@master
```

### Getting Help

```bash
# Show help
poetry --help
poetry add --help

# Check Poetry version
poetry --version

# Self update
poetry self update

# Verbose output for debugging
poetry -vvv install
```

## Migration from pip

### Converting requirements.txt

```bash
# Manual conversion
cat requirements.txt | xargs poetry add

# With development dependencies
cat dev-requirements.txt | xargs poetry add --group dev
```

### Export to requirements.txt

```bash
# Export production dependencies
poetry export -f requirements.txt --output requirements.txt

# Export with dev dependencies
poetry export -f requirements.txt --with dev --output requirements-dev.txt

# Export without hashes (for compatibility)
poetry export -f requirements.txt --without-hashes --output requirements.txt
```

## Resources

- **Poetry Documentation**: https://python-poetry.org/docs/
- **Poetry GitHub**: https://github.com/python-poetry/poetry
- **Nexus Framework**: https://nexus-framework.dev
- **Community Discord**: https://discord.gg/nexus-framework

---

With Poetry, the Nexus Framework provides a modern, reliable dependency management system that ensures reproducible builds and simplifies the development workflow for both the core framework and plugins.