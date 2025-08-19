#!/usr/bin/env python3
"""
Nexus CLI - Developer Command Line Interface

A comprehensive CLI tool for Nexus Framework developers to:
- Create and manage applications
- Develop and manage plugins
- Run development servers
- Generate project templates
- Manage configurations
- Debug and monitor applications
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import click
import yaml

from . import __version__
from .config import AppConfig, create_default_config, load_config
from .factory import create_nexus_app
from .utils import setup_logging

# Setup logging
logger = logging.getLogger("nexus.cli")


def get_project_root() -> Path:
    """Get the current project root directory."""
    return Path.cwd()


def get_plugins_dir() -> Path:
    """Get the plugins directory."""
    return get_project_root() / "plugins"


def get_config_file() -> Path:
    """Get the main configuration file."""
    return get_project_root() / "nexus_config.yaml"


@click.group()
@click.version_option(version=__version__, prog_name="Nexus CLI")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.pass_context
def cli(ctx: Any, verbose: bool, config: Optional[str]) -> None:
    """
    🚀 Nexus Framework CLI - Developer Tools

    The ultimate command-line interface for Nexus Framework development.
    Build, manage, and deploy plugin-based applications with ease.
    """
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Setup logging level
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)


# =============================================================================
# PROJECT MANAGEMENT COMMANDS
# =============================================================================


@cli.group()
@click.pass_context
def project(ctx: Any) -> None:
    """📁 Project management commands"""
    pass


@project.command("init")
@click.argument("name", default="my-nexus-app")
@click.option(
    "--template",
    "-t",
    default="basic",
    type=click.Choice(["basic", "api", "microservice", "web"]),
    help="Project template to use",
)
@click.option(
    "--description", "-d", default="A Nexus Framework Application", help="Project description"
)
@click.option("--author", "-a", default="", help="Author name")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing files")
def init_project(name: str, template: str, description: str, author: str, force: bool) -> None:
    """🎯 Initialize a new Nexus project"""
    project_dir = Path(name)

    if project_dir.exists() and not force:
        click.echo(f"❌ Directory '{name}' already exists. Use --force to overwrite.")
        sys.exit(1)

    click.echo(f"🎯 Creating new Nexus project: {name}")
    click.echo(f"📝 Template: {template}")
    click.echo(f"📄 Description: {description}")

    # Create project structure
    project_dir.mkdir(exist_ok=force)
    (project_dir / "plugins").mkdir(exist_ok=True)
    (project_dir / "config").mkdir(exist_ok=True)
    (project_dir / "logs").mkdir(exist_ok=True)
    (project_dir / "tests").mkdir(exist_ok=True)
    (project_dir / "docs").mkdir(exist_ok=True)

    # Create main application file
    main_py_content = generate_main_py(name, template, description, author)
    (project_dir / "main.py").write_text(main_py_content)

    # Create configuration file
    config_content = generate_config_yaml(name, description, author)
    (project_dir / "nexus_config.yaml").write_text(config_content)

    # Create requirements.txt
    requirements = generate_requirements(template)
    (project_dir / "requirements.txt").write_text(requirements)

    # Create README.md
    readme_content = generate_readme(name, description, author, template)
    (project_dir / "README.md").write_text(readme_content)

    # Create .gitignore
    gitignore_content = generate_gitignore()
    (project_dir / ".gitignore").write_text(gitignore_content)

    # Create pytest configuration
    pytest_ini_content = generate_pytest_ini()
    (project_dir / "pytest.ini").write_text(pytest_ini_content)

    # Create example test
    test_content = generate_test_example(name)
    (project_dir / "tests" / "test_app.py").write_text(test_content)

    # Create Dockerfile for containerization
    dockerfile_content = generate_dockerfile()
    (project_dir / "Dockerfile").write_text(dockerfile_content)

    # Create docker-compose.yml
    compose_content = generate_docker_compose(name)
    (project_dir / "docker-compose.yml").write_text(compose_content)

    click.echo(f"✅ Project '{name}' created successfully!")
    click.echo("\n📋 Next steps:")
    click.echo(f"   cd {name}")
    click.echo("   pip install -r requirements.txt")
    click.echo("   nexus run")
    click.echo("\n🔗 Useful commands:")
    click.echo("   nexus plugin create my-plugin    # Create a plugin")
    click.echo("   nexus run --reload               # Run with hot reload")
    click.echo("   nexus project info               # Show project info")


@project.command("info")
def project_info() -> None:
    """ℹ️ Show project information"""
    project_root = get_project_root()
    config_file = get_config_file()

    if not config_file.exists():
        click.echo("❌ Not in a Nexus project directory (no nexus_config.yaml found)")
        sys.exit(1)

    try:
        config = load_config(str(config_file))
        plugins_dir = get_plugins_dir()

        # Count plugins
        plugin_count = 0
        if plugins_dir.exists():
            plugin_count = len(
                [d for d in plugins_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
            )

        click.echo("📊 Project Information")
        click.echo("=" * 50)
        click.echo(f"🏷️  Name: {config.app.name}")
        click.echo(f"📝  Description: {config.app.description}")
        click.echo(f"📦  Version: {config.app.version}")
        click.echo(f"👤  Author: {getattr(config.app, 'author', 'Not specified')}")
        click.echo(f"📁  Location: {project_root}")
        click.echo(f"🔌  Plugins: {plugin_count}")
        click.echo(
            f"🗃️   Database: {config.database.type if hasattr(config, 'database') and config.database else 'Not configured'}"
        )
        click.echo(
            f"🌐  CORS: {'Enabled' if getattr(config, 'cors', {}).get('enabled', False) else 'Disabled'}"
        )

    except Exception as e:
        click.echo(f"❌ Error reading project configuration: {e}")
        sys.exit(1)


@project.command("validate")
def validate_project() -> None:
    """✅ Validate project configuration and structure"""
    project_root = get_project_root()
    config_file = get_config_file()
    errors = []
    warnings = []

    click.echo("🔍 Validating Nexus project...")

    # Check for required files
    required_files = ["nexus_config.yaml", "main.py"]
    for file_name in required_files:
        if not (project_root / file_name).exists():
            errors.append(f"Missing required file: {file_name}")

    # Check configuration
    if config_file.exists():
        try:
            config = load_config(str(config_file))

            # Validate required config sections
            if not hasattr(config, "app") or not config.app.name:
                errors.append("Configuration missing app.name")

            if not hasattr(config, "database"):
                warnings.append("No database configuration found")

        except Exception as e:
            errors.append(f"Invalid configuration file: {e}")

    # Check plugins directory
    plugins_dir = get_plugins_dir()
    if plugins_dir.exists():
        plugin_errors = validate_plugins_directory(plugins_dir)
        errors.extend(plugin_errors)
    else:
        warnings.append("No plugins directory found")

    # Report results
    if errors:
        click.echo("❌ Validation failed with errors:")
        for error in errors:
            click.echo(f"  • {error}")
        sys.exit(1)
    elif warnings:
        click.echo("⚠️  Project is valid but has warnings:")
        for warning in warnings:
            click.echo(f"  • {warning}")
        click.echo("✅ Project structure is valid")
    else:
        click.echo("✅ Project validation passed successfully!")


# =============================================================================
# SERVER COMMANDS
# =============================================================================


@cli.command("run")
@click.option(
    "--host", default="127.0.0.1", help="Host to bind to (use 0.0.0.0 for all interfaces)"
)
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--workers", default=1, type=int, help="Number of worker processes")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.pass_context
def run(ctx: Any, host: str, port: int, reload: bool, workers: int, debug: bool) -> None:
    """🚀 Run the Nexus application server"""
    # Security warning for binding to all interfaces
    if host == "0.0.0.0":  # nosec B104 - We explicitly warn users about security implications
        click.echo(
            "⚠️  WARNING: Binding to 0.0.0.0 makes the server accessible from any network interface.",
            err=True,
        )
        click.echo("   This may be a security risk in production environments.", err=True)
        click.echo("   Consider using 127.0.0.1 for local-only access.", err=True)
        click.echo("")

    config_path = ctx.obj.get("config_path")

    click.echo(f"🚀 Starting Nexus Framework v{__version__}")

    if not get_config_file().exists():
        click.echo("❌ No nexus_config.yaml found. Run 'nexus project init' first.")
        sys.exit(1)

    try:
        # Import uvicorn here to avoid import errors if not installed
        import uvicorn

        # Determine the app module
        if Path("main.py").exists():
            app_module = "main:app"
        else:
            click.echo("❌ No main.py file found")
            sys.exit(1)

        # Configure uvicorn
        uvicorn_config = {
            "host": host,
            "port": port,
            "reload": reload,
            "workers": workers if not reload else 1,
            "log_level": "debug" if debug or ctx.obj["verbose"] else "info",
        }

        click.echo(f"🌐 Server starting on http://{host}:{port}")
        click.echo(f"🔄 Hot reload: {'Enabled' if reload else 'Disabled'}")
        click.echo(f"👷 Workers: {uvicorn_config['workers']}")
        click.echo("🎯 Press Ctrl+C to stop")

        uvicorn.run(
            app_module,
            host=str(uvicorn_config["host"]),
            port=int(str(uvicorn_config["port"])),
            reload=bool(uvicorn_config["reload"]),
            workers=int(str(uvicorn_config["workers"])),
            log_level=str(uvicorn_config["log_level"]),
        )

    except ImportError:
        click.echo("❌ uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)
    except KeyboardInterrupt:
        click.echo("\n👋 Server stopped")
    except Exception as e:
        click.echo(f"❌ Failed to start server: {e}")
        sys.exit(1)


@cli.command("dev")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.pass_context
def dev(ctx: Any, port: int) -> None:
    """⚡ Run development server with hot reload and debugging"""
    ctx.invoke(run, host="127.0.0.1", port=port, reload=True, debug=True)


# =============================================================================
# PLUGIN MANAGEMENT COMMANDS
# =============================================================================


@cli.group()
@click.pass_context
def plugin(ctx: Any) -> None:
    """🔌 Plugin management commands"""
    pass


@plugin.command("create")
@click.argument("name")
@click.option(
    "--category",
    "-c",
    default="custom",
    type=click.Choice(["core", "business", "ui", "security", "custom"]),
    help="Plugin category",
)
@click.option("--description", "-d", default="", help="Plugin description")
@click.option("--author", "-a", default="", help="Plugin author")
@click.option("--version", "-v", default="1.0.0", help="Plugin version")
@click.option(
    "--template",
    "-t",
    default="basic",
    type=click.Choice(["basic", "api", "web", "database", "service"]),
    help="Plugin template",
)
def create_plugin(
    name: str, category: str, description: str, author: str, version: str, template: str
) -> None:
    """🎨 Create a new plugin"""
    plugins_dir = get_plugins_dir()

    if not plugins_dir.exists():
        click.echo("❌ Not in a Nexus project (no plugins directory found)")
        sys.exit(1)

    plugin_path = plugins_dir / category / name

    if plugin_path.exists():
        click.echo(f"❌ Plugin '{name}' already exists in category '{category}'")
        sys.exit(1)

    click.echo(f"🎨 Creating plugin: {name}")
    click.echo(f"📂 Category: {category}")
    click.echo(f"📋 Template: {template}")

    # Create plugin directory structure
    plugin_path.mkdir(parents=True)
    (plugin_path / "static").mkdir(exist_ok=True)
    (plugin_path / "templates").mkdir(exist_ok=True)
    (plugin_path / "tests").mkdir(exist_ok=True)

    # Generate plugin files
    manifest_content = generate_plugin_manifest(name, description, author, version, category)
    (plugin_path / "manifest.json").write_text(manifest_content)

    plugin_code = generate_plugin_code(name, template, description)
    (plugin_path / "plugin.py").write_text(plugin_code)

    # Create __init__.py
    init_content = f'"""Plugin: {name}"""\n\nfrom .plugin import {to_class_name(name)}\n\n__all__ = ["{to_class_name(name)}"]\n'
    (plugin_path / "__init__.py").write_text(init_content)

    # Create README
    readme_content = generate_plugin_readme(name, description, author, category)
    (plugin_path / "README.md").write_text(readme_content)

    # Create requirements.txt if needed
    requirements = generate_plugin_requirements(template)
    if requirements:
        (plugin_path / "requirements.txt").write_text(requirements)

    # Create test file
    test_content = generate_plugin_test(name)
    (plugin_path / "tests" / f"test_{name}.py").write_text(test_content)

    click.echo(f"✅ Plugin '{name}' created successfully!")
    click.echo(f"📁 Location: {plugin_path}")
    click.echo("\n📋 Next steps:")
    click.echo(f"   cd {plugin_path}")
    click.echo("   # Edit plugin.py to implement your functionality")
    click.echo("   nexus plugin validate " + name)
    click.echo("   nexus run --reload")


@plugin.command("list")
@click.option("--category", "-c", help="Filter by category")
@click.option("--status", "-s", type=click.Choice(["enabled", "disabled", "all"]), default="all")
def list_plugins(category: Optional[str], status: str) -> None:
    """📋 List all plugins"""
    plugins_dir = get_plugins_dir()

    if not plugins_dir.exists():
        click.echo("❌ No plugins directory found")
        return

    plugins = discover_plugins(plugins_dir, category)

    if not plugins:
        click.echo("📦 No plugins found")
        return

    click.echo(f"🔌 Found {len(plugins)} plugin(s):")
    click.echo("=" * 60)

    for plugin in plugins:
        status_icon = "✅" if plugin.get("enabled", False) else "⭕"
        click.echo(f"{status_icon} {plugin['name']} ({plugin['category']})")
        click.echo(f"   📝 {plugin['description']}")
        click.echo(f"   📦 v{plugin['version']} by {plugin['author']}")
        click.echo(f"   📁 {plugin['path']}")
        click.echo()


@plugin.command("info")
@click.argument("name")
def plugin_info(name: str) -> None:
    """ℹ️ Show detailed plugin information"""
    plugin = find_plugin(name)

    if not plugin:
        click.echo(f"❌ Plugin '{name}' not found")
        sys.exit(1)

    click.echo(f"🔌 Plugin Information: {name}")
    click.echo("=" * 50)
    click.echo(f"📝  Description: {plugin['description']}")
    click.echo(f"📦  Version: {plugin['version']}")
    click.echo(f"👤  Author: {plugin['author']}")
    click.echo(f"📂  Category: {plugin['category']}")
    click.echo(f"📄  License: {plugin.get('license', 'Not specified')}")
    click.echo(f"📁  Path: {plugin['path']}")
    click.echo(f"🏷️   Tags: {', '.join(plugin.get('tags', []))}")
    click.echo(f"🔗  Dependencies: {', '.join(plugin.get('dependencies', {}).keys())}")
    click.echo(f"🔐  Permissions: {', '.join(plugin.get('permissions', []))}")


@plugin.command("validate")
@click.argument("name", required=False)
def validate_plugin(name: Optional[str]) -> None:
    """✅ Validate plugin(s)"""
    plugins_dir = get_plugins_dir()

    if not plugins_dir.exists():
        click.echo("❌ No plugins directory found")
        sys.exit(1)

    if name:
        # Validate specific plugin
        plugin = find_plugin(name)
        if not plugin:
            click.echo(f"❌ Plugin '{name}' not found")
            sys.exit(1)

        errors = validate_single_plugin(plugin)
        if errors:
            click.echo(f"❌ Plugin '{name}' validation failed:")
            for error in errors:
                click.echo(f"  • {error}")
            sys.exit(1)
        else:
            click.echo(f"✅ Plugin '{name}' is valid")
    else:
        # Validate all plugins
        plugins = discover_plugins(plugins_dir)
        total_errors = 0

        click.echo(f"🔍 Validating {len(plugins)} plugins...")

        for plugin in plugins:
            errors = validate_single_plugin(plugin)
            if errors:
                click.echo(f"❌ {plugin['name']}:")
                for error in errors:
                    click.echo(f"  • {error}")
                total_errors += len(errors)
            else:
                click.echo(f"✅ {plugin['name']}")

        if total_errors > 0:
            click.echo(f"\n❌ Validation completed with {total_errors} errors")
            sys.exit(1)
        else:
            click.echo("\n✅ All plugins are valid!")


@plugin.command("install")
@click.argument("source")
@click.option("--category", "-c", default="custom", help="Plugin category")
def install_plugin(source: str, category: str) -> None:
    """📦 Install plugin from URL or local path"""
    click.echo(f"📦 Installing plugin from: {source}")
    # TODO: Implement plugin installation from git, zip, or local path
    click.echo("🚧 Plugin installation feature coming soon!")


@plugin.command("enable")
@click.argument("plugin_name")
@click.option("--no-routes", is_flag=True, help="Skip route registration")
def enable_plugin_cmd(plugin_name: str, no_routes: bool) -> None:
    """🟢 Enable a plugin"""
    import asyncio

    from nexus.config import create_default_config
    from nexus.factory import create_nexus_app

    click.echo(f"🟢 Enabling plugin '{plugin_name}'...")

    try:
        # Load configuration
        config_file = get_config_file()
        if config_file and config_file.exists():
            from nexus.config import load_config

            config = load_config(str(config_file))
        else:
            config = create_default_config()

        # Create app instance
        app = create_nexus_app(
            title="Nexus CLI", version="1.0.0", description="CLI plugin management", config=config
        )

        async def enable_async() -> bool:
            await app._startup()

            # Check if plugin exists
            plugin_info = app.plugin_manager.get_plugin_info(plugin_name)
            if not plugin_info:
                # Try discovering first
                from pathlib import Path

                plugins_path = Path(getattr(config.plugins, "directory", "plugins"))
                await app.plugin_manager.discover_plugins(plugins_path)
                plugin_info = app.plugin_manager.get_plugin_info(plugin_name)

                if not plugin_info:
                    click.echo(f"❌ Plugin '{plugin_name}' not found")
                    return False

            # Enable plugin
            success = await app.plugin_manager.enable_plugin(
                plugin_name, enable_routes=not no_routes
            )

            await app._shutdown()
            return success

        success = asyncio.run(enable_async())

        if success:
            routes_msg = "" if no_routes else " (routes registered)"
            click.echo(f"✅ Plugin '{plugin_name}' enabled successfully{routes_msg}")
        else:
            click.echo(f"❌ Failed to enable plugin '{plugin_name}'")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error enabling plugin: {e}")
        sys.exit(1)


@plugin.command("disable")
@click.argument("plugin_name")
@click.option("--no-routes", is_flag=True, help="Skip route removal")
def disable_plugin_cmd(plugin_name: str, no_routes: bool) -> None:
    """🔴 Disable a plugin"""
    import asyncio

    from nexus.config import create_default_config
    from nexus.factory import create_nexus_app

    click.echo(f"🔴 Disabling plugin '{plugin_name}'...")

    try:
        # Load configuration
        config_file = get_config_file()
        if config_file and config_file.exists():
            from nexus.config import load_config

            config = load_config(str(config_file))
        else:
            config = create_default_config()

        # Create app instance
        app = create_nexus_app(
            title="Nexus CLI", version="1.0.0", description="CLI plugin management", config=config
        )

        async def disable_async() -> bool:
            await app._startup()

            # Check if plugin exists
            plugin_info = app.plugin_manager.get_plugin_info(plugin_name)
            if not plugin_info:
                click.echo(f"❌ Plugin '{plugin_name}' not found")
                return False

            # Disable plugin
            success = await app.plugin_manager.disable_plugin(
                plugin_name, disable_routes=not no_routes
            )

            await app._shutdown()
            return success

        success = asyncio.run(disable_async())

        if success:
            routes_msg = "" if no_routes else " (routes removed)"
            click.echo(f"✅ Plugin '{plugin_name}' disabled successfully{routes_msg}")
        else:
            click.echo(f"❌ Failed to disable plugin '{plugin_name}'")
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error disabling plugin: {e}")
        sys.exit(1)


# =============================================================================
# CONFIGURATION COMMANDS
# =============================================================================


@cli.group()
def config() -> None:
    """⚙️ Configuration management commands"""
    pass


@config.command("show")
@click.option("--section", "-s", help="Show specific configuration section")
def show_config(section: Optional[str]) -> None:
    """📄 Show current configuration"""
    config_file = get_config_file()

    if not config_file.exists():
        click.echo("❌ No configuration file found")
        sys.exit(1)

    try:
        with open(config_file) as f:
            config_data = yaml.safe_load(f)

        if section:
            if section in config_data:
                click.echo(f"⚙️ Configuration section: {section}")
                click.echo(yaml.dump({section: config_data[section]}, default_flow_style=False))
            else:
                click.echo(f"❌ Section '{section}' not found")
                sys.exit(1)
        else:
            click.echo("⚙️ Current Configuration:")
            click.echo(yaml.dump(config_data, default_flow_style=False))

    except Exception as e:
        click.echo(f"❌ Error reading configuration: {e}")
        sys.exit(1)


@config.command("validate")
def validate_config() -> None:
    """✅ Validate configuration file"""
    config_file = get_config_file()

    if not config_file.exists():
        click.echo("❌ No configuration file found")
        sys.exit(1)

    try:
        config = load_config(str(config_file))

        # Validate required fields
        errors = []

        # Check app section
        if not hasattr(config, "app") or not config.app:
            errors.append("Missing required 'app' section")
        else:
            if not hasattr(config.app, "name") or not config.app.name:
                errors.append("Missing required 'app.name' field")
            if not hasattr(config.app, "environment") or not config.app.environment:
                errors.append("Missing required 'app.environment' field")

        # Check database section
        if not hasattr(config, "database") or not config.database:
            errors.append("Missing required 'database' section")
        else:
            if not hasattr(config.database, "type") or not config.database.type:
                errors.append("Missing required 'database.type' field")

        # Check server section
        if not hasattr(config, "server") or not config.server:
            errors.append("Missing required 'server' section")
        else:
            if not hasattr(config.server, "host") or not config.server.host:
                errors.append("Missing required 'server.host' field")
            if not hasattr(config.server, "port") or not config.server.port:
                errors.append("Missing required 'server.port' field")

        if errors:
            click.echo("❌ Configuration validation failed:")
            for error in errors:
                click.echo(f"  • {error}")
            sys.exit(1)

        click.echo("✅ Configuration is valid")

        # Show some key info
        click.echo(f"📝 App: {config.app.name}")
        click.echo(
            f"🗃️  Database: {config.database.type if config.database and hasattr(config.database, 'type') else 'Not configured'}"
        )
        click.echo(f"🌐 Server: {config.server.host}:{config.server.port}")

    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}")
        sys.exit(1)


@config.command("init")
@click.option(
    "--template",
    "-t",
    default="basic",
    type=click.Choice(["basic", "production", "development"]),
    help="Configuration template",
)
@click.option("--force", "-f", is_flag=True, help="Overwrite existing config")
def init_config(template: str, force: bool) -> None:
    """🎯 Initialize configuration file"""
    config_file = get_config_file()

    if config_file.exists() and not force:
        click.echo("❌ Configuration file already exists. Use --force to overwrite.")
        sys.exit(1)

    config_content = generate_config_yaml(
        "My Nexus App", "A Nexus Framework Application", "", template
    )
    config_file.write_text(config_content)

    click.echo(f"✅ Configuration file created: {config_file}")
    click.echo(f"📋 Template: {template}")


# =============================================================================
# DATABASE COMMANDS
# =============================================================================


@cli.group()
def db() -> None:
    """🗃️ Database management commands"""
    pass


@db.command("init")
def init_database() -> None:
    """🎯 Initialize database"""
    click.echo("🗃️ Initializing database...")
    # TODO: Implement database initialization
    click.echo("🚧 Database initialization feature coming soon!")


@db.command("migrate")
def migrate_database() -> None:
    """🔄 Run database migrations"""
    click.echo("🔄 Running database migrations...")
    # TODO: Implement database migrations
    click.echo("🚧 Database migration feature coming soon!")


@db.command("reset")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation")
def reset_database(yes: bool) -> None:
    """⚠️ Reset database (destructive)"""
    if not yes:
        if not click.confirm("⚠️ This will delete all data. Continue?"):
            click.echo("❌ Operation cancelled")
            return

    click.echo("🗃️ Resetting database...")
    # TODO: Implement database reset
    click.echo("🚧 Database reset feature coming soon!")


# =============================================================================
# TESTING COMMANDS
# =============================================================================


@cli.group()
def test() -> None:
    """🧪 Testing commands"""
    pass


@test.command("run")
@click.option("--plugin", "-p", help="Test specific plugin")
@click.option("--coverage", "-c", is_flag=True, help="Generate coverage report")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def run_tests(plugin: Optional[str], coverage: bool, verbose: bool) -> None:
    """🧪 Run tests"""
    try:
        cmd = ["python", "-m", "pytest"]

        if plugin:
            plugin_path = find_plugin(plugin)
            if not plugin_path:
                click.echo(f"❌ Plugin '{plugin}' not found")
                sys.exit(1)
            cmd.extend([f"{plugin_path['path']}/tests"])
        else:
            cmd.extend(["tests/"])

        if coverage:
            cmd.extend(["--cov=.", "--cov-report=html", "--cov-report=term"])

        if verbose:
            cmd.append("-v")

        click.echo("🧪 Running tests...")
        result = subprocess.run(cmd, check=False)

        if result.returncode == 0:
            click.echo("✅ All tests passed!")
        else:
            click.echo("❌ Some tests failed")
            sys.exit(1)

    except FileNotFoundError:
        click.echo("❌ pytest not installed. Install with: pip install pytest")
        sys.exit(1)


# =============================================================================
# DEVELOPMENT COMMANDS
# =============================================================================


@cli.group("dev-tools")
def dev_tools() -> None:
    """🛠️ Development tools"""
    pass


@dev_tools.command("shell")
def dev_shell() -> None:
    """🐚 Start interactive development shell"""
    click.echo("🐚 Starting Nexus development shell...")

    try:
        import IPython

        # Setup shell environment
        config_file = get_config_file()
        if config_file.exists():
            app = create_nexus_app(config=str(config_file))

            click.echo("✅ Nexus app loaded as 'app'")
            IPython.embed(header="🚀 Nexus Development Shell\nApp instance available as 'app'")  # type: ignore
        else:
            IPython.embed(header="🚀 Nexus Development Shell")  # type: ignore

    except ImportError:
        click.echo("❌ IPython not installed. Install with: pip install ipython")
        sys.exit(1)


@dev_tools.command("docs")
@click.option("--serve", "-s", is_flag=True, help="Serve documentation locally")
@click.option("--port", default=8001, help="Port for documentation server")
def generate_docs(serve: bool, port: int) -> None:
    """📚 Generate project documentation"""
    click.echo("📚 Generating documentation...")

    # TODO: Implement documentation generation
    if serve:
        click.echo(f"🌐 Serving docs at http://localhost:{port}")
        # TODO: Implement doc server

    click.echo("🚧 Documentation generation feature coming soon!")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def to_class_name(name: str) -> str:
    """Convert plugin name to class name."""
    return "".join(word.capitalize() for word in name.replace("-", "_").split("_"))


def discover_plugins(
    plugins_dir: Path, category_filter: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Discover all plugins in the plugins directory."""
    plugins = []

    for category_dir in plugins_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("."):
            continue

        if category_filter and category_dir.name != category_filter:
            continue

        for plugin_dir in category_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("."):
                continue

            manifest_file = plugin_dir / "manifest.json"
            if manifest_file.exists():
                try:
                    with open(manifest_file) as f:
                        manifest = json.load(f)

                    manifest["path"] = str(plugin_dir)
                    manifest["category"] = category_dir.name
                    plugins.append(manifest)
                except Exception as e:
                    logger.warning(f"Error reading manifest for {plugin_dir}: {e}")

    return plugins


