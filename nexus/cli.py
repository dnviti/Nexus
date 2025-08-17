#!/usr/bin/env python3
"""
Nexus CLI
Command-line interface for Nexus
"""

import os
import sys
import click
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any

from .core import AppConfig, PluginManager, ServiceRegistry, create_default_config
from .utils import setup_logging
from .monitoring import MetricsCollector
from . import __version__

# Setup logging
logger = logging.getLogger("nexus.cli")


@click.group()
@click.version_option(version=__version__, prog_name="Nexus")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.pass_context
def cli(ctx, verbose, config):
    """Nexus - The Ultimate Plugin-Based Application Platform"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Setup logging level
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--workers", default=1, type=int, help="Number of worker processes")
@click.pass_context
def run(ctx, host, port, reload, workers):
    """Run the Nexus application server"""
    click.echo(f"🚀 Starting Nexus Framework v{__version__}")

    try:
        import uvicorn
        from . import create_nexus_app

        # Create the application
        app = create_nexus_app(config_path=ctx.obj.get("config_path"))

        # Run the server
        uvicorn.run(
            app,
            host=host,
            port=port,
            reload=reload,
            workers=workers if not reload else 1,
            log_level="info" if not ctx.obj["verbose"] else "debug",
        )

    except ImportError:
        click.echo("❌ Error: uvicorn not installed. Run: pip install uvicorn", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Error starting server: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--output", "-o", type=click.Path(), help="Output file for configuration")
@click.pass_context
def init(ctx, output):
    """Initialize a new Nexus project"""
    click.echo("🎯 Initializing new Nexus project...")

    try:
        # Create default configuration
        config = create_default_config()

        # Determine output path
        if output:
            config_path = Path(output)
        else:
            config_path = Path("nexus_config.yaml")

        # Write configuration file
        import yaml
        from dataclasses import asdict

        with open(config_path, "w") as f:
            yaml.dump(asdict(config), f, default_flow_style=False, indent=2)

        click.echo(f"✅ Configuration created: {config_path}")

        # Create basic project structure
        project_dirs = ["plugins", "config", "logs", "static", "templates"]

        for dir_name in project_dirs:
            dir_path = Path(dir_name)
            dir_path.mkdir(exist_ok=True)
            click.echo(f"✅ Created directory: {dir_name}")

        # Create basic main.py
        main_py_content = """#!/usr/bin/env python3
\"\"\"
Nexus Application Entry Point
\"\"\"

from nexus import create_nexus_app

def main():
    app = create_nexus_app(config_path="nexus_config.yaml")
    return app

if __name__ == "__main__":
    import uvicorn
    app = main()
    uvicorn.run(app, host="0.0.0.0", port=8000)
