# Nexus Framework - Development Scripts

This directory contains development scripts and tools for the Nexus Framework project.

## 📁 Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `pre_push_check.py` | **Python Pre-Push Validator** | `python scripts/pre_push_check.py [--fix] [--fast]` |
| `pre-push-check.sh` | **Bash Pre-Push Validator** | `./scripts/pre-push-check.sh [--fix] [--fast]` |
| `check_services.py` | **Service Connectivity Checker** | `python scripts/check_services.py --services redis postgres` |

## 🚀 Pre-Push Validation Scripts

The pre-push validation scripts run all CI/CD pipeline checks locally before pushing to git, ensuring code quality and preventing CI failures.

### Python Script (Recommended)

**Cross-platform Python implementation with full feature support:**

```bash
# Run all checks
python scripts/pre_push_check.py

# Auto-fix formatting and imports
python scripts/pre_push_check.py --fix

# Quick validation (skips coverage and security)
python scripts/pre_push_check.py --fast

# Quick fix and check
python scripts/pre_push_check.py --fix --fast

# Show help
python scripts/pre_push_check.py --help
```

### Bash Script (Unix/Linux/macOS)

**Bash implementation for Unix-like systems:**

```bash
# Run all checks
./scripts/pre-push-check.sh

# Auto-fix formatting and imports
./scripts/pre-push-check.sh --fix

# Quick validation
./scripts/pre-push-check.sh --fast

# Show help
./scripts/pre-push-check.sh --help
```

## 🔍 What the Pre-Push Scripts Check

### Code Quality Pipeline
- ✅ **Code Formatting** (Black)
- ✅ **Import Sorting** (isort)
- ✅ **Linting** (Flake8)
- ✅ **Type Checking** (MyPy)
- ✅ **Security Scan** (Bandit)

### Test Pipeline
- ✅ **Unit Tests** (496 tests)
- ✅ **Integration Tests** (16 tests)
- ✅ **Code Coverage** (>80% required)

### Build Pipeline
- ✅ **Package Build** (Poetry)
- ✅ **Package Validation** (Twine)

### Additional Checks
- ✅ **Git Status Check**
- ✅ **Dependency Validation**
- ✅ **Project Metrics**
- ✅ **Git Hooks Setup**

## 🛠️ Service Connectivity Checker

Checks availability of external services required for integration tests.

```bash
# Check all services
python scripts/check_services.py

# Check specific services
python scripts/check_services.py --services redis postgres

# Custom configuration
python scripts/check_services.py --services mysql --max-attempts 60 --interval 1 --timeout 10
```

**Supported Services:**
- **Redis** (port 6379)
- **PostgreSQL** (port 5432)
- **MySQL** (port 3306)

## 🔧 Integration with Development Workflow

### Makefile Integration

The scripts integrate seamlessly with the project Makefile:

```bash
# Use pre-push scripts via Makefile
make pre-push         # Full validation
make fast-check       # Quick validation
make fix              # Auto-fix issues
```

### Git Hooks Integration

The scripts automatically set up git hooks:

```bash
# Pre-commit hook is automatically configured
git commit   # Runs fast validation automatically
```

**Manual hook setup:**
```bash
# Create pre-commit hook
echo '#!/bin/bash' > .git/hooks/pre-commit
echo 'python scripts/pre_push_check.py --fast' >> .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

### IDE Integration

#### VSCode Integration

Add to your `.vscode/tasks.json`:

```json
{
    "version": "2.0.0",
    "tasks": [
        {
            "label": "Nexus: Pre-Push Check",
            "type": "shell",
            "command": "python",
            "args": ["scripts/pre_push_check.py"],
            "group": "build",
            "presentation": {
                "echo": true,
                "reveal": "always",
                "focus": false,
                "panel": "shared"
            },
            "problemMatcher": []
        },
        {
            "label": "Nexus: Quick Fix",
            "type": "shell",
            "command": "python",
            "args": ["scripts/pre_push_check.py", "--fix", "--fast"],
            "group": "build"
        }
    ]
}
```

#### IntelliJ/PyCharm Integration

1. **Run Configuration:**
   - **Script Path:** `scripts/pre_push_check.py`
   - **Parameters:** `--fast`
   - **Working Directory:** Project root

2. **External Tools:**
   - **Program:** `python`
   - **Arguments:** `scripts/pre_push_check.py --fix`
   - **Working Directory:** `$ProjectFileDir$`

## 📊 Output and Reports

### Successful Run Example

```
🚀 Nexus Framework - Pre-Push Validation
Started at: 2025-08-17 15:40:11
Mode: Check-only

=====================================
 CODE QUALITY CHECKS
