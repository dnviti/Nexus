# CI/CD Troubleshooting Guide

Quick reference for resolving common CI/CD issues in the Nexus Framework.

## Common Errors

### "Resource not accessible by integration"

**Cause:** GitHub Actions permissions issue, typically with fork PRs or security actions.

**Fix:**

```yaml
# Add to workflow file
permissions:
  contents: read
  issues: write
  pull-requests: write
  checks: write
  security-events: write
```

**For fork PRs, use:**

```yaml
if: github.event_name != 'pull_request' || github.event.pull_request.head.repo.full_name == github.repository
```

### Poetry Installation Failed

**Windows:**

```bash
# Use PowerShell
poetry config virtualenvs.create true
poetry config virtualenvs.in-project true
poetry config virtualenvs.path .venv
```

**Unix/macOS:**

```bash
python -m pip install --upgrade pip
python -m pip install poetry
```

### Tests Hanging/Timeout

**Solution:**

```bash
# Set environment variables
export PYTHONASYNCIODEBUG=1
export PYTHONHASHSEED=0

# Use proper pytest flags
pytest --asyncio-mode=auto --timeout=300
```

### Cache Issues

**Fix:**

```bash
# Clear Poetry cache
poetry cache clear --all pypi
rm -rf .venv
poetry install
```

### Local Testing

### Development Workflow

```bash
# Quick check during development
python scripts/test_ci_locally.py --fast

# Full check (same as git commit)
python scripts/test_ci_locally.py

# Auto-commit with full validation
git commit -m "Your changes"  # Runs full check automatically
```

### Manual Commands

```bash
# Code quality (runs on every commit)
poetry run black --check nexus/ tests/
poetry run isort --check-only nexus/ tests/
poetry run flake8 nexus/ tests/
poetry run mypy nexus/

# Tests (runs on every commit)
poetry run pytest tests/ --cov=nexus

# Security (runs on every commit)
poetry run bandit -r nexus/
```

## Emergency Fixes

### Disable Failing Job

```yaml
jobs:
  failing-job:
    if: false # Temporarily disable
```

### Skip Non-Critical Steps

```yaml
continue-on-error: true
```

### Fork PR Issues

Fork PRs have limited permissions by design. Maintainers should:

1. Review the changes
2. Re-run workflows if needed
3. Merge when ready

**Note:** All commits are validated with full checks automatically via git hooks.

## Getting Help

1. Check this guide first
2. Test locally with `python scripts/test_ci_locally.py`
3. Create GitHub issue with logs if problem persists
4. Tag maintainers for urgent issues