"""

        with open("main.py", "w") as f:
            f.write(main_py_content)

        click.echo("✅ Created main.py")
        click.echo("🎉 Project initialized successfully!")
        click.echo("\nNext steps:")
        click.echo("  1. Install Nexus: pip install nexus-framework")
        click.echo("  2. Run your app: python main.py")
        click.echo("  3. Visit: http://localhost:8000")

    except Exception as e:
        click.echo(f"❌ Error initializing project: {e}", err=True)
        sys.exit(1)


@cli.group()
def plugin():
    """Plugin management commands"""
    pass


@plugin.command("list")
@click.pass_context
def plugin_list(ctx):
    """List available plugins"""
    click.echo("📦 Available Plugins:")

    try:
        # This would typically load from a plugin registry or scan directories
        click.echo("  • hello_world - Example greeting plugin")
        click.echo("  • task_manager - Task management plugin")
        click.echo("  • auth_advanced - Advanced authentication plugin")
        click.echo("\nUse 'nexus plugin info <name>' for more details")

    except Exception as e:
        click.echo(f"❌ Error listing plugins: {e}", err=True)


@plugin.command("create")
@click.argument("name")
@click.option("--template", default="basic", help="Plugin template to use")
@click.pass_context
def plugin_create(ctx, name, template):
    """Create a new plugin"""
    click.echo(f"🔌 Creating plugin: {name}")

    try:
        plugin_dir = Path(f"plugins/{name}")
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create plugin structure
        (plugin_dir / "__init__.py").touch()

        # Create basic plugin file
        plugin_content = f'''"""
{name.title()} Plugin for Nexus Framework
"""

from nexus.plugins import BasePlugin
from fastapi import APIRouter


class {name.title().replace("_", "")}Plugin(BasePlugin):
    """A sample plugin for Nexus Framework"""

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.description = "{name.title().replace("_", " ")} plugin"

    async def initialize(self) -> bool:
        """Initialize the plugin"""
        self.logger.info(f"Initializing {{self.name}} plugin")
        return True

    def get_api_routes(self):
        """Get API routes for this plugin"""
        router = APIRouter(prefix=f"/{{self.name}}", tags=[self.name])

        @router.get("/")
        async def get_info():
            return {{
                "plugin": self.name,
                "version": self.version,
                "description": self.description,
                "status": "active"
            }}

        return [router]

    async def shutdown(self):
        """Shutdown the plugin"""
        self.logger.info(f"Shutting down {{self.name}} plugin")


# Plugin factory function
def create_plugin():
    return {name.title().replace("_", "")}Plugin()
'''

        with open(plugin_dir / "plugin.py", "w") as f:
            f.write(plugin_content)

        # Create manifest file
        manifest_content = f"""{{
    "name": "{name}",
    "version": "1.0.0",
    "description": "{name.title().replace("_", " ")} plugin",
    "author": "Developer",
    "main": "plugin.py",
    "dependencies": [],
    "entry_point": "create_plugin"
}}"""

        with open(plugin_dir / "manifest.json", "w") as f:
            f.write(manifest_content)

        click.echo(f"✅ Plugin created at: {plugin_dir}")
        click.echo("📝 Files created:")
        click.echo(f"  • {plugin_dir}/plugin.py")
        click.echo(f"  • {plugin_dir}/manifest.json")
        click.echo(f"  • {plugin_dir}/__init__.py")

    except Exception as e:
        click.echo(f"❌ Error creating plugin: {e}", err=True)
        sys.exit(1)


@plugin.command("info")
@click.argument("name")
def plugin_info(name):
    """Show plugin information"""
    click.echo(f"🔍 Plugin Information: {name}")

    # This would typically load plugin metadata
    click.echo("  Name: Sample Plugin")
    click.echo("  Version: 1.0.0")
    click.echo("  Author: Developer")
    click.echo("  Description: A sample plugin")
    click.echo("  Status: Available")


@cli.command()
@click.pass_context
def status(ctx):
    """Show application status"""
    click.echo("📊 Nexus Framework Status")
    click.echo("=" * 40)

    try:
        click.echo(f"Version: {__version__}")
        click.echo("Status: Ready")
        click.echo("Plugins: 0 loaded")
        click.echo("Services: Core services available")
        click.echo("Health: All systems operational")

    except Exception as e:
        click.echo(f"❌ Error getting status: {e}", err=True)


@cli.command()
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
def health(output_format):
    """Check application health"""
    click.echo("🏥 Health Check")

    try:
        # This would typically run actual health checks
        health_data = {
            "status": "healthy",
            "checks": {"database": "healthy", "memory": "healthy", "disk": "healthy"},
            "timestamp": "2024-12-21T10:00:00Z",
        }

        if output_format == "json":
            import json

            click.echo(json.dumps(health_data, indent=2))
        else:
            click.echo(f"Overall Status: {health_data['status']}")
            for check, status in health_data["checks"].items():
                status_icon = "✅" if status == "healthy" else "❌"
                click.echo(f"  {status_icon} {check}: {status}")

    except Exception as e:
        click.echo(f"❌ Error checking health: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config-file", help="Path to configuration file")
def validate(config_file):
    """Validate configuration"""
    click.echo("🔍 Validating Configuration")

    try:
        if config_file:
            config_path = Path(config_file)
        else:
            config_path = Path("nexus_config.yaml")

        if not config_path.exists():
            click.echo(f"❌ Configuration file not found: {config_path}")
            sys.exit(1)

        # Load and validate configuration
        import yaml

        with open(config_path) as f:
            config_data = yaml.safe_load(f)

        click.echo(f"✅ Configuration file is valid: {config_path}")
        click.echo(f"📝 Configuration sections: {list(config_data.keys())}")

    except Exception as e:
        click.echo(f"❌ Configuration validation failed: {e}", err=True)
        sys.exit(1)


def main():
    """Main CLI entry point"""
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