=====================================
✅ Code formatting is correct
✅ Import sorting is correct
✅ No critical lint issues found
✅ Type checking passed
✅ No security issues found

=====================================
 TEST SUITE
=====================================
✅ Unit tests passed (496/496)
✅ Integration tests passed (16/16)

=====================================
 BUILD & PACKAGE
=====================================
✅ Package built successfully
✅ Package integrity verified

=====================================
 SUMMARY
=====================================
✅ All checks passed! ✨
✅ Ready to push to git! 🚀

Next steps:
  git add .
  git commit -m "Your commit message"
  git push
```

### Generated Reports

The scripts generate several reports:

- **`coverage.xml`** - Coverage report (XML format)
- **`htmlcov/`** - Coverage report (HTML format)
- **`bandit-report.json`** - Security scan results
- **`dist/`** - Built packages

## ⚡ Performance and Speed

### Timing Comparison

| Mode | Duration | Coverage | Security Scan |
|------|----------|----------|---------------|
| **Full** | ~60s | ✅ | ✅ |
| **Fast** | ~30s | ❌ | ❌ |
| **Fix Mode** | ~45s | Depends | Depends |

### Speed Optimization Tips

1. **Use Fast Mode for Development:**
   ```bash
   python scripts/pre_push_check.py --fast
   ```

2. **Use Fix Mode When Needed:**
   ```bash
   python scripts/pre_push_check.py --fix --fast
   ```

3. **Parallel Test Execution:**
   The scripts automatically use optimal pytest settings for speed.

## 🐛 Troubleshooting

### Common Issues

#### Poetry Not Found
```bash
# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -
# Or via pip
pip install poetry
```

#### Permission Denied (Bash Script)
```bash
chmod +x scripts/pre-push-check.sh
```

#### Python Version Issues
```bash
# Check Python version (requires 3.11+)
python --version

# Use specific Python version
python3.11 scripts/pre_push_check.py
```

#### Git Hooks Not Working
```bash
# Manually set up hooks
python scripts/pre_push_check.py  # This will configure hooks automatically
```

### Debugging Mode

Enable verbose output for debugging:

```bash
# Python script with debugging
python -v scripts/pre_push_check.py

# Manual step-by-step debugging
make format-check  # Check formatting only
make lint          # Check linting only
make type-check    # Check types only
make test-fast     # Run tests only
```

### Skip Specific Checks

If you need to skip specific checks temporarily:

```bash
# Skip security scan
python scripts/pre_push_check.py --fast

# Manual component testing
poetry run black --check nexus/ tests/     # Format check only
poetry run isort --check nexus/ tests/     # Import check only
poetry run flake8 nexus/ tests/            # Lint check only
poetry run mypy nexus/                     # Type check only
poetry run pytest tests/unit/ --maxfail=1  # Quick test
```

## 📋 Requirements

### System Requirements
- **Python:** 3.11+ (required)
- **Poetry:** Latest version (required)
- **Git:** Any modern version (required)
- **Unix Tools:** For bash script (optional)

### Python Dependencies
All dependencies are managed via Poetry and installed automatically:
- **Testing:** pytest, pytest-cov, pytest-asyncio
- **Quality:** black, isort, flake8, mypy
- **Security:** bandit
- **Build:** twine

## 🔗 Related Documentation

- **[Main README](../README.md)** - Project overview
- **[Contributing Guide](../CONTRIBUTING.md)** - Development guidelines
- **[Makefile](../Makefile)** - Development commands
- **[pyproject.toml](../pyproject.toml)** - Project configuration

## 💡 Tips and Best Practices

### Development Workflow

1. **Start Development:**
   ```bash
   make dev-setup  # Initial setup
   ```

2. **During Development:**
   ```bash
   make fast-check  # Quick validation
   make fix         # Auto-fix issues
   ```

3. **Before Committing:**
   ```bash
   make pre-push    # Full validation
   ```

4. **Emergency Fixes:**
   ```bash
   python scripts/pre_push_check.py --fix --fast
   ```

### Continuous Integration

The scripts mirror the CI pipeline exactly:

```yaml
# .github/workflows/main.yml equivalent
- Code Quality: ✅ (Black, isort, Flake8, MyPy, Bandit)
- Tests: ✅ (Unit + Integration with coverage)
- Build: ✅ (Package build and validation)
```

### Team Collaboration

**Recommended team workflow:**

1. **Onboarding:** New developers run `make dev-setup`
2. **Daily Development:** Use `make fast-check` frequently
3. **Pre-Commit:** Git hooks run automatically
4. **Pre-Push:** Manual `make pre-push` for final validation
5. **CI/CD:** Pipeline matches local checks exactly

---

**📧 Need Help?** Check the [main project README](../README.md) or open an issue on GitHub.
