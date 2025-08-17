# GitHub Pages Setup Guide

This guide will help you set up GitHub Pages for the Nexus documentation website.

## Quick Setup

### 1. Repository Settings

1. Navigate to your repository settings:
   ```
   https://github.com/dnviti/Nexus/settings/pages
   ```

2. Under **Source**, select **"GitHub Actions"**
   - **DO NOT** select "Deploy from a branch"
   - The source should show "GitHub Actions" with a green checkmark

### 2. Workflow Permissions

1. Go to Actions settings:
   ```
   https://github.com/dnviti/Nexus/settings/actions
   ```

2. Under **Workflow permissions**:
   - ✅ Select **"Read and write permissions"**
   - ✅ Check **"Allow GitHub Actions to create and approve pull requests"**

### 3. Manual Deployment (If Needed)

If automatic deployment doesn't work:

1. Go to Actions tab:
   ```
   https://github.com/dnviti/Nexus/actions/workflows/docs.yml
   ```

2. Click **"Run workflow"**
3. Select **main** branch
4. Click **"Run workflow"**

## Troubleshooting Common Issues

### Issue: "Branch main is not allowed to deploy to github-pages"

**Solution 1: Remove Environment Protection Rules**
1. Go to `https://github.com/dnviti/Nexus/settings/environments`
2. Click on `github-pages` environment
3. Under **"Deployment branches and tags"**:
   - Select **"All branches"**
   - OR add `main` to **"Selected branches and tags"**
4. Remove any **"Required reviewers"**
5. Set **"Wait timer"** to `0`

**Solution 2: Delete and Recreate Environment**
1. Go to environments settings
2. Delete the `github-pages` environment
3. Let GitHub Actions create it automatically on next run

### Issue: "No github-pages environment found"

**Solution:**
1. Go to `https://github.com/dnviti/Nexus/settings/environments`
2. Click **"New environment"**
3. Name it `github-pages`
4. Set deployment branch rules to allow `main`
5. Save the environment

### Issue: "Pages build and deployment workflow failed"

**Solution:**
1. Check the Actions tab for error details
2. Common fixes:
   - Ensure `mkdocs.yml` has correct navigation
   - Verify all referenced files exist
   - Check for MkDocs build errors

### Issue: "404 - File not found" on GitHub Pages

**Solution:**
1. Verify the site URL: `https://dnviti.github.io/Nexus/`
2. Check if deployment completed successfully
3. Ensure `index.html` was generated in the build

## Manual Build Testing

Test the documentation build locally:

```bash
# Install dependencies
poetry install --with docs

# Build documentation
poetry run mkdocs build --strict

# Serve locally for testing
poetry run mkdocs serve
```

Visit `http://localhost:8000` to preview the documentation.

## Expected Workflow Behavior

### On Push to Main Branch:
1. **Build and Deploy Job** runs
2. Documentation is built with MkDocs
3. Site is deployed to GitHub Pages
4. Available at `https://dnviti.github.io/Nexus/`

### On Push to Other Branches:
1. **Build Only Job** runs
2. Documentation is built for testing
3. Build artifacts are uploaded (no deployment)

### On Pull Requests:
1. **Build Only Job** runs
2. Verifies documentation builds successfully
3. No deployment occurs

## Deployment URL

Once configured correctly, the documentation will be available at:

**🌐 https://dnviti.github.io/Nexus/**

## File Structure

The documentation structure includes:

```
docs/
├── index.md                 # Home page
├── getting-started/         # Installation & setup guides
├── architecture/            # System architecture docs
├── plugins/                 # Plugin development guides
├── api/                     # API reference documentation
├── deployment/              # Deployment guides
└── guides/                  # Additional guides
```

## Advanced Configuration

### Custom Domain (Optional)

To use a custom domain like `docs.nexus.dev`:

1. Add a `CNAME` file to the repository root:
   ```
   echo "docs.nexus.dev" > CNAME
   ```

2. Update `mkdocs.yml`:
   ```yaml
   site_url: https://docs.nexus.dev/
   ```

3. Configure DNS records with your domain provider:
   ```
   CNAME docs.nexus.dev dnviti.github.io
   ```

### Build Optimization

The workflow includes several optimizations:

- **Caching**: Poetry dependencies are cached for faster builds
- **Concurrency**: Only one deployment runs at a time
- **Strict Mode**: Catches documentation errors early
- **Artifact Upload**: Build artifacts are preserved for debugging

## Support

If you encounter issues:

1. **Check Actions Tab**: Look for detailed error messages
2. **Review This Guide**: Ensure all steps are completed
3. **Test Locally**: Verify the build works on your machine
4. **GitHub Documentation**: See [official GitHub Pages docs](https://docs.github.com/en/pages)

## Workflow Status

Monitor deployment status at:
- **Actions**: `https://github.com/dnviti/Nexus/actions`
- **Deployments**: `https://github.com/dnviti/Nexus/deployments`
- **Settings**: `https://github.com/dnviti/Nexus/settings/pages`
