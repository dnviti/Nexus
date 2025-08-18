# Documentation Versioning Implementation

This document provides a comprehensive overview of the versioned documentation system implemented for the Nexus Platform.

## 🎯 Overview

The Nexus Platform now supports versioned documentation with the following key features:

- **Version-specific documentation** (e.g., v2.0.0, v2.1.0)
- **Development documentation** with warning banners
- **Automated GitHub Pages deployment**
- **Version management scripts**
- **Local development tools**

## 📁 Directory Structure

```
nexus-platform/
├── docs/
│   ├── versions.json              # Version metadata
│   ├── index.html                 # Version selector landing page
│   ├── README.md                  # Documentation guide
│   ├── overrides/                 # Custom theme overrides
│   ├── v2.0.0/                    # Latest stable version
│   │   ├── index.md
│   │   ├── getting-started/
│   │   ├── architecture/
│   │   ├── plugins/
│   │   ├── api/
│   │   ├── deployment/
│   │   └── guides/
│   └── dev/                       # Development version
│       ├── index.md               # (with dev warning banner)
│       ├── getting-started/
│       ├── architecture/
│       ├── plugins/
│       ├── api/
│       ├── deployment/
│       └── guides/
├── scripts/docs/                  # Management scripts
│   ├── README.md                  # Scripts documentation
│   ├── manage_versions.py         # Core version management
│   ├── release.sh                 # Release automation
│   └── serve.sh                   # Local development server
├── mkdocs.yml                     # Main config (backward compatibility)
├── mkdocs-v2.0.0.yml             # v2.0.0 specific config
├── mkdocs-dev.yml                # Development config
└── .github/workflows/docs.yml    # Updated CI/CD pipeline
```

## 🌐 Live Documentation URLs

| Version             | URL                                             | Branch  | Status                   |
| ------------------- | ----------------------------------------------- | ------- | ------------------------ |
| **Landing Page**    | https://dnviti.github.io/nexus-platform/        | main    | Auto-redirects to latest |
| **v2.0.0 (Latest)** | https://dnviti.github.io/nexus-platform/v2.0.0/ | main    | Stable                   |
| **Development**     | https://dnviti.github.io/nexus-platform/dev/    | develop | Development              |

## 🛠️ Key Features

### 1. Version Management System

**Automated Scripts:**

- `manage_versions.py` - Core version operations (create, list, remove, build)
- `release.sh` - Complete release workflow automation
- `serve.sh` - Local development server

**Version Metadata (`versions.json`):**

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

### 2. Development Version Warning System

The development documentation automatically includes a prominent warning banner:

```markdown
!!! warning "Development Documentation"
This is the **development version** of the Nexus Platform documentation. The content here may be incomplete, experimental, or subject to change. For stable documentation, please visit the [latest release version](../v2.0.0/).
```

**Visual Distinctions:**

- **Stable versions:** Blue theme (`primary: blue`)
- **Development version:** Orange theme (`primary: orange`)

### 3. GitHub Actions CI/CD

**Updated Workflow (`.github/workflows/docs.yml`):**

- **Tag Push (e.g., v2.0.0):** Builds and deploys that specific version's documentation
- **Develop Branch:** Builds and deploys development documentation only
- **Main Branch:** No documentation build (alignment branch only)
- **Pull Requests:** Tests documentation builds without deployment

**Deployment Strategy:**

```yaml
jobs:
  docs-tag: # Deploys specific version from tag push
  docs-develop: # Deploys dev version from develop branch
  build-only: # Tests builds for PRs
  lint-docs: # Validates documentation quality
```

### 4. Landing Page & Version Selection

**Auto-redirect Landing Page (`docs/index.html`):**

- Automatically redirects to latest stable version after 5 seconds
- Provides manual version selection interface
- Modern, responsive design with version cards
- Stops auto-redirect on user interaction

**Features:**

- Version status indicators (Latest, Development)
- Release date information
- Responsive design for mobile devices
- Direct links to all available versions

## 🚀 Usage Guide

### Creating a New Documentation Version

**Tag-Based Method (Recommended):**

```bash
# Prepare v2.1.0 and create tag (triggers auto-deployment)
./scripts/docs/release.sh v2.1.0 --set-latest --create-tag
```

**Manual Method:**

```bash
# Step-by-step approach
python scripts/docs/manage_versions.py prepare-tag v2.1.0
python scripts/docs/manage_versions.py set-latest v2.1.0
git add . && git commit -m "docs: prepare v2.1.0 for release"
git tag v2.1.0 && git push origin v2.1.0
```

### Local Development

**Serve Specific Version:**

```bash
# Serve latest stable version
./scripts/docs/serve.sh v2.0.0

# Serve development version with live reload
./scripts/docs/serve.sh dev --reload --port 8080
```

**Interactive Version Selection:**

```bash
# Prompts for version selection
./scripts/docs/serve.sh
```

### Version Management

**List All Versions:**

```bash
python scripts/docs/manage_versions.py list
```

**Remove Old Version:**

```bash
python scripts/docs/manage_versions.py remove v1.0.0
```

**Build All Versions:**

```bash
python scripts/docs/manage_versions.py build
```

## 🔄 Workflow Examples

### 1. New Feature Release

```bash
# 1. Prepare version and create tag (auto-deploys)
./scripts/docs/release.sh v2.1.0 --set-latest --create-tag

# 2. Test locally (if needed)
./scripts/docs/serve.sh v2.1.0

# 3. Tag push triggers automatic deployment
# GitHub Actions builds and deploys documentation automatically
```

### 2. Development Documentation Update

```bash
# 1. Make changes to docs/dev/
vim docs/dev/getting-started/new-feature.md

# 2. Test locally with live reload
./scripts/docs/serve.sh dev --reload

# 3. Commit to develop branch
git add docs/dev/
git commit -m "docs: document new feature in development"
git push origin develop
```

