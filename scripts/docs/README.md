# Documentation Management Scripts

This directory contains scripts to help manage the versioned documentation for the Nexus Platform.

## 📁 Scripts Overview

| Script | Purpose | Usage |
|--------|---------|-------|
| `manage_versions.py` | Core version management | Create, list, update, and remove documentation versions |
| `release.sh` | Release automation | Automated workflow for creating new documentation releases |
| `serve.sh` | Local development | Serve different documentation versions locally |

## 🚀 Quick Start

### Creating a New Documentation Version

```bash
# Simple version creation
./scripts/docs/release.sh v2.1.0

# Create and set as latest with build
./scripts/docs/release.sh v2.1.0 --set-latest --build

# Dry run to see what would happen
./scripts/docs/release.sh v2.1.0 --dry-run
```

### Local Development

```bash
# Serve latest stable version
./scripts/docs/serve.sh v2.0.0

# Serve development version
./scripts/docs/serve.sh dev

# Serve with live reload on custom port
./scripts/docs/serve.sh dev --port 8080 --reload
```

### Version Management

```bash
# List all versions
python scripts/docs/manage_versions.py list

# Create version manually
python scripts/docs/manage_versions.py create v2.1.0

# Set latest version
python scripts/docs/manage_versions.py set-latest v2.1.0

# Remove version
python scripts/docs/manage_versions.py remove v2.0.0
```

## 📋 Detailed Usage

### 1. `manage_versions.py` - Core Version Management

The Python script provides low-level version management functionality.

#### Commands

**Create a new version:**
```bash
python scripts/docs/manage_versions.py create <version> [--from <source_version>]
```

**List all versions:**
```bash
python scripts/docs/manage_versions.py list
```

**Set latest version:**
```bash
python scripts/docs/manage_versions.py set-latest <version>
```

**Remove a version:**
```bash
python scripts/docs/manage_versions.py remove <version>
```

**Build documentation:**
```bash
python scripts/docs/manage_versions.py build [version]
```

#### Examples

```bash
# Create v2.1.0 from latest
python scripts/docs/manage_versions.py create v2.1.0

# Create v2.1.0 from specific version
python scripts/docs/manage_versions.py create v2.1.0 --from v2.0.0

# Build all versions
python scripts/docs/manage_versions.py build

# Build specific version
python scripts/docs/manage_versions.py build v2.1.0
```

### 2. `release.sh` - Release Automation

High-level script that automates the entire release process.

#### Options

| Option | Description |
|--------|-------------|
| `-s, --source VERSION` | Source version to copy from |
| `-l, --set-latest` | Set as latest stable version |
| `-b, --build` | Build documentation after creation |
| `-d, --dry-run` | Show what would be done |
| `-v, --verbose` | Enable verbose output |
| `-h, --help` | Show help |

#### Examples

```bash
# Basic release
./scripts/docs/release.sh v2.1.0

# Full release workflow
./scripts/docs/release.sh v2.1.0 --source v2.0.0 --set-latest --build

# Test what would happen
./scripts/docs/release.sh v2.1.0 --dry-run --verbose

# Interactive confirmation
./scripts/docs/release.sh v2.1.0 --set-latest
```

### 3. `serve.sh` - Local Development Server

Serves documentation locally for development and testing.

#### Options

| Option | Description |
|--------|-------------|
| `-p, --port PORT` | Port to serve on (default: 8000) |
| `-r, --reload` | Enable live reload |
| `-h, --help` | Show help |

#### Examples

```bash
# Serve latest version
./scripts/docs/serve.sh v2.0.0

# Serve dev version with live reload
./scripts/docs/serve.sh dev --reload

# Custom port
./scripts/docs/serve.sh v2.0.0 --port 8080

# Interactive version selection
./scripts/docs/serve.sh
```

## 🔄 Workflow Examples

### Creating a New Release

**Scenario:** You're releasing version 2.1.0 and want it to be the new latest stable version.

```bash
# 1. Create the release
./scripts/docs/release.sh v2.1.0 --set-latest --build

# 2. Test locally
./scripts/docs/serve.sh v2.1.0

# 3. Commit and push
git add .
git commit -m "docs: add documentation for v2.1.0"
git push origin main
```

### Updating Development Documentation

**Scenario:** You're working on the develop branch and want to update dev docs.

