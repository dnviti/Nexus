# AI Agents Documentation Management Guide

This document provides comprehensive guidelines for AI agents on how to manage, maintain, and update the Nexus Platform documentation. It covers the complete workflow, best practices, and technical implementation details.

## 🎯 Overview

The Nexus Platform uses a **major version-based documentation system** with semantic versioning and automated workflows. AI agents should understand this structure to effectively maintain documentation quality and consistency.

## 📁 Documentation Architecture

### Directory Structure

```
nexus-platform/
├── docs/
│   ├── v0/                           # Major version v0.x documentation (STABLE)
│   │   ├── index.md                  # Landing page with version info
│   │   ├── changelog.md              # Complete v0.x release history
│   │   ├── migrations/               # Migration guides between versions
│   │   │   └── v0.1.0-to-v0.1.1.md  # Example migration guide
│   │   ├── getting-started/          # User onboarding guides
│   │   ├── architecture/             # System design docs
│   │   ├── plugins/                  # Plugin development guides
│   │   ├── api/                      # API reference documentation
│   │   ├── deployment/               # Production deployment guides
│   │   └── guides/                   # How-to guides and tutorials
│   ├── dev/                          # Development version (LATEST CHANGES)
│   │   ├── (mirrors v0 structure)
│   │   └── ai-agents-documentation-guide.md  # This file
│   ├── versions.json                 # Version metadata configuration
│   └── README.md                     # Documentation index
├── mkdocs-v0.yml                     # v0 documentation build config
├── mkdocs-dev.yml                    # Development documentation build config
└── mkdocs.yml                        # Main documentation config
```

### Version Mapping Strategy

| Git Tag                            | Documentation Version | URL Path | Purpose              |
| ---------------------------------- | --------------------- | -------- | -------------------- |
| `v0.1.0`, `v0.1.1`, `v0.1.2`, etc. | `v0`                  | `/v0/`   | Stable major version |
| `v1.0.0`, `v1.1.0`, etc.           | `v1`                  | `/v1/`   | Next major version   |
| `develop` branch                   | `dev`                 | `/dev/`  | Latest development   |

## 🔄 AI Agent Workflow

### 1. Documentation Updates for New Releases

When a new version is released (e.g., v0.1.2), AI agents should:

#### A. Update Changelog

**File**: `docs/v0/changelog.md`

1. **Add new version entry** at the top:

```markdown
## v0.1.2 (YYYY-MM-DD)

### 🚀 Enhancements

- Description of improvements

### 🐛 Bug Fixes

- Description of fixes

### 📚 Documentation

- Documentation updates

### 🔧 Infrastructure

- Build/CI improvements
```

2. **Use semantic categorization**:
   - 🎉 **Major Features**: New significant functionality
   - 🚀 **Enhancements**: Improvements to existing features
   - 🐛 **Bug Fixes**: Fixes for identified issues
   - 📚 **Documentation**: Documentation updates
   - 🔧 **Infrastructure**: Build, CI/CD, and development tools
   - ⚠️ **Breaking Changes**: Changes requiring code updates

#### B. Create Migration Guide (if needed)

**File**: `docs/v0/migrations/vX.X.X-to-vY.Y.Y.md`

Create only for versions with breaking changes or significant updates:

```markdown
# Migration Guide: vX.X.X → vY.Y.Y

## Overview

Brief description of changes and migration difficulty.

## Quick Migration

Step-by-step instructions for common cases.

## Breaking Changes

List any breaking changes with solutions.

## Compatibility

What remains compatible vs. what changes.

**Migration Difficulty**: 🟢 Easy / 🟡 Moderate / 🔴 Complex
**Estimated Time**: X minutes
**Risk Level**: 🟢 Low / 🟡 Medium / 🔴 High
```

#### C. Update Version References

1. **Update `docs/v0/index.md`** current version reference
2. **Update navigation** in `mkdocs-v0.yml` if new migration guides added
3. **Verify examples** and code snippets use current version

### 2. Major Version Releases

When transitioning to a new major version (e.g., v0.x → v1.0):

#### A. Create New Major Version Directory