### 3. Maintenance Tasks

```bash
# Remove outdated version
python scripts/docs/manage_versions.py remove v1.0.0

# Update latest version (updates metadata only)
python scripts/docs/manage_versions.py set-latest v2.1.0

# Prepare and tag new version (triggers deployment)
python scripts/docs/manage_versions.py prepare-tag v2.1.0
git tag v2.1.0 && git push origin v2.1.0
```

## 🏗️ Technical Implementation

### MkDocs Configuration Strategy

**Version-Specific Configs:**

- `mkdocs-v2.0.0.yml` - Stable version configuration
- `mkdocs-dev.yml` - Development version configuration
- `mkdocs.yml` - Backward compatibility (points to latest)

**Key Configuration Differences:**

```yaml
# Stable Version (mkdocs-v2.0.0.yml)
site_name: Nexus Platform Documentation v2.0.0
site_url: https://dnviti.github.io/nexus-platform/v2.0.0/
docs_dir: docs/v2.0.0
site_dir: site/v2.0.0
theme:
  palette:
    primary: blue

# Development Version (mkdocs-dev.yml)
site_name: Nexus Platform Documentation (Development)
site_url: https://dnviti.github.io/nexus-platform/dev/
docs_dir: docs/dev
site_dir: site/dev
theme:
  palette:
    primary: orange
```

### GitHub Pages Deployment

**Site Structure:**

```
https://dnviti.github.io/nexus-platform/
├── index.html           # Landing page with version selector
├── versions.json        # Version metadata API
├── v2.0.0/             # Latest stable documentation
│   ├── index.html
│   ├── getting-started/
│   └── ...
└── dev/                # Development documentation
    ├── index.html
    ├── getting-started/
    └── ...
```

### Version Metadata API

The `versions.json` file serves as a simple API for:

- Version listing and status
- Latest version detection
- Client-side version switching (future enhancement)
- Deployment validation

## 🔧 Configuration & Customization

### Environment Variables

| Variable            | Description                | Default      |
| ------------------- | -------------------------- | ------------ |
| `MKDOCS_CONFIG_DIR` | MkDocs config directory    | Project root |
| `DOCS_BUILD_DIR`    | Documentation build output | `site/`      |

### Theme Customization

**Custom Overrides Directory:** `docs/overrides/`

- Custom templates
- Additional CSS/JS
- Theme modifications

**Color Schemes:**

- Stable: Blue theme for production-ready documentation
- Development: Orange theme to clearly indicate experimental content

### Script Configuration

**Default Behaviors:**

- New versions default to copying from latest stable
- Development version always includes warning banner
- Auto-redirect timeout: 5 seconds
- Default serve port: 8000

## 📊 Benefits Achieved

### 1. User Experience

- ✅ Clear version distinction with visual cues
- ✅ Automatic latest version redirection
- ✅ Warning banners for development content
- ✅ Mobile-responsive documentation

### 2. Developer Experience

- ✅ Tag-based automated deployment workflow
- ✅ Local development with live reload
- ✅ Simple script-based management
- ✅ Comprehensive error handling and validation

### 3. Maintenance

- ✅ Automated CI/CD on tag deployment
- ✅ Clean separation: develop=dev docs, tags=version docs
- ✅ Version metadata tracking
- ✅ Easy cleanup of old versions

### 4. Scalability

- ✅ Support for unlimited documentation versions
- ✅ Tag-triggered deployment pipelines
- ✅ Flexible configuration system
- ✅ API-ready version metadata

## 🆘 Troubleshooting

### Common Issues

**Build Failures:**

```bash
# Check configuration syntax
poetry run mkdocs build -f mkdocs-v2.1.0.yml --strict --verbose
```

**Version Conflicts:**

```bash
# Remove existing version
python scripts/docs/manage_versions.py remove v2.1.0
```

**Local Server Issues:**

```bash
# Use different port
./scripts/docs/serve.sh v2.0.0 --port 8081
```

### Validation Commands

```bash
# Validate versions.json
python -c "import json; json.load(open('docs/versions.json')); print('✅ Valid')"

# Check documentation structure
python scripts/docs/manage_versions.py list

# Test builds
python scripts/docs/manage_versions.py build
```

## 📚 Next Steps & Future Enhancements

### Immediate Actions

1. Test the complete workflow with a new version
2. Update existing documentation content
3. Train team members on new scripts
4. Monitor GitHub Actions deployment

### Future Enhancements

1. **Version Selector Widget:** Add version switching to each page
2. **Automated Archival:** Remove very old versions automatically
3. **Analytics Integration:** Track version usage patterns
4. **Content Synchronization:** Tools to sync common content across versions
5. **API Documentation:** Auto-generate API docs from code
6. **Search Improvements:** Version-aware search functionality

## 🏆 Conclusion

The Nexus Platform now has a robust, scalable documentation versioning system that provides:

- **Tag-based deployment** for stable releases with automatic CI/CD
- **Clear separation** between stable (tag-based) and development (branch-based) documentation
- **Professional presentation** with version-aware themes and warnings
- **Developer-friendly tools** for local development and testing
- **Scalable architecture** ready for unlimited versions with independent deployments

The implementation successfully addresses the original requirements with the correct workflow:

- ✅ Version-specific documentation folders (`docs/vx.y.z/`)
- ✅ Development version with warning banners (`docs/dev/`)
- ✅ GitHub Pages deployment for version selection
- ✅ Tag-based CI/CD pipeline for stable versions, develop branch for dev docs
- ✅ Main branch as alignment branch only (no documentation builds)

Users can now confidently choose the appropriate documentation version for their needs, while developers have a proper tag-based workflow that separates development and release documentation clearly.
