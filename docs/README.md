# Nexus Platform Documentation

This directory contains the versioned documentation for the Nexus Platform. The documentation is built using [MkDocs](https://www.mkdocs.org/) with the [Material theme](https://squidfunk.github.io/mkdocs-material/).

## 📁 Structure

```
docs/
├── README.md                 # This file
├── versions.json            # Version metadata
├── overrides/               # Custom theme overrides
├── v0/                      # Stable version documentation
│   ├── index.md
│   ├── getting-started/
│   ├── architecture/
│   ├── plugins/
│   ├── api/
│   ├── deployment/
│   └── guides/
├── dev/                    # Development version documentation
│   ├── index.md           # (includes dev warning banner)
│   ├── getting-started/
│   ├── architecture/
│   ├── plugins/
│   ├── api/
│   ├── deployment/
│   └── guides/
└── (future versions...)
```

## 🏗️ Version Management

### Available Versions

- **v0** - Latest stable release
- **dev** - Development version (from `develop` branch)

### Creating a New Version

Use the documentation management script to create new versions:

```bash
# Create a new version from the latest
python scripts/docs/manage_versions.py create v1

# Create a new version from a specific source
python scripts/docs/manage_versions.py create v1 --from v0

# List all versions
python scripts/docs/manage_versions.py list

# Set a version as latest
python scripts/docs/manage_versions.py set-latest v1
```

### Manual Version Creation

If you prefer to create versions manually:

1. **Create version directory:**

   ```bash
   mkdir docs/v1
   cp -r docs/v0/* docs/v1/
   ```

2. **Create MkDocs config:**

   ```bash
   cp mkdocs-v0.yml mkdocs-v1.yml
   # Edit the new config file to update paths and version info
   ```

3. **Update versions.json:**
   Add the new version to the metadata file.

## 🚀 Building Documentation

### Build All Versions

```bash
python scripts/docs/manage_versions.py build
```

### Build Specific Version

```bash
# Build v0
mkdocs build -f mkdocs-v0.yml

# Build dev version
mkdocs build -f mkdocs-dev.yml

# Build specific version using script
python scripts/docs/manage_versions.py build v0
```

### Local Development

```bash
# Serve v0 documentation
mkdocs serve -f mkdocs-v0.yml

# Serve dev documentation
mkdocs serve -f mkdocs-dev.yml
```

## 📋 Version Workflow

### Main Branch (Stable Releases)

1. Documentation for stable versions lives in `docs/vX.Y.Z/`
2. Each stable version has its own MkDocs config: `mkdocs-vX.Y.Z.yml`
3. GitHub Actions builds and deploys to `https://dnviti.github.io/nexus-platform/vX.Y.Z/`
4. Latest stable version is set as default redirect

### Develop Branch (Development Documentation)

1. Development documentation lives in `docs/dev/`
2. Uses `mkdocs-dev.yml` configuration
3. Includes warning banner about development status
4. Uses orange color scheme to distinguish from stable versions
5. GitHub Actions builds and deploys to `https://dnviti.github.io/nexus-platform/dev/`

## 🎨 Customization

### Theme Colors

- **Stable versions:** Blue theme (`primary: blue`)
- **Development version:** Orange theme (`primary: orange`)

### Development Warning

The development version includes an automatic warning banner:

```markdown
!!! warning "Development Documentation"
This is the **development version** of the Nexus Platform documentation. The content here may be incomplete, experimental, or subject to change. For stable documentation, please visit the [latest release version](../v0/).
```

## 🔄 GitHub Actions

The documentation is automatically built and deployed using GitHub Actions:

- **Main branch:** Builds and deploys stable version documentation
- **Develop branch:** Builds and deploys development documentation
- **Pull requests:** Tests documentation builds without deployment

### Workflow Files

- `.github/workflows/docs.yml` - Main documentation workflow

### Deployment

Documentation is deployed to GitHub Pages at:

- Main site: https://dnviti.github.io/nexus-platform/
- v0: https://dnviti.github.io/nexus-platform/v0/
- Development: https://dnviti.github.io/nexus-platform/dev/

## 📝 Writing Documentation

### Guidelines

1. **Use descriptive titles** - Make section titles clear and specific
2. **Include code examples** - Provide practical examples for all features
3. **Add navigation hints** - Help users understand where they are and where to go next
4. **Cross-reference** - Link between related sections
5. **Keep it updated** - Update docs when code changes

### Markdown Extensions

Available extensions in all versions:

- `admonition` - Warning, note, and tip boxes
- `pymdownx.details` - Collapsible sections
- `pymdownx.superfences` - Advanced code blocks with Mermaid support
- `pymdownx.highlight` - Syntax highlighting
- `pymdownx.tabbed` - Tabbed content
- `pymdownx.tasklist` - Task lists
- `toc` - Table of contents

### Content Structure

Each documentation version should include:

- **Getting Started** - Installation, quick start, first plugin
- **Architecture** - System overview, core components, patterns
- **Plugin Development** - Building plugins, APIs, testing
- **API Reference** - Complete API documentation
- **Deployment** - Production deployment guides
- **Guides** - Examples, best practices, troubleshooting

## 🔧 Maintenance

### Regular Tasks

1. **Update versions.json** when creating new releases
2. **Archive old versions** that are no longer supported
3. **Update cross-references** when restructuring content
4. **Test builds** before deploying
5. **Review and update** content for accuracy

### Version Lifecycle

1. **Development** - Active development in `docs/dev/`
2. **Release** - Create new version `docs/vX.Y.Z/`
3. **Stable** - Set as latest stable version
4. **Maintenance** - Bug fixes and updates
5. **Archive** - Eventually remove very old versions

## 🆘 Troubleshooting

### Common Issues

**Build fails with "Configuration file not found"**

- Ensure the MkDocs config file exists for the version you're building
- Check that the `docs_dir` path in the config is correct

**Links broken between versions**

- Use relative links when possible
- Update cross-references when moving content

**Development warning not showing**

- Check that the warning is in the `docs/dev/index.md` file
- Ensure the `admonition` extension is enabled

**GitHub Actions failing**

- Check that Poetry dependencies are up to date
- Verify MkDocs config syntax
- Ensure all referenced files exist

### Getting Help

- **GitHub Issues**: Report documentation bugs
- **GitHub Discussions**: Ask questions about documentation
- **Discord**: Real-time help with documentation

## 📚 Resources

- [MkDocs Documentation](https://www.mkdocs.org/)
- [Material Theme Documentation](https://squidfunk.github.io/mkdocs-material/)
- [Python Markdown Extensions](https://python-markdown.github.io/extensions/)
- [Mermaid Diagrams](https://mermaid-js.github.io/mermaid/)

---

**Happy documenting!** 📖✨