def find_plugin(name: str) -> Optional[Dict[str, Any]]:
    """Find a plugin by name."""
    plugins_dir = get_plugins_dir()
    if not plugins_dir.exists():
        return None

    plugins = discover_plugins(plugins_dir)
    return next((p for p in plugins if p["name"] == name), None)


def validate_single_plugin(plugin: Dict[str, Any]) -> List[str]:
    """Validate a single plugin and return list of errors."""
    errors = []
    plugin_path = Path(plugin["path"])

    # Check required files
    required_files = ["plugin.py", "manifest.json"]
    for file_name in required_files:
        if not (plugin_path / file_name).exists():
            errors.append(f"Missing required file: {file_name}")

    # Validate manifest
    try:
        manifest_file = plugin_path / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file) as f:
                manifest = json.load(f)

            required_fields = ["name", "version", "description"]
            for field in required_fields:
                if not manifest.get(field):
                    errors.append(f"Manifest missing required field: {field}")
    except Exception as e:
        errors.append(f"Invalid manifest.json: {e}")

    return errors


def validate_plugins_directory(plugins_dir: Path) -> List[str]:
    """Validate the plugins directory structure."""
    errors = []

    # Check for valid category directories
    valid_categories = {"core", "business", "ui", "security", "custom"}
    for item in plugins_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            if item.name not in valid_categories:
                errors.append(f"Invalid plugin category: {item.name}")

    return errors


