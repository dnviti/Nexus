# Contributing to Nexus

We welcome contributions! Here's how to get involved.

## Quick Start

```bash
# Fork and clone
git clone https://github.com/your-username/nexus.git
cd nexus

# Setup development environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
poetry install --with dev,test

# IMPORTANT: Set up git hooks for quality assurance
python scripts/pre_push_check.py

# Verify setup
python scripts/test_ci_locally.py --fast

# Run tests
poetry run pytest

# Start development server
python main.py
```

## ⚠️ IMPORTANT: Quality Assurance Setup

**ALL CONTRIBUTORS must set up git hooks to ensure code quality and reduce CI failures.**

### Automatic Setup (Recommended)

```bash
python scripts/pre_push_check.py  # Sets up pre-commit hooks automatically
```

### Manual Setup

```bash
git config core.hooksPath .githooks
chmod +x .githooks/*
```

### What Hooks Validate on Each Commit

- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (Flake8)
- ✅ Type checking (MyPy)
- ✅ Security scanning (Bandit)
- ✅ Full test suite (496 unit + 16 integration tests)
- ✅ Code coverage analysis
- ✅ Build validation

**Benefits:**

- Catches issues early (before CI)
- Maintains consistent code quality
- Reduces development friction
- Speeds up review process

See [`.githooks/README.md`](.githooks/README.md) for detailed documentation.

## Development Workflow

### Recommended Process

```bash
# Quick development validation (during coding)
python scripts/pre_push_check.py --fast

# Make your changes...

# Commit changes (triggers full validation automatically)
git add .
git commit -m "Meaningful commit message"

# Push after successful validation
git push
```

### Development Commands

```bash
# Fast check during development
make fast-check
python scripts/pre_push_check.py --fast

# Auto-fix formatting issues
python scripts/pre_push_check.py --fix

# Full local CI simulation
python scripts/test_ci_locally.py

# Run specific checks
poetry run black nexus/ tests/     # Format code
poetry run isort nexus/ tests/     # Sort imports
poetry run flake8 nexus/ tests/    # Lint code
poetry run mypy nexus/             # Type check
poetry run pytest tests/           # Run tests
```

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public methods
- All commits must pass pre-commit hooks
- Maximum line length: 100 characters

```bash
# Format code
poetry run black nexus/
poetry run isort nexus/

# Check types
poetry run mypy nexus/
```

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=nexus

# Run specific test
poetry run pytest tests/test_core.py::test_plugin_loading
```

### Plugin Development

```bash
# Create new plugin
nexus plugin create test_plugin

# Test plugin
poetry run pytest plugins/test_plugin/tests/
```

## Contribution Process

### 1. Create Issue

- Bug reports: Include steps to reproduce
- Feature requests: Describe use case and benefits
- Questions: Use Discussions instead

### 2. Fork & Branch

```bash
git checkout -b feature/my-awesome-feature
git checkout -b bugfix/fix-plugin-loading
```

### 3. Make Changes

- Write tests for new features
- Update documentation if needed
- Follow coding standards

### 4. Submit Pull Request

- Clear title and description
- Link related issues
- Include test results
- Update CHANGELOG.md

## Pull Request Template

```markdown
## Description

Brief description of changes

## Type of Change

- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing

- [ ] Tests pass locally
- [ ] New tests added for features
- [ ] Manual testing completed

## Checklist

- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] CHANGELOG.md updated
```

## Documentation

### API Documentation

```bash
# Generate docs
poetry run mkdocs build

# Serve locally
poetry run mkdocs serve
```

### Writing Guidelines

- Use clear, concise language
- Include code examples
- Add Mermaid diagrams for complex concepts
- Test all examples

## Architecture Decisions

### Plugin System

- Each plugin must be self-contained
- Use event bus for communication
- Avoid direct plugin-to-plugin dependencies

### Database Changes

- Create migrations for schema changes
- Support multiple database backends
- Test with SQLite for development

### API Design

- Follow REST conventions
- Use OpenAPI documentation
- Maintain backward compatibility

## Release Process

### Version Numbers

- Follow semantic versioning (MAJOR.MINOR.PATCH)
- Breaking changes increment MAJOR
- New features increment MINOR
- Bug fixes increment PATCH

### Release Checklist

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release branch
4. Run full test suite
5. Create GitHub release
6. Publish to PyPI

## Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: Questions and community chat
- **Discord**: Real-time community support

## Code of Conduct

### Our Standards

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain professional communication

### Enforcement

Report issues to the maintainers. All reports will be handled confidentially.

---

Thank you for contributing to Nexus! 🚀