```bash
# 1. Make changes to docs/dev/
# 2. Test locally
./scripts/docs/serve.sh dev --reload

# 3. Build to check for errors
python scripts/docs/manage_versions.py build dev

# 4. Commit and push to develop branch
git add docs/dev/
git commit -m "docs: update development documentation"
git push origin develop
```

### Removing Old Versions

**Scenario:** Version 1.0.0 is no longer supported and should be removed.

```bash
# 1. List current versions
python scripts/docs/manage_versions.py list

# 2. Remove the old version
python scripts/docs/manage_versions.py remove v1.0.0

# 3. Commit changes
git add .
git commit -m "docs: remove v1.0.0 documentation"
git push origin main
```

## 🏗️ How It Works

### Version Structure

```
docs/
├── versions.json          # Version metadata
├── v2.0.0/               # Stable version
│   ├── index.md
│   ├── getting-started/
│   └── ...
├── dev/                  # Development version
│   ├── index.md          # (with warning banner)
│   ├── getting-started/
│   └── ...
└── overrides/            # Theme customizations
```

### Generated Files

For each version, these files are created/updated:

- `docs/<version>/` - Documentation content directory
- `mkdocs-<version>.yml` - MkDocs configuration file
- `docs/versions.json` - Version metadata (updated)

### Build Output

```
site/
├── index.html           # Version selector page
├── versions.json        # Version metadata
├── v2.0.0/             # Built v2.0.0 docs
│   ├── index.html
│   └── ...
└── dev/                # Built dev docs
    ├── index.html
    └── ...
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MKDOCS_CONFIG_DIR` | Directory for MkDocs configs | Project root |
| `DOCS_BUILD_DIR` | Build output directory | `site/` |

### Version Metadata Format

The `docs/versions.json` file contains:

```json
{
  "versions": [
    {
      "version": "v2.0.0",
      "title": "v2.0.0 (Latest)",
      "aliases": ["latest"],
      "path": "v2.0.0",
      "status": "stable",
      "released": "2024-01-15"
    },
    {
      "version": "dev",
      "title": "Development",
      "aliases": ["develop"],
      "path": "dev",
      "status": "development",
      "released": null
    }
  ],
  "latest": "v2.0.0",
  "development": "dev"
}
```

## 🔍 Troubleshooting

### Common Issues

**"Version already exists" error:**
```bash
# Remove the existing version first
python scripts/docs/manage_versions.py remove v2.1.0
```

**MkDocs build fails:**
```bash
# Check configuration syntax
poetry run mkdocs build -f mkdocs-v2.1.0.yml --strict --verbose
```

**Port already in use:**
```bash
# Use a different port
./scripts/docs/serve.sh v2.0.0 --port 8081
```

**Poetry not found:**
```bash
# Install Poetry or use direct MkDocs
pip install mkdocs mkdocs-material
mkdocs serve -f mkdocs-v2.0.0.yml
```

### Debug Mode

Enable verbose output for debugging:

```bash
# For release script
./scripts/docs/release.sh v2.1.0 --verbose --dry-run

# For manage_versions.py
python scripts/docs/manage_versions.py create v2.1.0 --verbose
```

### Validation

Check your setup:

```bash
# Validate versions.json
python -c "
import json
with open('docs/versions.json') as f:
    data = json.load(f)
print('✅ versions.json is valid')
print(f'Latest: {data[\"latest\"]}')
print(f'Versions: {[v[\"version\"] for v in data[\"versions\"]]}')
"

# List all MkDocs configs
ls -la mkdocs-*.yml

# Check documentation structure
find docs/ -name "*.md" | head -10
```

## 🆘 Getting Help

### Documentation Issues

- **Missing features:** Open an issue or discussion
- **Script bugs:** Report in GitHub Issues
- **Usage questions:** Ask in GitHub Discussions

### Community

- **GitHub Repository:** [nexus-platform](https://github.com/dnviti/nexus-platform)
- **Issues:** Report bugs and feature requests
- **Discussions:** Ask questions and share ideas
- **Discord:** Real-time community support

## 📚 Related Documentation

- [Main Documentation README](../README.md)
- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material Theme Docs](https://squidfunk.github.io/mkdocs-material/)
- [GitHub Actions Workflow](../../.github/workflows/docs.yml)

---

**Happy documenting!** 📖✨