def generate_main_py(name: str, template: str, description: str, author: str) -> str:
    """Generate main.py content based on template."""
    if template == "api":
        return f'''#!/usr/bin/env python3
"""
{name} - API Server
{description}
"""

import nexus

def create_app():
    """Create the Nexus application."""
    return nexus.create_api_app(
        title="{name}",
        version="1.0.0",
        description="{description}",
        config="nexus_config.yaml"
    )

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
'''
    elif template == "microservice":
        return f'''#!/usr/bin/env python3
"""
{name} - Microservice
{description}
"""

import nexus

def create_app():
    """Create the Nexus microservice."""
    return nexus.create_microservice(
        name="{name.lower().replace(' ', '_')}",
        version="1.0.0",
        config="nexus_config.yaml"
    )

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
'''
    elif template == "web":
        return f'''#!/usr/bin/env python3
"""
{name} - Web Application
{description}
"""

import nexus

def create_app():
    """Create the Nexus web application."""
    return nexus.create_web_app(
        title="{name}",
        version="1.0.0",
        config="nexus_config.yaml"
    )

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
'''
    else:  # basic
        return f'''#!/usr/bin/env python3
"""
{name} - Nexus Application
{description}
"""

import nexus

def create_app():
    """Create the Nexus application."""
    return nexus.create_nexus_app(
        title="{name}",
        version="1.0.0",
        description="{description}",
        config="nexus_config.yaml"
    )

app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
'''


