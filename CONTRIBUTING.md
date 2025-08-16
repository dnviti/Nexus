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
poetry install

# Run tests
poetry run pytest

# Start development server
python main.py
```

## Development Guidelines

### Code Style

- Follow PEP 8
- Use type hints
- Write docstrings for public methods
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