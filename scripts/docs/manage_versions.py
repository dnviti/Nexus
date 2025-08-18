#!/usr/bin/env python3
"""
Documentation Version Management Script

This script helps manage versioned documentation for the Nexus Platform.
It can create new versions, update existing ones, and manage the versions.json metadata.

Usage:
    python manage_versions.py create <version>          # Create new version
    python manage_versions.py list                      # List all versions
    python manage_versions.py set-latest <version>      # Set latest version
    python manage_versions.py remove <version>          # Remove version
    python manage_versions.py build [version]           # Build specific or all versions
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class DocumentationManager:
    """Manages versioned documentation for Nexus Platform."""

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the documentation manager.

        Args:
            project_root: Path to the project root. If None, auto-detect.
        """
        if project_root is None:
            # Auto-detect project root by looking for pyproject.toml
            current = Path(__file__).resolve()
            while current.parent != current:
                if (current / "pyproject.toml").exists():
                    project_root = current
                    break
                current = current.parent
            else:
                raise RuntimeError("Could not find project root (no pyproject.toml found)")

        self.project_root = Path(project_root)
        self.docs_root = self.project_root / "docs"
        self.versions_file = self.docs_root / "versions.json"

        # Ensure directories exist
        self.docs_root.mkdir(exist_ok=True)

        # Load or create versions metadata
        self.versions = self._load_versions()

    def _load_versions(self) -> Dict:
        """Load versions metadata from versions.json."""
        if self.versions_file.exists():
            with open(self.versions_file, "r") as f:
                return json.load(f)
        else:
            # Create default versions file
            default_versions = {"versions": [], "latest": None, "development": "dev"}
            self._save_versions(default_versions)
            return default_versions

    def _save_versions(self, versions: Dict) -> None:
        """Save versions metadata to versions.json."""
        with open(self.versions_file, "w") as f:
            json.dump(versions, f, indent=2)
        self.versions = versions

    def _get_current_version_from_pyproject(self) -> str:
        """Extract current version from pyproject.toml."""
        pyproject_path = self.project_root / "pyproject.toml"
        if not pyproject_path.exists():
            raise RuntimeError("pyproject.toml not found")

        with open(pyproject_path, "r") as f:
            for line in f:
                if line.strip().startswith("version = "):
                    # Extract version from line like: version = "2.0.2"
                    version = line.split("=")[1].strip().strip("\"'")
                    return f"v{version}"

        raise RuntimeError("Could not find version in pyproject.toml")

    def _create_mkdocs_config(self, version: str, is_dev: bool = False) -> None:
        """Create MkDocs configuration file for a version.

        Args:
            version: Version string (e.g., 'v2.0.0' or 'dev')
            is_dev: Whether this is a development version
        """
        config_file = self.project_root / f"mkdocs-{version}.yml"

        # Determine colors and title based on version type
        if is_dev:
            primary_color = "orange"
            accent_color = "orange"
            site_title = f"Nexus Platform Documentation (Development)"
            site_description = (
                "The Ultimate Plugin-Based Application Platform - Development Version"
            )
            edit_branch = "develop"
        else:
            primary_color = "blue"
            accent_color = "blue"
            site_title = f"Nexus Platform Documentation {version}"
            site_description = "The Ultimate Plugin-Based Application Platform"
            edit_branch = "main"

        config_content = f"""site_name: {site_title}
site_description: {site_description}
site_author: Nexus Team
site_url: https://dnviti.github.io/nexus-platform/{version}/

repo_name: dnviti/nexus-platform
repo_url: https://github.com/dnviti/nexus-platform
edit_uri: edit/{edit_branch}/docs/{version}/

docs_dir: docs/{version}
site_dir: site/{version}

theme:
  name: material
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - search.share
    - content.code.copy
    {'- announce.dismiss' if is_dev else ''}
  palette:
    - scheme: default
      primary: {primary_color}
      accent: {accent_color}
      toggle:
        icon: material/brightness-7
        name: Switch to dark mode
    - scheme: slate
      primary: {primary_color}
      accent: {accent_color}
      toggle:
        icon: material/brightness-4
        name: Switch to light mode


extra:
  version:
    provider: mike
    default: {version}
  social:
    - icon: fontawesome/brands/github
      link: https://github.com/dnviti/nexus-platform
    - icon: fontawesome/brands/discord
      link: https://discord.gg/nexus
    - icon: fontawesome/brands/twitter
      link: https://twitter.com/nexus_dev

nav:
  - Home: index.md
  - Getting Started:
      - Overview: getting-started/README.md
      - Installation: getting-started/installation.md
      - Quick Start: getting-started/quickstart.md
      - First Plugin: getting-started/first-plugin.md
      - Configuration: getting-started/configuration.md
  - Architecture:
      - Overview: architecture/overview.md
      - Core Components: architecture/core-components.md
      - Event System: architecture/events.md
      - Security: architecture/security.md
  - Plugin Development:
      - Overview: plugins/README.md
      - Basics: plugins/basics.md
      - API Routes: plugins/api-routes.md
      - Database: plugins/database.md
      - Testing: plugins/testing.md
      - Advanced: plugins/advanced.md
      - Events: plugins/events.md
      - Services: plugins/services.md
  - API Reference:
      - Overview: api/README.md
      - Core Classes: api/core.md
      - Authentication: api/auth.md
      - Events: api/events.md
      - Plugins: api/plugins.md
      - Admin: api/admin.md
      - Users: api/users.md
  - Deployment:
      - Overview: deployment/README.md
      - Docker: deployment/docker.md
      - Kubernetes: deployment/kubernetes.md
      - Monitoring: deployment/monitoring.md
      - Development: deployment/development.md
      - Bare Metal: deployment/bare-metal.md
      - Cloud: deployment/cloud.md
  - Guides:
      - Overview: guides/README.md
      - Configuration: guides/configuration.md
      - Development: guides/development.md
      - Plugins: guides/plugins.md

markdown_extensions:
  - admonition
  - pymdownx.details
  - pymdownx.superfences:
      custom_fences:
        - name: mermaid
          class: mermaid
          format: !!python/name:pymdownx.superfences.fence_code_format
  - pymdownx.highlight:
      anchor_linenums: true
  - pymdownx.inlinehilite
  - pymdownx.snippets
  - attr_list
  - md_in_html
  - pymdownx.emoji:
      emoji_index: !!python/name:material.extensions.emoji.twemoji
      emoji_generator: !!python/name:material.extensions.emoji.to_svg
  - pymdownx.tabbed:
      alternate_style: true
  - pymdownx.tasklist:
      custom_checkbox: true
  - toc:
      permalink: true

plugins:
  - search:
      separator: '[\\s\\-,:!=\\[\\]()"`/]+|\\.(?!\\d)|&[lg]t;|(?!\\b)(?=[A-Z][a-z])'
  - autorefs

copyright: Copyright &copy; 2024 Nexus Team
"""

        with open(config_file, "w") as f:
            f.write(config_content)

        print(f"Created MkDocs config: {config_file}")

    def create_version(self, version: str, source_version: Optional[str] = None) -> None:
        """Create a new documentation version.

        Args:
            version: New version to create (e.g., 'v2.1.0')
            source_version: Version to copy from. If None, uses latest or current docs.
        """
        # Validate version format
        if not version.startswith("v") and version != "dev":
            version = f"v{version}"

        version_dir = self.docs_root / version

        if version_dir.exists():
            print(f"Version {version} already exists!")
            return

        # Determine source directory
        if source_version:
            source_dir = self.docs_root / source_version
            if not source_dir.exists():
                print(f"Source version {source_version} does not exist!")
                return
        else:
            # Use latest version or current docs root
            if self.versions["latest"]:
                source_dir = self.docs_root / self.versions["latest"]
            else:
                # Look for existing versioned docs or use root docs
                existing_versions = [v for v in self.versions["versions"] if v["version"] != "dev"]
                if existing_versions:
                    source_dir = self.docs_root / existing_versions[0]["version"]
                else:
                    # Use current docs structure (fallback)
                    source_dir = None

        # Create version directory
        version_dir.mkdir(exist_ok=True)

        if source_dir and source_dir.exists():
            # Copy from source version
            for item in source_dir.iterdir():
                if item.is_dir():
                    shutil.copytree(item, version_dir / item.name)
                else:
                    shutil.copy2(item, version_dir / item.name)
            print(f"Copied documentation from {source_dir} to {version_dir}")
        else:
            # Create basic structure
            (version_dir / "getting-started").mkdir(exist_ok=True)
            (version_dir / "architecture").mkdir(exist_ok=True)
            (version_dir / "plugins").mkdir(exist_ok=True)
            (version_dir / "api").mkdir(exist_ok=True)
            (version_dir / "deployment").mkdir(exist_ok=True)
            (version_dir / "guides").mkdir(exist_ok=True)

            # Create basic index
            index_content = f"""# Nexus Platform {version}

Welcome to the Nexus Platform documentation for version {version}.

This is a new version - documentation content will be added here.
"""
            with open(version_dir / "index.md", "w") as f:
                f.write(index_content)

            print(f"Created new documentation structure for {version}")

        # Add development warning for dev version
        if version == "dev":
            index_file = version_dir / "index.md"
            if index_file.exists():
                with open(index_file, "r") as f:
                    content = f.read()

                warning = """!!! warning "Development Documentation"
    This is the **development version** of the Nexus Platform documentation. The content here may be incomplete, experimental, or subject to change. For stable documentation, please visit the [latest release version](../v2.0.0/).

"""

                # Add warning at the beginning
                with open(index_file, "w") as f:
                    f.write(warning + content)

        # Create MkDocs config
        self._create_mkdocs_config(version, is_dev=(version == "dev"))

        # Update versions metadata
        is_dev = version == "dev"
        new_version_info = {
            "version": version,
            "title": f"{version} (Development)" if is_dev else version,
            "aliases": ["develop"] if is_dev else [],
            "path": version,
            "status": "development" if is_dev else "stable",
            "released": None if is_dev else datetime.now().strftime("%Y-%m-%d"),
        }

        # Remove existing entry if it exists
        self.versions["versions"] = [
            v for v in self.versions["versions"] if v["version"] != version
        ]

        # Add new version
        if is_dev:
            # Add dev version at the end
            self.versions["versions"].append(new_version_info)
        else:
            # Add stable version at the beginning
            self.versions["versions"].insert(0, new_version_info)
            # Update latest if this is a stable version
            if not self.versions["latest"] or version > self.versions["latest"]:
                self.versions["latest"] = version
                # Update title to include "Latest"
                new_version_info["title"] = f"{version} (Latest)"

        self._save_versions(self.versions)
        print(f"Added version {version} to versions.json")

    def list_versions(self) -> None:
        """List all available documentation versions."""
        print("Available documentation versions:")
        print("-" * 40)

        for version_info in self.versions["versions"]:
            status_icon = "🚧" if version_info["status"] == "development" else "✅"
            latest_mark = " (LATEST)" if version_info["version"] == self.versions["latest"] else ""

            print(f"{status_icon} {version_info['version']}{latest_mark}")
            print(f"   Title: {version_info['title']}")
            print(f"   Status: {version_info['status']}")
            if version_info["released"]:
                print(f"   Released: {version_info['released']}")
            print()

    def set_latest(self, version: str) -> None:
        """Set a version as the latest stable version.

        Args:
            version: Version to set as latest
        """
        # Find version in metadata
        version_found = False
        for version_info in self.versions["versions"]:
            if version_info["version"] == version:
                if version_info["status"] != "stable":
                    print(f"Cannot set {version} as latest - it's not a stable version")
                    return
                version_found = True
                break

        if not version_found:
            print(f"Version {version} not found")
            return

        # Update latest
        old_latest = self.versions["latest"]
        self.versions["latest"] = version

        # Update titles
        for version_info in self.versions["versions"]:
            if version_info["version"] == version:
                if "(Latest)" not in version_info["title"]:
                    version_info["title"] = f"{version} (Latest)"
            elif version_info["version"] == old_latest:
                version_info["title"] = version_info["title"].replace(" (Latest)", "")

        self._save_versions(self.versions)
        print(f"Set {version} as the latest version")

    def remove_version(self, version: str) -> None:
        """Remove a documentation version.

        Args:
            version: Version to remove
        """
        version_dir = self.docs_root / version
        config_file = self.project_root / f"mkdocs-{version}.yml"

        # Remove from versions metadata
        self.versions["versions"] = [
            v for v in self.versions["versions"] if v["version"] != version
        ]

        # Update latest if this was the latest
        if self.versions["latest"] == version:
            stable_versions = [v for v in self.versions["versions"] if v["status"] == "stable"]
            if stable_versions:
                self.versions["latest"] = stable_versions[0]["version"]
                stable_versions[0]["title"] = f"{stable_versions[0]['version']} (Latest)"
            else:
                self.versions["latest"] = None

        self._save_versions(self.versions)

        # Remove directories and files
        if version_dir.exists():
            shutil.rmtree(version_dir)
            print(f"Removed documentation directory: {version_dir}")

        if config_file.exists():
            config_file.unlink()
            print(f"Removed MkDocs config: {config_file}")

        print(f"Removed version {version}")

    def build_version(self, version: Optional[str] = None) -> None:
        """Build documentation for a specific version or all versions.

        Args:
            version: Specific version to build. If None, builds all versions.
        """
        if version:
            versions_to_build = [version]
        else:
            versions_to_build = [v["version"] for v in self.versions["versions"]]

        for v in versions_to_build:
            config_file = self.project_root / f"mkdocs-{v}.yml"
            if not config_file.exists():
                print(f"MkDocs config not found for {v}, creating it...")
                self._create_mkdocs_config(v, is_dev=(v == "dev"))

            print(f"Building documentation for {v}...")
            try:
                result = subprocess.run(
                    ["mkdocs", "build", "-f", str(config_file), "--strict"],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    print(f"✅ Successfully built {v}")
                else:
                    print(f"❌ Failed to build {v}")
                    print(f"Error: {result.stderr}")

            except FileNotFoundError:
                print(
                    "❌ MkDocs not found. Please install it with: pip install mkdocs mkdocs-material"
                )
                return


def main():
    """Main CLI interface."""
    parser = argparse.ArgumentParser(
        description="Manage Nexus Platform documentation versions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s create v2.1.0                 # Create version v2.1.0
  %(prog)s create v2.1.0 --from v2.0.0   # Create v2.1.0 from v2.0.0
  %(prog)s list                          # List all versions
  %(prog)s set-latest v2.1.0             # Set v2.1.0 as latest
  %(prog)s remove v2.0.0                 # Remove version v2.0.0
  %(prog)s build                         # Build all versions
  %(prog)s build v2.1.0                  # Build specific version
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new version")
    create_parser.add_argument("version", help="Version to create (e.g., v2.1.0)")
    create_parser.add_argument("--from", dest="source_version", help="Source version to copy from")

    # List command
    subparsers.add_parser("list", help="List all versions")

    # Set latest command
    latest_parser = subparsers.add_parser("set-latest", help="Set latest version")
    latest_parser.add_argument("version", help="Version to set as latest")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a version")
    remove_parser.add_argument("version", help="Version to remove")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build documentation")
    build_parser.add_argument("version", nargs="?", help="Specific version to build (optional)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    try:
        manager = DocumentationManager()

        if args.command == "create":
            manager.create_version(args.version, args.source_version)
        elif args.command == "list":
            manager.list_versions()
        elif args.command == "set-latest":
            manager.set_latest(args.version)
        elif args.command == "remove":
            manager.remove_version(args.version)
        elif args.command == "build":
            manager.build_version(args.version)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