def generate_config_yaml(name: str, description: str, author: str, template: str = "basic") -> str:
    """Generate configuration YAML content."""
    if template == "production":
        return f"""# {name} - Production Configuration
app:
  name: "{name}"
  description: "{description}"
  version: "1.0.0"
  author: "{author}"
  debug: false
  host: "0.0.0.0"
  port: 8000

database:
  type: "postgresql"
  host: "localhost"
  port: 5432
  database: "{name.lower().replace(' ', '_')}"
  username: "nexus_user"
  password: "${{DATABASE_PASSWORD}}"
  pool_size: 10
  max_overflow: 20

cors:
  enabled: true
  origins:
    - "https://yourdomain.com"
    - "https://api.yourdomain.com"
  credentials: true
  methods: ["GET", "POST", "PUT", "DELETE"]
  headers: ["*"]

security:
  secret_key: "${{SECRET_KEY}}"
  algorithm: "HS256"
  access_token_expire_minutes: 30

logging:
  level: "INFO"
  file: "logs/app.log"
  max_size: "10MB"
  backup_count: 5

plugins:
  directory: "plugins"
  auto_discover: true
  enabled_by_default: false

monitoring:
  enabled: true
  metrics_port: 9090
"""
    elif template == "development":
        return f"""# {name} - Development Configuration
app:
  name: "{name}"
  description: "{description}"
  version: "1.0.0"
  author: "{author}"
  debug: true
  host: "127.0.0.1"
  port: 8000

database:
  type: "sqlite"
  database: "data/dev.db"

cors:
  enabled: true
  origins: ["*"]
  credentials: true
  methods: ["*"]
  headers: ["*"]

security:
  secret_key: "dev-secret-key-change-in-production"
  algorithm: "HS256"
  access_token_expire_minutes: 60

logging:
  level: "DEBUG"
  console: true

plugins:
  directory: "plugins"
  auto_discover: true
  enabled_by_default: true
  hot_reload: true

monitoring:
  enabled: false
"""
    else:  # basic
        return f"""# {name} Configuration
app:
  name: "{name}"
  description: "{description}"
  version: "1.0.0"
  author: "{author}"

database:
  type: "sqlite"
  database: "nexus.db"

cors:
  enabled: true
  origins: ["*"]

plugins:
  directory: "plugins"
  auto_discover: true
"""


