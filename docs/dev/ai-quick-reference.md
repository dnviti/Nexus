# AI Agents Quick Reference Card

## 🚀 Common Documentation Tasks

### New Release Documentation
```bash
# 1. Update changelog (docs/v0/changelog.md)
## v0.1.X (YYYY-MM-DD)
### 🎉 Major Features / 🚀 Enhancements / 🐛 Bug Fixes / 📚 Documentation / 🔧 Infrastructure / ⚠️ Breaking Changes

# 2. Create migration guide if breaking changes (docs/v0/migrations/)
# 3. Update version info in docs/v0/index.md
# 4. Test build: poetry run mkdocs build --strict -f mkdocs-v0.yml
```

### Major Version Release (v0 → v1)
```bash
# 1. Copy docs: cp -r docs/v0/ docs/v1/
# 2. Copy config: cp mkdocs-v0.yml mkdocs-v1.yml
# 3. Update mkdocs-v1.yml (site_name, site_url, docs_dir, site_dir)
# 4. Update versions.json (set v1 as latest, v0 as legacy)
# 5. Update workflow in .github/workflows/docs.yml
```

## 📁 File Structure Quick Map

```
docs/
├── v0/                    # Stable v0.x docs
│   ├── changelog.md       # ALL v0.x releases
│   ├── migrations/        # Version upgrade guides
│   └── ...
├── dev/                   # Development docs
└── versions.json          # Version metadata
```

## 🎯 Version Mapping Rules

| Git Tag | Doc Version | URL | When |
|---------|-------------|-----|------|
| v0.1.x | v0 | /v0/ | Patch releases |
| v0.x.0 | v0 | /v0/ | Minor releases |
| v1.0.0 | v1 | /v1/ | Major releases |
| develop | dev | /dev/ | Development |

## ✅ Quick Checklist

### Before Committing Documentation:
- [ ] Changelog updated with proper emoji categories
- [ ] Migration guide created (if breaking changes)
- [ ] Version references updated
- [ ] Navigation updated in mkdocs config
- [ ] Build test passes: `poetry run mkdocs build --strict -f mkdocs-v0.yml`
- [ ] No broken internal links
- [ ] Code examples tested and working

### Emoji Categories:
- 🎉 Major Features
- 🚀 Enhancements
- 🐛 Bug Fixes
- 📚 Documentation
- 🔧 Infrastructure
- ⚠️ Breaking Changes

## 🚨 Common Mistakes to Avoid

- ❌ Don't edit v0.1.x directories directly → Edit v0/ instead
- ❌ Don't skip migration guides for breaking changes
- ❌ Don't forget to update navigation in mkdocs configs
- ❌ Don't mix dev features in stable docs
- ❌ Don't hardcode version numbers in examples

## 🔧 Essential Commands

```bash
# Build and test documentation
poetry run mkdocs build --strict -f mkdocs-v0.yml

# Serve locally for testing
poetry run mkdocs serve -f mkdocs-v0.yml

# Check navigation structure
grep -r "nav:" mkdocs-*.yml

# Validate version consistency
grep -r "v0\." docs/v0/ | grep -v changelog | grep -v migration
```

## 📝 Quick Templates

### Changelog Entry:
```markdown
## v0.1.X (YYYY-MM-DD)

### 🎉 Major Features
- Feature description

### 🐛 Bug Fixes
- Fix description

### 📚 Documentation
- Documentation updates
```

### Migration Guide Header:
```markdown
# Migration Guide: vX.X.X → vY.Y.Y

**Migration Difficulty**: 🟢 Easy / 🟡 Moderate / 🔴 Complex
**Estimated Time**: X minutes
**Risk Level**: 🟢 Low / 🟡 Medium / 🔴 High
```

## 🎯 Success Indicators

- ✅ All builds pass without warnings
- ✅ Navigation is logical and complete
- ✅ Version references are consistent
- ✅ Migration paths are clear
- ✅ Code examples work
- ✅ No broken links

---
*For detailed instructions, see [AI Agents Documentation Management Guide](ai-agents-documentation-guide.md)*
