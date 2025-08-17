# Git Hooks for Nexus Framework

This directory contains git hooks that ensure code quality and consistency across the Nexus Framework project.

## Overview

The hooks in this directory provide automatic validation during git operations to catch issues early and maintain high code quality standards.

## Available Hooks

### `pre-commit`

Runs comprehensive validation before each commit:

- ✅ Code formatting (Black)
- ✅ Import sorting (isort)
- ✅ Linting (Flake8)
- ✅ Type checking (MyPy)
- ✅ Security scanning (Bandit)
- ✅ Full test suite (496 unit + 16 integration tests)
- ✅ Code coverage analysis
- ✅ Build validation

## Setup Instructions

### Option 1: Quick Setup Scripts (Recommended)

**Unix/Linux/macOS:**

```bash
.githooks/setup.sh
```

**Windows (PowerShell):**

```powershell
.githooks/setup.ps1
```

### Option 2: Python Script Setup

Run the pre-push check script which automatically configures hooks:

```bash
python scripts/pre_push_check.py
```

### Option 3: Manual Setup

Configure git to use the hooks from this directory:

```bash
# Set git hooks directory to use .githooks
git config core.hooksPath .githooks

# Make hooks executable (if needed)
chmod +x .githooks/*
```

### Option 4: Copy Individual Hooks

Copy specific hooks to your local `.git/hooks/` directory:

```bash
cp .githooks/pre-commit .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

## Verification

Test that hooks are working correctly:

```bash
# Test the pre-commit hook directly
.githooks/pre-commit

# Or make a test commit
echo "# Test" >> README.md
git add README.md
git commit -m "Test commit validation"
git reset HEAD~1  # Undo test commit
git restore README.md  # Restore file
```

## Development Workflow

### Recommended Development Process:

1. **Quick Development Checks:**

   ```bash
   python scripts/pre_push_check.py --fast  # Fast validation during development
   ```

2. **Commit Changes:**

   ```bash
   git add .
   git commit -m "Your commit message"  # Triggers full validation automatically
   ```

3. **Push Changes:**
   ```bash
   git push  # Already validated during commit
   ```

## Hook Behavior

### On Successful Validation:

- Commit proceeds normally
- All checks pass
- Ready to push

### On Failed Validation:

- Commit is blocked
- Detailed error messages displayed
- Suggestions for fixes provided

Example failure output:

```
❌ Pre-commit checks failed!
💡 Fix issues or run: python scripts/pre_push_check.py --fix
```

## Performance

| Operation              | Duration | Coverage | Security |
| ---------------------- | -------- | -------- | -------- |
| Pre-commit Hook        | ~60s     | ✅       | ✅       |
| Fast Development Check | ~30s     | ❌       | ❌       |

## Troubleshooting

### Hook Not Running

```bash
# Check if hooks path is configured
git config core.hooksPath

# Verify hook is executable
ls -la .githooks/pre-commit

# Test hook manually
.githooks/pre-commit
```

### Permission Issues

```bash
# Make hooks executable
chmod +x .githooks/*
```

### Python/Poetry Issues

```bash
# Ensure Poetry is installed and configured
poetry --version
poetry install --with dev,test
```

### Bypass Hook (Emergency Only)

```bash
# Skip validation (NOT RECOMMENDED)
git commit --no-verify -m "Emergency commit"
```

## Benefits

- **Early Error Detection**: Catch issues before they reach CI
- **Consistent Quality**: Every commit meets the same standards
- **Faster CI**: Reduced failures in continuous integration
- **Team Alignment**: Everyone uses the same validation process

## Integration with CI/CD

The hooks use the same validation as the CI pipeline, ensuring local and remote environments are synchronized:

- Same tools and versions
- Same configuration files
- Same validation criteria

## Support

For issues with git hooks:

1. Check `.github/TROUBLESHOOTING.md`
2. Run `python scripts/test_ci_locally.py --verbose` for debugging
3. Create a GitHub issue with hook output if problems persist

## Team Guidelines

### For New Contributors:

1. Clone the repository
2. Run setup script: `.githooks/setup.sh` (Unix) or `.githooks/setup.ps1` (Windows)
3. Alternative: `python scripts/pre_push_check.py` to set up hooks
4. Verify setup with a test commit

### For Maintainers:

1. Keep hooks updated with CI pipeline changes
2. Document any new validation requirements
3. Test hooks across different environments

---

**Note**: These hooks enforce the same quality standards as the CI pipeline. Following this setup reduces development friction and ensures consistent code quality across the project.
<!-- Git hooks setup completed -->