def generate_requirements(template: str) -> str:
    """Generate requirements.txt content."""
    base_requirements = [
        "nexus-platform>=1.0.0",
        "uvicorn[standard]>=0.18.0",
        "fastapi>=0.100.0",
        "pydantic>=2.0.0",
        "click>=8.0.0",
        "pyyaml>=6.0",
    ]

    if template == "api":
        base_requirements.extend(
            [
                "httpx>=0.24.0",
                "python-multipart>=0.0.6",
            ]
        )
    elif template == "microservice":
        base_requirements.extend(
            [
                "httpx>=0.24.0",
                "redis>=4.0.0",
                "celery>=5.2.0",
            ]
        )
    elif template == "web":
        base_requirements.extend(
            [
                "jinja2>=3.1.0",
                "python-multipart>=0.0.6",
                "aiofiles>=23.0.0",
            ]
        )

    # Development dependencies
    dev_requirements = [
        "",
        "# Development dependencies",
        "pytest>=7.0.0",
        "pytest-asyncio>=0.21.0",
        "pytest-cov>=4.0.0",
        "black>=23.0.0",
        "isort>=5.12.0",
        "flake8>=6.0.0",
        "mypy>=1.0.0",
    ]

    return "\n".join(base_requirements + dev_requirements)


def generate_readme(name: str, description: str, author: str, template: str) -> str:
    """Generate README.md content."""
    return f"""# {name}

{description}

## Overview

This is a {template} application built with the Nexus Framework, featuring:

- 🔌 **Plugin Architecture** - Modular and extensible
- 🚀 **High Performance** - Built on FastAPI and asyncio
- 🛡️ **Enterprise Security** - Authentication and authorization
- 📊 **Real-time Monitoring** - Built-in health checks and metrics
- 🔄 **Hot Reload** - Plugin hot-swapping without restarts

## Quick Start

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd {name.lower().replace(' ', '-')}

# Install dependencies
pip install -r requirements.txt
```

### Running the Application

```bash
# Development server with hot reload
nexus run --reload

# Production server
nexus run --workers 4

# Custom host and port
nexus run --host 0.0.0.0 --port 8080
```

### Configuration

Edit `nexus_config.yaml` to configure your application:

```yaml
app:
  name: "{name}"
  description: "{description}"

database:
  type: "sqlite"  # or postgresql, mysql, etc.
  database: "nexus.db"

plugins:
  directory: "plugins"
  auto_discover: true
```

## Plugin Development

### Create a New Plugin

```bash
# Create a basic plugin
nexus plugin create my-plugin

# Create a plugin with specific template
nexus plugin create my-api-plugin --template api --category business
```

### Plugin Structure

```
plugins/
├── category/
│   └── my-plugin/
│       ├── __init__.py
│       ├── plugin.py          # Main plugin code
│       ├── manifest.json      # Plugin metadata
│       ├── README.md
│       ├── requirements.txt   # Plugin dependencies
│       ├── static/           # Static files
│       ├── templates/        # Jinja2 templates
│       └── tests/           # Plugin tests
```

## Available Commands

```bash
# Project management
nexus project init my-app        # Create new project
nexus project info              # Show project information
nexus project validate          # Validate project structure

# Development server
nexus run                       # Start server
nexus run --reload              # Start with hot reload
nexus dev                       # Start development mode

# Plugin management
nexus plugin create <name>      # Create new plugin
nexus plugin list              # List all plugins
nexus plugin info <name>       # Show plugin info
nexus plugin validate         # Validate plugins

# Configuration
nexus config show             # Show current config
nexus config validate        # Validate configuration
nexus config init            # Initialize new config

# Testing
nexus test run               # Run all tests
nexus test run --plugin <name>  # Test specific plugin
nexus test run --coverage   # Run with coverage

# Development tools
nexus dev shell             # Interactive development shell
nexus dev docs             # Generate documentation
```

## API Endpoints

Once running, your application will be available at:

- **Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **System Info**: http://localhost:8000/api/system/info
- **Debug Interface**: http://localhost:8000/debug

## Testing

```bash
# Run all tests
nexus test run

# Run with coverage
nexus test run --coverage

# Test specific plugin
nexus test run --plugin my-plugin
```

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000
CMD ["nexus", "run", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/nexus
    depends_on:
      - db

  db:
    image: postgres:15
    environment:
      POSTGRES_DB: nexus
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
```

## Architecture

```
{name}
├── main.py              # Application entry point
├── nexus_config.yaml    # Configuration file
├── plugins/            # Plugin directory
│   ├── core/          # Core system plugins
│   ├── business/      # Business logic plugins
│   ├── ui/           # User interface plugins
│   ├── security/     # Security plugins
│   └── custom/       # Custom plugins
├── tests/             # Application tests
├── docs/             # Documentation
├── logs/             # Log files
└── data/             # Data files
```

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

{author if author else "Your Name"}

## Support

- 📚 **Documentation**: [Link to documentation]
- 🐛 **Issues**: [Link to issues]
- 💬 **Discussions**: [Link to discussions]
- 📧 **Contact**: [Your contact information]

---

Built with ❤️ using [Nexus Framework](https://github.com/nexus-platform)
"""