1. **Copy structure**: `cp -r docs/v0/ docs/v1/`
2. **Update version references** throughout v1 documentation
3. **Create new config**: `cp mkdocs-v0.yml mkdocs-v1.yml`
4. **Update `mkdocs-v1.yml`**:
   - Change `site_name` to include v1.x
   - Update `site_url` to `/v1/`
   - Update `docs_dir` to `docs/v1`
   - Update `site_dir` to `site/v1`

#### B. Update versions.json

```json
{
  "versions": [
    {
      "version": "v1",
      "title": "v1.x (Latest Stable)",
      "aliases": ["latest", "stable"],
      "path": "v1",
      "status": "stable",
      "released": "YYYY-MM-DD",
      "current_version": "v1.0.0"
    },
    {
      "version": "v0",
      "title": "v0.x (Legacy)",
      "aliases": [],
      "path": "v0",
      "status": "legacy",
      "released": "YYYY-MM-DD",
      "current_version": "v0.1.x"
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
  "latest": "v1",
  "development": "dev"
}
```

#### C. Update Workflows

Update `.github/workflows/docs.yml` to handle new major version.

### 3. Development Documentation

**File**: `docs/dev/*`

- Always keep development docs in sync with latest code
- Include experimental features and breaking changes
- Update immediately when develop branch changes
- Document new features before they're released

## 📝 Content Guidelines

### Writing Standards

1. **Clear and Concise**: Use simple, direct language
2. **Code Examples**: Always include working code examples
3. **Version Specific**: Clearly indicate version requirements
4. **Testing**: Verify all code examples work
5. **Cross-references**: Link related documentation sections

### Markdown Best Practices

````markdown
# Use proper heading hierarchy (H1 → H2 → H3)

## Code Blocks with Language

```python
# Always specify language for syntax highlighting
from nexus import create_nexus_app
```
````

## Admonitions for Important Info

!!! info "Version Requirement"
This feature requires Nexus Platform v0.1.1 or later.

!!! warning "Breaking Change"
This is a breaking change from previous versions.

!!! tip "Best Practice"
We recommend using this approach for better performance.

````

### Documentation Types

1. **API Reference**: Auto-generated from code docstrings
2. **Tutorials**: Step-by-step learning guides
3. **How-to Guides**: Problem-solving oriented
4. **Architecture**: System design and concepts
5. **Changelog**: Version history and changes
6. **Migration Guides**: Upgrade instructions

## 🔧 Technical Implementation

### MkDocs Configuration

Each major version has its own configuration:

