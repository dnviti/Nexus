# Development Scripts

Essential development tools for the Nexus Framework.

## Scripts Overview

| Script               | Purpose                    | Usage                                                        |
| -------------------- | -------------------------- | ------------------------------------------------------------ |
| `pre_push_check.py`  | Pre-push validation        | `python scripts/pre_push_check.py [--fix] [--fast]`          |
| `pre-push-check.sh`  | Bash pre-push validation   | `./scripts/pre-push-check.sh [--fix] [--fast]`               |
| `test_ci_locally.py` | Local CI simulation        | `python scripts/test_ci_locally.py [--fast] [--verbose]`     |
| `check_services.py`  | Service connectivity check | `python scripts/check_services.py --services redis postgres` |

## Quick Start

### Pre-Push Validation

```bash
# Quick check during development
python scripts/pre_push_check.py --fast

# Full validation before pushing
python scripts/pre_push_check.py

# Auto-fix issues
python scripts/pre_push_check.py --fix
```

### Local CI Testing

```bash
# Fast development check
python scripts/test_ci_locally.py --fast

# Complete CI simulation
python scripts/test_ci_locally.py

# Debug mode with detailed output
python scripts/test_ci_locally.py --verbose
```

## What Gets Checked

**On Every Commit (Full Check):**

- ✅ **Code Formatting** (Black)
- ✅ **Import Sorting** (isort)
- ✅ **Linting** (Flake8)
- ✅ **Type Checking** (MyPy)
- ✅ **Security Scan** (Bandit)
- ✅ **Tests** (496 unit + 16 integration)
- ✅ **Coverage** (>80% required)
- ✅ **Package Build** (Poetry)

## Performance

| Mode     | Duration | Coverage | Use Case               |
| -------- | -------- | -------- | ---------------------- |
| **Fast** | ~30s     | ❌       | Development iteration  |
| **Full** | ~60s     | ✅       | Auto-commit & pre-push |

**Note:** Git commits automatically run full checks for maximum quality assurance.

## Setup

### Automatic Git Hooks

The pre-push script automatically sets up git hooks that run **full validation** on every commit.

```bash
python scripts/pre_push_check.py  # Sets up hooks automatically
```

**What happens on commit:**

- Full code quality checks (Black, isort, Flake8, MyPy)
- Security scan (Bandit)
- Complete test suite with coverage
- Build validation

### Manual Setup

```bash
# Make scripts executable
chmod +x scripts/pre-push-check.sh

# Install dependencies
poetry install --with dev,test
```

## Troubleshooting

### Common Issues

**Poetry not found:**

```bash
curl -sSL https://install.python-poetry.org | python3 -
```

**Permission denied:**

```bash
chmod +x scripts/pre-push-check.sh
```

**Tests failing:**

```bash
# Run locally to debug
python scripts/test_ci_locally.py --verbose
```

### Getting Help

1. Run with `--verbose` for detailed output
2. Check `.github/TROUBLESHOOTING.md`
3. Create GitHub issue with logs if needed

## Requirements

- Python 3.11+
- Poetry (latest)
- Git (any recent version)

## Examples

```bash
# Development workflow
make dev-setup              # Initial setup
make fast-check             # Quick validation during development
make fix                    # Auto-fix issues
git commit                  # Triggers full validation automatically
git push                    # Ready to push after commit validation

# Direct script usage
python scripts/pre_push_check.py --fast --fix  # Quick dev check
python scripts/pre_push_check.py               # Full check (runs on commit)
python scripts/test_ci_locally.py --fast
./scripts/pre-push-check.sh --help
```