def generate_gitignore() -> str:
    """Generate .gitignore content."""
    return """# Byte-compiled / optimized / DLL files
__pycache__/
*.py[cod]
*$py.class

# C extensions
*.so

# Distribution / packaging
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
pip-wheel-metadata/
share/python-wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST

# PyInstaller
*.manifest
*.spec

# Installer logs
pip-log.txt
pip-delete-this-directory.txt

# Unit test / coverage reports
htmlcov/
.tox/
.nox/
.coverage
.coverage.*
.cache
nosetests.xml
coverage.xml
*.cover
*.py,cover
.hypothesis/
.pytest_cache/

# Virtual environments
.env
.venv
env/
venv/
ENV/
env.bak/
venv.bak/

# IDEs
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Nexus specific
nexus.db
*.db
logs/
data/
.nexus/
temp/

# Environment variables
.env.local
.env.production
.env.staging

# Docker
.dockerignore
docker-compose.override.yml

# Temporary files
tmp/
temp/
*.tmp
*.temp
"""


def generate_pytest_ini() -> str:
    """Generate pytest.ini content."""
    return """[tool:pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
addopts =
    --strict-markers
    --strict-config
    --verbose
    --tb=short
    --asyncio-mode=auto
markers =
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks tests as integration tests
    unit: marks tests as unit tests
    plugin: marks tests as plugin tests
filterwarnings =
    ignore::UserWarning
    ignore::DeprecationWarning
"""


def generate_test_example(name: str) -> str:
    """Generate example test file."""
    return f'''"""
Tests for {name}
"""

import pytest
from fastapi.testclient import TestClient

# This will be imported when the test runs
# from main import app


class TestApplication:
    """Test the main application."""

    def test_health_endpoint(self):
        """Test the health check endpoint."""
        # client = TestClient(app.app)
        # response = client.get("/health")
        # assert response.status_code == 200
        # assert response.json()["status"] == "healthy"
        pass  # TODO: Implement after app is created

    def test_system_info(self):
        """Test the system info endpoint."""
        # client = TestClient(app.app)
        # response = client.get("/api/system/info")
        # assert response.status_code == 200
        # assert "app" in response.json()
        pass  # TODO: Implement after app is created


class TestPlugins:
    """Test plugin functionality."""

    def test_plugin_discovery(self):
        """Test plugin discovery."""
        # TODO: Implement plugin discovery tests
        pass

    def test_plugin_loading(self):
        """Test plugin loading."""
        # TODO: Implement plugin loading tests
        pass


class TestConfiguration:
    """Test configuration management."""

    def test_config_validation(self):
        """Test configuration validation."""
        # TODO: Implement configuration tests
        pass


@pytest.mark.integration
class TestIntegration:
    """Integration tests."""

    def test_full_application_startup(self):
        """Test complete application startup."""
        # TODO: Implement integration tests
        pass


@pytest.mark.asyncio
class TestAsync:
    """Test async functionality."""

    async def test_async_endpoints(self):
        """Test async endpoints."""
        # TODO: Implement async tests
        pass
'''


def generate_dockerfile() -> str:
    """Generate Dockerfile content."""
    return """# Use Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NEXUS_ENV=production

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \\
    && apt-get install -y --no-install-recommends \\
        build-essential \\
        curl \\
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \\
    && pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create necessary directories
RUN mkdir -p logs data

# Create non-root user
RUN useradd --create-home --shell /bin/bash nexus \\
    && chown -R nexus:nexus /app
USER nexus

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["nexus", "run", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
"""


def generate_docker_compose(name: str) -> str:
    """Generate docker-compose.yml content."""
    return """version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"
    environment:
      - NEXUS_ENV=production
      - DATABASE_URL=postgresql://nexus:nexus@db:5432/nexus
      - REDIS_URL=redis://redis:6379/0
    volumes:
      - ./logs:/app/logs
      - ./data:/app/data
    depends_on:
      - db
      - redis
    restart: unless-stopped
    networks:
      - nexus-network

  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_DB: nexus
      POSTGRES_USER: nexus
      POSTGRES_PASSWORD: nexus
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    restart: unless-stopped
    networks:
      - nexus-network

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - nexus-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/ssl:ro
    depends_on:
      - app
    restart: unless-stopped
    networks:
      - nexus-network

volumes:
  postgres_data:
  redis_data:

networks:
  nexus-network:
    driver: bridge
"""


def generate_plugin_manifest(
    name: str, description: str, author: str, version: str, category: str
) -> str:
    """Generate plugin manifest.json content."""
    manifest: Dict[str, Any] = {
        "name": name,
        "version": version,
        "description": description or f"A {name} plugin",
        "author": author or "Unknown",
        "category": category,
        "license": "MIT",
        "homepage": "",
        "repository": "",
        "documentation": "",
        "tags": [],
        "dependencies": {},
        "permissions": [],
        "min_nexus_version": "1.0.0",
        "max_nexus_version": None,
        "enabled": True,
        "config_schema": {
            "type": "object",
            "properties": {
                "enabled": {
                    "type": "boolean",
                    "default": True,
                    "description": "Enable/disable the plugin",
                }
            },
        },
    }

    return json.dumps(manifest, indent=2)