```yaml
# mkdocs-v0.yml example
site_name: Nexus Platform Documentation v0.x
site_url: https://dnviti.github.io/nexus-platform/v0/
docs_dir: docs/v0
site_dir: site/v0

nav:
  - Home: index.md
  - Getting Started: [...]
  - Changelog:
      - Version History: changelog.md
      - Migration Guides:
          - v0.1.0 → v0.1.1: migrations/v0.1.0-to-v0.1.1.md
````

### Build Process

The documentation build is triggered by:

1. **Tag pushes** (v0.x.x → builds v0 docs)
2. **Develop branch pushes** (builds dev docs)
3. **Manual workflow dispatch**

### GitHub Actions Integration

The workflow automatically:

1. **Detects major version** from git tag
2. **Builds appropriate documentation**
3. **Deploys to GitHub Pages**
4. **Updates landing page** with version info

## 🎯 AI Agent Decision Matrix

### When to Update Documentation

| Scenario                   | Action Required                    | Files to Update                               |
| -------------------------- | ---------------------------------- | --------------------------------------------- |
| New patch release (v0.1.x) | Update changelog                   | `docs/v0/changelog.md`                        |
| New minor release (v0.x.0) | Update changelog + migration guide | `docs/v0/changelog.md`, `docs/v0/migrations/` |
| New major release (v1.0.0) | Create new version docs            | `docs/v1/`, `mkdocs-v1.yml`, `versions.json`  |
| Feature added to develop   | Update dev docs                    | `docs/dev/`                                   |
| API changes                | Update API reference               | `docs/*/api/`                                 |
| New plugin capability      | Update plugin guides               | `docs/*/plugins/`                             |
| Deployment changes         | Update deployment docs             | `docs/*/deployment/`                          |

### Quality Checklist

Before completing documentation updates, verify:

- [ ] All code examples are tested and working
- [ ] Version requirements are clearly stated
- [ ] Links between related sections are updated
- [ ] Changelog follows semantic categorization
- [ ] Migration guides include difficulty assessment
- [ ] No broken internal links
- [ ] Navigation structure is logical
- [ ] Search keywords are appropriate

## 🚨 Common Pitfalls

### What NOT to Do

1. **Don't edit patch version docs directly** (like old v0.1.0 folder)
   - Always edit major version docs (v0 folder)

2. **Don't skip migration guides** for breaking changes
   - Even small breaking changes need migration docs

3. **Don't forget to update navigation** in mkdocs configs
   - New pages need to be added to nav structure

4. **Don't mix development and stable docs**
   - Keep experimental features in dev docs only

5. **Don't hardcode version numbers** in examples
   - Use placeholders or latest stable version

### Error Recovery

If documentation is broken:

1. **Check build logs** in GitHub Actions
2. **Verify file paths** and internal links
3. **Test MkDocs build locally**: `poetry run mkdocs build -f mkdocs-v0.yml`
4. **Rollback if necessary** to previous working state

## 📋 Templates

### New Version Changelog Entry

```markdown
## v0.1.X (YYYY-MM-DD)

### 🎉 Major Features

- New feature description with brief explanation

### 🚀 Enhancements

- Improvement description
- Performance enhancement details

### 🐛 Bug Fixes

- Fix description with issue reference if available
- Security fix details

### 📚 Documentation

- Documentation improvements
- New guides or tutorials added

### 🔧 Infrastructure

- Build system improvements
- CI/CD pipeline updates
- Development tool enhancements

### ⚠️ Breaking Changes

- Breaking change description
- Migration instructions or reference to migration guide
```

### Migration Guide Template

````markdown
# Migration Guide: vX.X.X → vY.Y.Y

## Overview

Brief description of the changes and what this migration involves.

## Quick Migration

### 1. Update Package

```bash
pip install --upgrade nexus-platform==Y.Y.Y
```
````

### 2. Update Code (if needed)

```python
# Old way (vX.X.X)
old_code_example()

# New way (vY.Y.Y)
new_code_example()
```

### 3. Test Your Application

```bash
nexus run
```

## Breaking Changes

List of breaking changes with solutions.

## Compatibility

What remains compatible vs. what changes.

## Troubleshooting

Common issues and solutions.

**Migration Difficulty**: 🟢 Easy
**Estimated Time**: < 5 minutes
**Risk Level**: 🟢 Low

````

## 🔍 Verification Commands

Use these commands to verify documentation integrity:

```bash
# Test documentation build
poetry run mkdocs build --strict -f mkdocs-v0.yml

# Check for broken links (if using link checker)
poetry run mkdocs serve -f mkdocs-v0.yml

# Validate navigation structure
grep -r "nav:" mkdocs-*.yml

# Check version consistency
grep -r "v0\." docs/v0/ | grep -v changelog | grep -v migration
````

## 📚 Resources

- **MkDocs Documentation**: https://www.mkdocs.org/
- **Material Theme**: https://squidfunk.github.io/mkdocs-material/
- **Markdown Guide**: https://www.markdownguide.org/
- **Semantic Versioning**: https://semver.org/
- **GitHub Actions**: https://docs.github.com/en/actions

## 🎯 Success Metrics

Good documentation management achieves:

- ✅ **Consistent versioning** across all docs
- ✅ **Zero broken links** between sections
- ✅ **Complete migration paths** for all versions
- ✅ **Accurate code examples** that work
- ✅ **Clear changelog entries** for each release
- ✅ **Proper semantic categorization** of changes
- ✅ **Automated build success** for all versions

---

**Last Updated**: 2025-08-18
**Version**: 1.0
**Maintainer**: AI Agents Documentation Team
