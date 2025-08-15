# Contributing to Nexus Framework

First off, thank you for considering contributing to Nexus Framework! It's people like you that make Nexus Framework such a great tool. We welcome contributions from everyone, regardless of their level of experience.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Pull Request Process](#pull-request-process)
- [Issue Guidelines](#issue-guidelines)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Community](#community)
- [Recognition](#recognition)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](./COMMUNITY.md#code-of-conduct). By participating, you are expected to uphold this code. Please report unacceptable behavior to conduct@nexus-framework.dev.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When you create a bug report, include as many details as possible using the required template.

**Great Bug Reports** tend to have:
- A quick summary and/or background
- Steps to reproduce
  - Be specific!
  - Provide sample code if possible
- What you expected would happen
- What actually happens
- Notes (possibly including why you think this might be happening)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, include:
- Use a clear and descriptive title
- Provide a step-by-step description of the suggested enhancement
- Provide specific examples to demonstrate the steps
- Describe the current behavior and explain which behavior you expected to see instead
- Explain why this enhancement would be useful

### Your First Code Contribution

Unsure where to begin? You can start by looking through these issues:
- `good-first-issue` - issues which should only require a few lines of code
- `help-wanted` - issues which need extra attention
- `documentation` - issues related to documentation

### Pull Requests

The process described here has several goals:
- Maintain Nexus Framework's quality
- Fix problems that are important to users
- Engage the community in working toward the best possible Nexus Framework
- Enable a sustainable system for maintainers to review contributions

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Git
- PostgreSQL/MongoDB (optional, SQLite works for development)
- Redis (optional for caching)
- Node.js (for building documentation)

### Setting Up Your Development Environment

1. **Fork the Repository**
   ```bash
   # Fork via GitHub UI, then clone your fork
   git clone https://github.com/YOUR-USERNAME/nexus.git
   cd nexus
   ```

2. **Set Up Python Environment**
   ```bash
   # Create virtual environment
   python -m venv venv
   
   # Activate virtual environment
   # On Linux/Mac:
   source venv/bin/activate
   # On Windows:
   # venv\Scripts\activate
   
   # Install development dependencies
   pip install -e ".[dev]"
   ```

3. **Set Up Pre-commit Hooks**
   ```bash
   # Install pre-commit hooks
   pre-commit install
   
   # Run hooks on all files (optional)
   pre-commit run --all-files
   ```

4. **Configure Environment**
   ```bash
   # Copy example environment file
   cp .env.example .env
   
   # Edit .env with your settings
   # Required: DATABASE_URL, REDIS_URL (if using Redis)
   ```

5. **Run Tests**
   ```bash
   # Run all tests
   pytest
   
   # Run with coverage
   pytest --cov=nexus --cov-report=html
   
   # Run specific test file
   pytest tests/test_plugins.py
   
   # Run with verbose output
   pytest -v
   ```

6. **Start Development Server**
   ```bash
   # Run the development server
   python -m nexus.dev
   
   # Or with hot reload
   uvicorn nexus.main:app --reload
   ```

## Development Workflow

### 1. Create a Branch

```bash
# Create and checkout a new branch
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
# or
git checkout -b docs/documentation-update
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the coding standards
- Add or update tests as needed
- Update documentation if necessary

### 3. Test Your Changes

```bash
# Run tests
pytest

# Run linting
flake8 nexus/
black --check nexus/
mypy nexus/

# Run security checks
bandit -r nexus/
safety check
```

### 4. Commit Your Changes

```bash
# Stage your changes
git add .

# Commit with a descriptive message
git commit -m "feat: add new plugin authentication method"
```

### 5. Push and Create Pull Request

```bash
# Push to your fork
git push origin feature/your-feature-name

# Create pull request via GitHub UI
```

## Coding Standards

### Python Style Guide

We follow PEP 8 with some modifications:
- Line length: 88 characters (Black's default)
- Use type hints for all public functions
- Use docstrings for all public modules, functions, classes, and methods

### Code Style Example

```python
from typing import Optional, List, Dict, Any
from nexus.core import Plugin
import logging

logger = logging.getLogger(__name__)


class ExamplePlugin(Plugin):
    """
    Example plugin demonstrating coding standards.
    
    This plugin shows how to properly structure and document
    a Nexus Framework plugin following our coding standards.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None) -> None:
        """
        Initialize the example plugin.
        
        Args:
            config: Optional configuration dictionary
        """
        super().__init__(config)
        self.name = "example"
        self.version = "1.0.0"
    
    async def process_data(
        self,
        data: List[Dict[str, Any]],
        validate: bool = True
    ) -> Dict[str, Any]:
        """
        Process incoming data.
        
        Args:
            data: List of data items to process
            validate: Whether to validate data before processing
            
        Returns:
            Processed data results
            
        Raises:
            ValidationError: If validation fails
            ProcessingError: If processing encounters an error
        """
        if validate:
            self._validate_data(data)
        
        try:
            results = await self._process_items(data)
            return {"status": "success", "results": results}
        except Exception as e:
            logger.error(f"Processing failed: {e}")
            raise ProcessingError(f"Failed to process data: {e}")
    
    def _validate_data(self, data: List[Dict[str, Any]]) -> None:
        """Validate input data."""
        # Private method - shorter docstring is acceptable
        for item in data:
            if "id" not in item:
                raise ValidationError("Missing required field: id")
```

### Import Order

1. Standard library imports
2. Third-party imports
3. Nexus framework imports
4. Local application imports

```python
# Standard library
import os
import sys
from datetime import datetime
from typing import Optional, List

# Third-party
import asyncio
from fastapi import FastAPI
from pydantic import BaseModel

# Nexus framework
from nexus.core import Plugin
from nexus.database import Repository

# Local application
from .models import User
from .utils import helpers
```

## Testing Guidelines

### Test Structure

```python
import pytest
from unittest.mock import Mock, AsyncMock
from nexus.plugins import ExamplePlugin


class TestExamplePlugin:
    """Test suite for ExamplePlugin."""
    
    @pytest.fixture
    def plugin(self):
        """Create plugin instance for testing."""
        return ExamplePlugin({"test": True})
    
    @pytest.fixture
    def mock_database(self):
        """Create mock database for testing."""
        db = Mock()
        db.fetch = AsyncMock(return_value=[])
        return db
    
    async def test_plugin_initialization(self, plugin):
        """Test plugin initializes correctly."""
        assert plugin.name == "example"
        assert plugin.version == "1.0.0"
        assert plugin.config["test"] is True
    
    async def test_data_processing_success(self, plugin, mock_database):
        """Test successful data processing."""
        plugin.database = mock_database
        data = [{"id": "1", "value": "test"}]
        
        result = await plugin.process_data(data)
        
        assert result["status"] == "success"
        mock_database.fetch.assert_called_once()
    
    @pytest.mark.parametrize("invalid_data", [
        [],
        [{"value": "missing_id"}],
        None,
    ])
    async def test_data_validation_failure(self, plugin, invalid_data):
        """Test data validation with invalid inputs."""
        with pytest.raises(ValidationError):
            await plugin.process_data(invalid_data)
```

### Test Requirements

- All new features must include tests
- All bug fixes should include a test that reproduces the issue
- Maintain test coverage above 80%
- Use meaningful test names that describe what is being tested
- Use fixtures for common test setup
- Mock external dependencies

## Documentation

### Documentation Standards

- Use clear, concise language
- Include code examples where appropriate
- Keep documentation up-to-date with code changes
- Use proper markdown formatting
- Include diagrams for complex concepts

### Docstring Format

We use Google-style docstrings:

```python
def example_function(param1: str, param2: int = 0) -> Dict[str, Any]:
    """
    Brief description of function.
    
    Longer description if needed, explaining in more detail what
    the function does and any important information.
    
    Args:
        param1: Description of param1
        param2: Description of param2, defaults to 0
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param1 is empty
        TypeError: When param2 is not an integer
        
    Example:
        >>> result = example_function("test", 42)
        >>> print(result)
        {"status": "success", "value": 42}
    """
    pass
```

## Pull Request Process

### Before Submitting

1. **Update Documentation** - Make sure any new features are documented
2. **Add Tests** - Ensure all new code is tested
3. **Run Full Test Suite** - `pytest` should pass
4. **Check Code Style** - `black`, `flake8`, and `mypy` should pass
5. **Update CHANGELOG** - Add your changes to CHANGELOG.md
6. **Rebase if Needed** - Keep your branch up-to-date with main

### Pull Request Template

```markdown
## Description
Brief description of what this PR does

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)
- [ ] Documentation update

## Testing
- [ ] All tests pass locally
- [ ] Added new tests for new functionality
- [ ] Updated existing tests as needed

## Checklist
- [ ] My code follows the project's style guidelines
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have made corresponding changes to the documentation
- [ ] My changes generate no new warnings
- [ ] Any dependent changes have been merged and published

## Related Issues
Fixes #(issue number)

## Screenshots (if applicable)
Add screenshots to help explain your changes
```

### Review Process

1. **Automated Checks** - CI/CD runs tests, linting, and security checks
2. **Code Review** - At least one maintainer reviews the code
3. **Discussion** - Address any feedback or questions
4. **Approval** - Maintainer approves the PR
5. **Merge** - PR is merged into main branch

## Issue Guidelines

### Creating Issues

Use the appropriate issue template:
- **Bug Report** - For reporting bugs
- **Feature Request** - For suggesting new features
- **Documentation** - For documentation improvements
- **Question** - For questions about the project

### Issue Labels

- `bug` - Something isn't working
- `enhancement` - New feature or request
- `documentation` - Improvements or additions to documentation
- `good-first-issue` - Good for newcomers
- `help-wanted` - Extra attention is needed
- `invalid` - This doesn't seem right
- `question` - Further information is requested
- `wontfix` - This will not be worked on
- `duplicate` - This issue or pull request already exists

## Commit Message Guidelines

We follow the Conventional Commits specification:

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat` - A new feature
- `fix` - A bug fix
- `docs` - Documentation only changes
- `style` - Changes that don't affect code meaning (formatting, etc.)
- `refactor` - Code change that neither fixes a bug nor adds a feature
- `perf` - Performance improvement
- `test` - Adding or updating tests
- `build` - Changes that affect the build system
- `ci` - Changes to CI configuration files and scripts
- `chore` - Other changes that don't modify src or test files

### Examples

```bash
# Feature
feat(plugins): add plugin hot-reload capability

# Bug fix
fix(auth): resolve token expiration issue

# Documentation
docs(api): update API documentation for v2 endpoints

# Performance
perf(database): optimize query for large datasets

# With scope and breaking change
feat(api)!: change authentication endpoint structure

BREAKING CHANGE: Authentication endpoint moved from /auth to /api/v2/auth
```

## Community

### Getting Help

- **Discord**: Join our [Discord server](https://discord.gg/nexus-framework)
- **Forum**: Visit our [community forum](https://community.nexus-framework.dev)
- **Stack Overflow**: Use tag `nexus-framework`

### Staying Updated

- **Blog**: Read our [blog](https://blog.nexus-framework.dev)
- **Newsletter**: Subscribe to our [newsletter](https://newsletter.nexus-framework.dev)
- **Twitter**: Follow [@NexusFramework](https://twitter.com/NexusFramework)

## Recognition

### Contributors

All contributors are recognized in:
- README.md contributors section
- Website contributors page
- Release notes
- Annual community report

### Rewards

Active contributors receive:
- Nexus Framework swag
- Conference tickets
- Special Discord roles
- Invitation to contributor events

## Thank You!

Your contributions to open source, no matter how small, make projects like Nexus Framework possible. Thank you for taking the time to contribute!

---

<div align="center">
  <strong>Happy Contributing! 🎉</strong>
  <br>
  <sub>The Nexus Framework Team</sub>
</div>