def generate_plugin_code(name: str, template: str, description: str) -> str:
    """Generate plugin code based on template."""
    class_name = to_class_name(name)

    if template == "api":
        return f'''"""
{name} Plugin - API Template

{description}
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


# Data models
class {class_name}Request(BaseModel):
    """Request model for {name}."""
    name: str
    value: Any


class {class_name}Response(BaseModel):
    """Response model for {name}."""
    id: str
    name: str
    value: Any
    status: str


class {class_name}(BasePlugin):
    """
    {name} Plugin - API Template

    Provides REST API endpoints for {name} functionality.
    """

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.category = "api"

    async def on_enable(self) -> None:
        """Enable the plugin."""
        logger.info(f"Enabling {{self.name}} plugin")
        # Initialize plugin resources here

    async def on_disable(self) -> None:
        """Disable the plugin."""
        logger.info(f"Disabling {{self.name}} plugin")
        # Cleanup plugin resources here

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(
            prefix=f"/plugins/{{self.name}}",
            tags=["{name}"]
        )

        @router.get("/", response_model=Dict[str, Any])
        async def get_info():
            """Get plugin information."""
            return {{
                "name": self.name,
                "version": self.version,
                "status": "running",
                "description": "{description}"
            }}

        @router.get("/items", response_model=List[{class_name}Response])
        async def list_items():
            """List all items."""
            # TODO: Implement item listing
            return []

        @router.post("/items", response_model={class_name}Response)
        async def create_item(request: {class_name}Request):
            """Create a new item."""
            # TODO: Implement item creation
            return {class_name}Response(
                id="1",
                name=request.name,
                value=request.value,
                status="created"
            )

        @router.get("/items/{{item_id}}", response_model={class_name}Response)
        async def get_item(item_id: str):
            """Get a specific item."""
            # TODO: Implement item retrieval
            raise HTTPException(status_code=404, detail="Item not found")

        @router.put("/items/{{item_id}}", response_model={class_name}Response)
        async def update_item(item_id: str, request: {class_name}Request):
            """Update an item."""
            # TODO: Implement item update
            raise HTTPException(status_code=404, detail="Item not found")

        @router.delete("/items/{{item_id}}")
        async def delete_item(item_id: str):
            """Delete an item."""
            # TODO: Implement item deletion
            raise HTTPException(status_code=404, detail="Item not found")

        return [router]

    def get_event_handlers(self) -> Dict[str, Any]:
        """Get event handlers for this plugin."""
        return {{
            f"{{self.name}}.item.created": self._handle_item_created,
            f"{{self.name}}.item.updated": self._handle_item_updated,
            f"{{self.name}}.item.deleted": self._handle_item_deleted,
        }}

    async def _handle_item_created(self, event_data: Dict[str, Any]) -> None:
        """Handle item created event."""
        logger.info(f"Item created: {{event_data}}")

    async def _handle_item_updated(self, event_data: Dict[str, Any]) -> None:
        """Handle item updated event."""
        logger.info(f"Item updated: {{event_data}}")

    async def _handle_item_deleted(self, event_data: Dict[str, Any]) -> None:
        """Handle item deleted event."""
        logger.info(f"Item deleted: {{event_data}}")
'''

    elif template == "web":
        return f'''"""
{name} Plugin - Web Template

{description}
"""

import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


class {class_name}(BasePlugin):
    """
    {name} Plugin - Web Template

    Provides web interface for {name} functionality.
    """

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.category = "web"

        # Setup templates
        template_dir = Path(__file__).parent / "templates"
        self.templates = Jinja2Templates(directory=str(template_dir))

    async def on_enable(self) -> None:
        """Enable the plugin."""
        logger.info(f"Enabling {{self.name}} plugin")

    async def on_disable(self) -> None:
        """Disable the plugin."""
        logger.info(f"Disabling {{self.name}} plugin")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(
            prefix=f"/plugins/{{self.name}}",
            tags=["{name}"]
        )

        @router.get("/", response_class=HTMLResponse)
        async def index_page(request: Request):
            """Main page for the plugin."""
            context = {{
                "request": request,
                "plugin_name": self.name,
                "plugin_version": self.version,
                "title": "{name.title()}",
            }}
            return self.templates.TemplateResponse("index.html", context)

        @router.get("/dashboard", response_class=HTMLResponse)
        async def dashboard_page(request: Request):
            """Dashboard page for the plugin."""
            context = {{
                "request": request,
                "plugin_name": self.name,
                "title": "{name.title()} Dashboard",
            }}
            return self.templates.TemplateResponse("dashboard.html", context)

        @router.get("/api/data")
        async def get_data():
            """Get plugin data via API."""
            return {{
                "plugin": self.name,
                "data": [],
                "status": "success"
            }}

        return [router]

    def get_static_files_config(self) -> Dict[str, str]:
        """Get static files configuration."""
        static_dir = Path(__file__).parent / "static"
        return {{
            "directory": str(static_dir),
            "path": f"/plugins/{{self.name}}/static"
        }}
'''

    elif template == "database":
        return f'''"""
{name} Plugin - Database Template

{description}
"""

import logging
from typing import Any, Dict, List, Optional

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


class {class_name}(BasePlugin):
    """
    {name} Plugin - Database Template

    Provides database operations for {name} functionality.
    """

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.category = "database"

    async def on_enable(self) -> None:
        """Enable the plugin."""
        logger.info(f"Enabling {{{{self.name}}}} plugin")

        # Initialize database schema
        await self._initialize_schema()

    async def on_disable(self) -> None:
        """Disable the plugin."""
        logger.info(f"Disabling {{{{self.name}}}} plugin")

    async def _initialize_schema(self) -> None:
        """Initialize database schema for this plugin."""
        if self.db_adapter:
            # Create tables/collections for this plugin
            schema = self.get_database_schema()
            await self.db_adapter.create_schema(schema)
            logger.info(f"Database schema initialized for {{{{self.name}}}}")

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {{
            "tables": {{
                f"{{{{self.name}}}}_items": {{
                    "columns": {{
                        "id": {{"type": "string", "primary_key": True}},
                        "name": {{"type": "string", "required": True}},
                        "description": {{"type": "text"}},
                        "created_at": {{"type": "datetime", "auto_now_add": True}},
                        "updated_at": {{"type": "datetime", "auto_now": True}},
                    }},
                    "indexes": [
                        {{"columns": ["name"], "unique": True}},
                        {{"columns": ["created_at"]}},
                    ]
                }}
            }}
        }}

    # Database operations
    async def create_item(self, name: str, description: str = "") -> Dict[str, Any]:
        """Create a new item."""
        if not self.db_adapter:
            raise Exception("Database not available")

        item_data = {{
            "name": name,
            "description": description,
        }}

        result = await self.db_adapter.create(f"{{{{self.name}}}}_items", item_data)
        logger.info(f"Created item: {{result}}")
        return result

    async def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        """Get an item by ID."""
        if not self.db_adapter:
            return None

        return await self.db_adapter.get(f"{{{{self.name}}}}_items", item_id)

    async def update_item(self, item_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Update an item."""
        if not self.db_adapter:
            return None

        result = await self.db_adapter.update(f"{{{{self.name}}}}_items", item_id, data)
        logger.info(f"Updated item {{item_id}}: {{result}}")
        return result

    async def delete_item(self, item_id: str) -> bool:
        """Delete an item."""
        if not self.db_adapter:
            return False

        result = await self.db_adapter.delete(f"{{{{self.name}}}}_items", item_id)
        logger.info(f"Deleted item {{item_id}}")
        return result

    async def list_items(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """List items."""
        if not self.db_adapter:
            return []

        return await self.db_adapter.list(f"{{{{self.name}}}}_items", limit=limit, offset=offset)
'''

    elif template == "service":
        return f'''"""
{name} Plugin - Service Template

{description}
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


class {class_name}(BasePlugin):
    """
    {name} Plugin - Service Template

    Provides background services for {name} functionality.
    """

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.category = "service"
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def on_enable(self) -> None:
        """Enable the plugin."""
        logger.info(f"Enabling {{self.name}} service plugin")

        # Start background service
        await self.start_service()

    async def on_disable(self) -> None:
        """Disable the plugin."""
        logger.info(f"Disabling {{self.name}} service plugin")

        # Stop background service
        await self.stop_service()

    async def start_service(self) -> None:
        """Start the background service."""
        if self._running:
            logger.warning(f"{{self.name}} service already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._service_loop())
        logger.info(f"{{self.name}} service started")

    async def stop_service(self) -> None:
        """Stop the background service."""
        if not self._running:
            return

        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info(f"{{self.name}} service stopped")

    async def _service_loop(self) -> None:
        """Main service loop."""
        while self._running:
            try:
                # Perform service work here
                await self._process_work()

                # Wait before next iteration
                await asyncio.sleep(60)  # Run every minute

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in {{{{self.name}}}} service loop: {{e}}")
                await asyncio.sleep(10)  # Wait before retrying

    async def _process_work(self) -> None:
        """Process service work."""
        # TODO: Implement service logic here
        logger.debug(f"{{{{self.name}}}} service processing work")

    def get_service_status(self) -> Dict[str, Any]:
        """Get service status."""
        return {{
            "name": "{{self.name}}",
            "version": "{{self.version}}",
            "running": self._running,
            "task_running": self._task is not None and not self._task.done(),
        }}
'''

    else:  # basic template
        return f'''"""
{name} Plugin

{description}
"""

import logging
from typing import Any, Dict, List

from fastapi import APIRouter

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


class {class_name}(BasePlugin):
    """
    {name} Plugin

    A basic plugin for {name} functionality.
    """

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.description = "{description}"

    async def on_enable(self) -> None:
        """Called when the plugin is enabled."""
        logger.info(f"Enabling {{{{self.name}}}} plugin")

        # Initialize plugin resources here
        await self._initialize()

    async def on_disable(self) -> None:
        """Called when the plugin is disabled."""
        logger.info(f"Initializing {{{{self.name}}}} plugin")

        # Cleanup plugin resources here
        await self._cleanup()

    async def _initialize(self) -> None:
        """Initialize plugin resources."""
        # TODO: Add initialization logic
        pass

    async def _cleanup(self) -> None:
        """Cleanup plugin resources."""
        # TODO: Add cleanup logic
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(
            prefix=f"/plugins/{{{{self.name}}}}",
            tags=["{{self.name}}"]
        )

        @router.get("/")
        async def get_plugin_info():
            """Get plugin information."""
            return {{
                "name": "{{self.name}}",
                "version": "{{self.version}}",
                "description": "{{self.description}}",
                "status": "running"
            }}

        @router.get("/health")
        async def health_check():
            """Plugin health check."""
            return {{
                "plugin": "{{self.name}}",
                "status": "healthy",
                "version": "{{self.version}}"
            }}

        return [router]

    def get_event_handlers(self) -> Dict[str, Any]:
        """Get event handlers for this plugin."""
        return {{
            f"{{{{self.name}}}}.test": self._handle_test_event,
        }}

    async def _handle_test_event(self, event_data: Dict[str, Any]) -> None:
        """Handle test event."""
        logger.info(f"Received test event: {{event_data}}")
'''


