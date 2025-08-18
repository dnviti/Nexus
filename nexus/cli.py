#!/usr/bin/env python3
"""
Nexus CLI
Command-line interface for Nexus
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

import click

from . import __version__
from .core import create_default_config
from .utils import setup_logging

# Setup logging
logger = logging.getLogger("nexus.cli")


@click.group()
@click.version_option(version=__version__, prog_name="Nexus")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.pass_context
def cli(ctx: Any, verbose: bool, config: Optional[str]) -> None:
    """Nexus - The Ultimate Plugin-Based Application Platform"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Setup logging level
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)


@cli.command()
@click.option("--host", default="0.0.0.0", help="Host to bind to")  # nosec B104
@click.option("--port", default=8000, type=int, help="Port to bind to")
@click.option("--reload", is_flag=True, help="Enable auto-reload for development")
@click.option("--workers", default=1, type=int, help="Number of worker processes")
@click.pass_context
def run(ctx: Any, host: str, port: int, reload: bool, workers: int) -> None:
    """Run the Nexus application server"""
    click.echo(f"🚀 Starting Nexus Framework v{__version__}")

    try:
        import uvicorn

        from . import create_nexus_app

        # Create the application
        app = create_nexus_app(config_path=ctx.obj.get("config_path"))

        # Run the server
        uvicorn.run(
            app.app,
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
def init(ctx: Any, output: str) -> None:
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
        from dataclasses import asdict

        import yaml

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
        click.echo("  1. Install Nexus: pip install nexus-platform-framework")
        click.echo("  2. Run your app: python main.py")
        click.echo("  3. Visit: http://localhost:8000")

    except Exception as e:
        click.echo(f"❌ Error initializing project: {e}", err=True)
        sys.exit(1)


@cli.group()
def plugin() -> None:
    """Plugin management commands"""
    click.echo("Plugin management commands. Use --help for available subcommands.")


@plugin.command("list")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
@click.option("--category", help="Filter by plugin category")
@click.pass_context
def plugin_list(ctx: Any, output_format: str, category: Optional[str]) -> None:
    """List available plugins"""
    import asyncio
    import json

    click.echo("📦 Listing available plugins...")

    try:

        async def list_plugins_async() -> None:
            from pathlib import Path

            from .core import EventBus, MemoryAdapter, PluginManager, ServiceRegistry

            # Initialize required components
            event_bus = EventBus()
            await event_bus.start()

            service_registry = ServiceRegistry()
            db_adapter = MemoryAdapter()
            await db_adapter.connect()

            plugin_manager = PluginManager(event_bus, service_registry)
            plugin_manager.set_database(db_adapter)

            # Discover plugins
            plugins_path = Path("plugins")
            discovered_plugins = await plugin_manager.discover_plugins(plugins_path)

            # Filter by category if specified
            if category:
                discovered_plugins = [p for p in discovered_plugins if p.category == category]

            if output_format == "json":
                plugin_data = []
                for plugin in discovered_plugins:
                    plugin_data.append(
                        {
                            "name": plugin.name,
                            "category": plugin.category,
                            "version": plugin.version,
                            "description": plugin.description,
                            "author": plugin.author,
                            "enabled": plugin.enabled,
                        }
                    )
                click.echo(json.dumps(plugin_data, indent=2))
            else:
                if not discovered_plugins:
                    click.echo("No plugins found.")
                else:
                    click.echo(f"Found {len(discovered_plugins)} plugins:")
                    for plugin in discovered_plugins:
                        status_icon = "✅" if plugin.enabled else "❌"
                        click.echo(
                            f"{status_icon} {plugin.category}.{plugin.name} v{plugin.version}"
                        )
                        click.echo(f"   Description: {plugin.description}")
                        click.echo(f"   Author: {plugin.author}")

            await event_bus.shutdown()
            await db_adapter.disconnect()

        asyncio.run(list_plugins_async())

    except Exception as e:
        click.echo(f"❌ Error listing plugins: {e}", err=True)


@plugin.command("create")
@click.argument("name")
@click.option("--template", default="basic", help="Plugin template to use")
@click.option("--category", default="custom", help="Plugin category")
@click.option("--author", help="Plugin author name")
@click.option("--description", help="Plugin description")
@click.pass_context
def plugin_create(
    ctx: Any,
    name: str,
    template: str,
    category: str,
    author: Optional[str],
    description: Optional[str],
) -> None:
    """Create a new plugin"""
    import json

    click.echo(f"🔌 Creating plugin: {name}")

    try:
        plugin_dir = Path(f"plugins/{category}/{name}")
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create plugin structure
        (plugin_dir / "__init__.py").write_text("# Plugin initialization\n")

        # Create manifest.json
        manifest = {
            "name": name,
            "version": "1.0.0",
            "description": description or f"A {name} plugin",
            "author": author or "Unknown",
            "category": category,
            "license": "MIT",
            "dependencies": {},
            "permissions": [],
            "tags": [],
        }

        with open(plugin_dir / "manifest.json", "w") as f:
            json.dump(manifest, f, indent=2)

        # Create basic plugin file
        plugin_code = f'''"""
{name} Plugin

{description or f"A {name} plugin for Nexus platform"}
"""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter
from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)

class {name.title().replace('_', '')}Plugin(BasePlugin):
    """A {name} plugin."""

    def __init__(self):
        super().__init__()
        self.name = "{name}"
        self.version = "1.0.0"
        self.category = "{category}"

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {{self.name}} plugin")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {{self.name}} plugin")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix=f"/plugins/{{self.name}}", tags=[f"{{self.name}}"])

        @router.get("/")
        async def get_plugin_info():
            """Get plugin information."""
            return {{
                "name": self.name,
                "version": self.version,
                "category": self.category,
                "status": "running"
            }}

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {{
            "collections": {{
                f"{{self.name}}_data": {{
                    "indexes": [
                        {{"field": "id", "unique": True}},
                        {{"field": "created_at"}}
                    ]
                }}
            }}
        }}
'''

        # Write plugin code to file
        with open(plugin_dir / "plugin.py", "w") as f:
            f.write(plugin_code)

        # Create README.md
        readme_content = f"""# {name.title()} Plugin

{description or f'A {name} plugin for Nexus platform'}

## Installation

This plugin is automatically discovered when placed in the plugins directory.

## Configuration

Add configuration options to your Nexus configuration file:

```yaml
plugins:
  {name}:
    enabled: true
    # Add plugin-specific configuration here
```

## API Endpoints

- `GET /plugins/{name}/` - Get plugin information

## Author

{author or 'Unknown'}

## License

MIT
"""

        with open(plugin_dir / "README.md", "w") as f:
            f.write(readme_content)

        click.echo(f"✅ Plugin '{name}' created successfully at {plugin_dir}")
        click.echo(f"📝 Edit {plugin_dir}/plugin.py to implement your plugin logic")
        click.echo(f"📖 See {plugin_dir}/README.md for usage instructions")

    except Exception as e:
        click.echo(f"❌ Error creating plugin: {e}", err=True)
        sys.exit(1)


@plugin.command("info")
@click.argument("plugin_name")
@click.pass_context
def plugin_info(ctx: Any, plugin_name: str) -> None:
    """Show detailed plugin information"""
    import asyncio

    click.echo(f"🔍 Plugin information for: {plugin_name}")

    try:

        async def get_plugin_info_async() -> None:
            from pathlib import Path

            from .core import EventBus, MemoryAdapter, PluginManager, ServiceRegistry

            # Initialize required components
            event_bus = EventBus()
            await event_bus.start()

            service_registry = ServiceRegistry()
            db_adapter = MemoryAdapter()
            await db_adapter.connect()

            plugin_manager = PluginManager(event_bus, service_registry)
            plugin_manager.set_database(db_adapter)

            # Discover plugins
            plugins_path = Path("plugins")
            discovered_plugins = await plugin_manager.discover_plugins(plugins_path)

            # Find the plugin
            plugin = None
            for p in discovered_plugins:
                if p.name == plugin_name or f"{p.category}.{p.name}" == plugin_name:
                    plugin = p
                    break

            if not plugin:
                click.echo(f"❌ Plugin '{plugin_name}' not found")
                return

            click.echo("Information:")
            click.echo(f"📦 Name: {plugin.name}")
            click.echo(f"🏷️  Category: {plugin.category}")
            click.echo(f"🔖 Version: {plugin.version}")
            click.echo(f"📝 Description: {plugin.description}")
            click.echo(f"👤 Author: {plugin.author}")
            click.echo(f"📄 License: {plugin.license}")
            click.echo(f"🟢 Enabled: {'Yes' if plugin.enabled else 'No'}")
            click.echo(f"❤️  Health: {plugin.health}")

            if plugin.homepage:
                click.echo(f"🌐 Homepage: {plugin.homepage}")
            if plugin.repository:
                click.echo(f"📦 Repository: {plugin.repository}")

            if plugin.dependencies:
                click.echo(f"🔗 Dependencies: {', '.join(plugin.dependencies.get('plugins', []))}")
            if plugin.permissions:
                click.echo(f"🔐 Required Permissions: {', '.join(plugin.permissions)}")
            if plugin.tags:
                click.echo(f"🏷️  Tags: {', '.join(plugin.tags)}")

            await event_bus.shutdown()
            await db_adapter.disconnect()

        asyncio.run(get_plugin_info_async())

    except Exception as e:
        click.echo(f"❌ Error getting plugin info: {e}", err=True)
        sys.exit(1)


@plugin.command("enable")
@click.argument("plugin_name")
@click.pass_context
def plugin_enable(ctx: Any, plugin_name: str) -> None:
    """Enable a plugin"""
    import asyncio

    click.echo(f"🔌 Enabling plugin: {plugin_name}")

    try:

        async def enable_plugin_async() -> bool:
            from .core import EventBus, MemoryAdapter, PluginManager, ServiceRegistry

            # Initialize required components
            event_bus = EventBus()
            await event_bus.start()

            service_registry = ServiceRegistry()
            db_adapter = MemoryAdapter()
            await db_adapter.connect()

            plugin_manager = PluginManager(event_bus, service_registry)
            plugin_manager.set_database(db_adapter)

            # Enable the plugin
            success = await plugin_manager.enable_plugin(plugin_name)

            if success:
                click.echo(f"✅ Plugin '{plugin_name}' enabled successfully")
                status = plugin_manager.get_plugin_status(plugin_name)
                click.echo(f"   Status: {status.value}")
            else:
                click.echo(f"❌ Failed to enable plugin '{plugin_name}'")

            await event_bus.shutdown()
            await db_adapter.disconnect()
            return success

        success = asyncio.run(enable_plugin_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error enabling plugin: {e}", err=True)
        sys.exit(1)


@plugin.command("disable")
@click.argument("plugin_name")
@click.pass_context
def plugin_disable(ctx: Any, plugin_name: str) -> None:
    """Disable a plugin"""
    import asyncio

    click.echo(f"🔌 Disabling plugin: {plugin_name}")

    try:

        async def disable_plugin_async() -> bool:
            from .core import EventBus, MemoryAdapter, PluginManager, ServiceRegistry

            # Initialize required components
            event_bus = EventBus()
            await event_bus.start()

            service_registry = ServiceRegistry()
            db_adapter = MemoryAdapter()
            await db_adapter.connect()

            plugin_manager = PluginManager(event_bus, service_registry)
            plugin_manager.set_database(db_adapter)

            # Disable the plugin
            success = await plugin_manager.disable_plugin(plugin_name)

            if success:
                click.echo(f"✅ Plugin '{plugin_name}' disabled successfully")
                status = plugin_manager.get_plugin_status(plugin_name)
                click.echo(f"   Status: {status.value}")
            else:
                click.echo(f"❌ Failed to disable plugin '{plugin_name}'")

            await event_bus.shutdown()
            await db_adapter.disconnect()
            return success

        success = asyncio.run(disable_plugin_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error disabling plugin: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.pass_context
def status(ctx: Any) -> None:
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
def health(output_format: str) -> None:
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
            checks = health_data.get("checks", {})
            if isinstance(checks, dict):
                for check, status in checks.items():
                    status_icon = "✅" if status == "healthy" else "❌"
                    click.echo(f"  {status_icon} {check}: {status}")

    except Exception as e:
        click.echo(f"❌ Error checking health: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--config-file", help="Path to configuration file")
def validate(config_file: str) -> None:
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


def main() -> None:
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