def generate_plugin_readme(name: str, description: str, author: str, category: str) -> str:
    """Generate plugin README.md content."""
    class_name = to_class_name(name)

    return f"""# {name.title()} Plugin

{description}

## Overview

This is a {category} plugin for the Nexus Framework that provides {name} functionality.

## Features

- 🔌 **Modular Design** - Clean plugin architecture
- 🚀 **High Performance** - Async/await support
- 📊 **API Endpoints** - RESTful API interface
- 🔄 **Event System** - Event-driven architecture
- 🛡️ **Error Handling** - Robust error management

## Installation

This plugin is automatically discovered when placed in the correct plugins directory:

```
plugins/{category}/{name}/
```

## Configuration

Add the following to your `nexus_config.yaml`:

```yaml
plugins:
  {name}:
    enabled: true
    # Add plugin-specific configuration here
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/plugins/{name}/` | Get plugin information |
| GET | `/plugins/{name}/health` | Plugin health check |

## Events

### Published Events

- `{name}.started` - When plugin starts
- `{name}.stopped` - When plugin stops

### Subscribed Events

- `{name}.test` - Test event handler

## Usage

### Basic Usage

```python
# The plugin is automatically loaded by the Nexus Framework
# Access via the plugin manager:

plugin = app.plugin_manager.get_plugin('{name}')
if plugin:
    status = plugin.get_service_status()
    print(f"Plugin status: {{status}}")
```

### API Usage

```bash
# Get plugin information
curl http://localhost:8000/plugins/{name}/

# Check plugin health
curl http://localhost:8000/plugins/{name}/health
```

## Development

### Testing

```bash
# Run plugin tests
nexus test run --plugin {name}

# Run with coverage
nexus test run --plugin {name} --coverage
```

### Debugging

```bash
# Validate plugin
nexus plugin validate {name}

# Check plugin info
nexus plugin info {name}
```

## Plugin Structure

```
{name}/
├── __init__.py          # Plugin initialization
├── plugin.py            # Main plugin code ({class_name})
├── manifest.json        # Plugin metadata
├── README.md           # This file
├── requirements.txt    # Plugin dependencies
├── static/             # Static files (CSS, JS, images)
├── templates/          # Jinja2 templates
└── tests/             # Plugin tests
    └── test_{name}.py
```

## Dependencies

See `requirements.txt` for plugin-specific dependencies.

## Configuration Schema

```json
{{
  "type": "object",
  "properties": {{
    "enabled": {{
      "type": "boolean",
      "default": true,
      "description": "Enable/disable the plugin"
    }}
  }}
}}
```

## License

MIT License

## Author

{author or "Unknown"}

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Support

- 📚 **Documentation**: [Plugin Documentation]
- 🐛 **Issues**: [Report Issues]
- 💬 **Discussions**: [Join Discussions]

---

Built with ❤️ using [Nexus Framework](https://github.com/nexus-platform)
"""


def generate_plugin_requirements(template: str) -> str:
    """Generate plugin requirements.txt content."""
    if template == "api":
        return """# API Template Dependencies
httpx>=0.24.0
pydantic>=2.0.0
"""
    elif template == "web":
        return """# Web Template Dependencies
jinja2>=3.1.0
aiofiles>=23.0.0
"""
    elif template == "database":
        return """# Database Template Dependencies
sqlalchemy>=2.0.0
alembic>=1.11.0
"""
    elif template == "service":
        return """# Service Template Dependencies
celery>=5.2.0
redis>=4.0.0
"""
    else:
        return """# Basic Template Dependencies
# Add plugin-specific dependencies here
"""


def generate_plugin_test(name: str) -> str:
    """Generate plugin test file."""
    class_name = to_class_name(name)

    return f'''"""
Tests for {name} plugin
"""

import pytest
from unittest.mock import AsyncMock, Mock

from {name}.plugin import {class_name}


class Test{class_name}:
    """Test the {name} plugin."""

    @pytest.fixture
    def plugin(self):
        """Create a plugin instance for testing."""
        return {class_name}()

    def test_plugin_initialization(self, plugin):
        """Test plugin initialization."""
        assert plugin.name == "{name}"
        assert plugin.version == "1.0.0"
        assert isinstance(plugin.description, str)

    @pytest.mark.asyncio
    async def test_plugin_enable(self, plugin):
        """Test plugin enable."""
        await plugin.on_enable()
        # Add assertions based on plugin functionality

    @pytest.mark.asyncio
    async def test_plugin_disable(self, plugin):
        """Test plugin disable."""
        await plugin.on_disable()
        # Add assertions based on plugin functionality

    def test_get_api_routes(self, plugin):
        """Test API routes."""
        routes = plugin.get_api_routes()
        assert isinstance(routes, list)
        assert len(routes) > 0

    def test_get_event_handlers(self, plugin):
        """Test event handlers."""
        handlers = plugin.get_event_handlers()
        assert isinstance(handlers, dict)

    @pytest.mark.asyncio
    async def test_event_handler(self, plugin):
        """Test event handling."""
        event_data = {{"test": "data"}}

        # Test the event handler
        handler = plugin.get_event_handlers().get(f"{name}.test")
        if handler:
            await handler(event_data)


class Test{class_name}Integration:
    """Integration tests for {name} plugin."""

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_plugin_lifecycle(self):
        """Test complete plugin lifecycle."""
        plugin = {class_name}()

        # Test enable
        await plugin.on_enable()

        # Test functionality
        routes = plugin.get_api_routes()
        assert len(routes) > 0

        # Test disable
        await plugin.on_disable()

    @pytest.mark.integration
    def test_plugin_api_endpoints(self):
        """Test plugin API endpoints."""
        # TODO: Implement API endpoint tests
        pass

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_plugin_events(self):
        """Test plugin event handling."""
        # TODO: Implement event handling tests
        pass
'''


def main() -> None:
    """Main CLI entry point."""
    try:
        cli()
    except KeyboardInterrupt:
        click.echo("\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n💥 Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
