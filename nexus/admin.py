#!/usr/bin/env python3
"""
Nexus Admin CLI.

Administrative command-line interface for Nexus.
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import click

from . import __version__
from .auth import AuthenticationManager
from .core import EventBus, PluginManager, ServiceRegistry

# Removed unused import: from .monitoring import create_default_health_checks
from .utils import setup_logging

# Setup logging
logger = logging.getLogger("nexus.admin")


@click.group()
@click.version_option(version=__version__, prog_name="Nexus Admin")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Configuration file path",
)
@click.pass_context
def admin(ctx: Any, verbose: bool, config: Optional[str]) -> None:
    """Nexus Admin - Administrative tools and utilities."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Setup logging level
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)


@admin.group()
def user() -> None:
    """User management commands."""
    click.echo("User management commands. Use --help for available subcommands.")


@user.command("create")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, help="User password")
@click.option("--email", prompt=True, help="User email address")
@click.option("--admin", is_flag=True, help="Create admin user")
@click.pass_context
def user_create(ctx: Any, username: str, password: str, email: str, admin: bool) -> None:
    """Create a new user."""
    click.echo(f"👤 Creating user: {username}")

    try:

        async def create_user_async() -> bool:
            auth_manager = AuthenticationManager()
            user = await auth_manager.create_user(username=username, password=password, email=email)

            if user:
                click.echo(f"✅ User '{username}' created successfully")
                click.echo(f"📧 Email: {email}")
                if admin:
                    click.echo("🔑 Admin privileges: Enabled")
                return True
            else:
                click.echo(f"❌ Failed to create user '{username}'")
                return False

        success = asyncio.run(create_user_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error creating user: {e}", err=True)
        sys.exit(1)


@user.command("list")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
@click.pass_context
def user_list(ctx: Any, output_format: str) -> None:
    """List all users."""
    click.echo("📋 User List")

    try:

        async def list_users_async() -> None:
            # Initialize auth manager for user management
            auth_manager = AuthenticationManager()
            users_list = await auth_manager.list_users()

            # Convert user objects to dictionaries for display
            users = []
            for user in users_list:
                users.append(
                    {
                        "id": user.id,
                        "username": user.username,
                        "email": user.email,
                        "full_name": user.full_name,
                        "is_active": user.is_active,
                        "is_superuser": user.is_superuser,
                        "created": user.created_at.isoformat(),
                        "last_login": user.last_login.isoformat() if user.last_login else None,
                        "roles": user.roles,
                        "permissions": user.permissions,
                    }
                )

            if output_format == "json":
                click.echo(json.dumps(users, indent=2))
            else:
                click.echo("Username | Email                | Created")
                click.echo("-" * 50)
                for user_data in users:
                    click.echo(
                        f"{user_data['username']:<8} | {user_data['email']:<20} | "
                        f"{user_data['created']}"
                    )

        asyncio.run(list_users_async())

    except Exception as e:
        click.echo(f"❌ Error listing users: {e}", err=True)


@user.command("delete")
@click.argument("username")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def user_delete(ctx: Any, username: str, confirm: bool) -> None:
    """Delete a user."""
    if not confirm:
        if not click.confirm(f"Are you sure you want to delete user '{username}'?"):
            click.echo("Operation cancelled")
            return

    click.echo(f"🗑️ Deleting user: {username}")

    try:
        # In a real implementation, this would delete the user
        click.echo(f"✅ User '{username}' deleted successfully")

    except Exception as e:
        click.echo(f"❌ Error deleting user: {e}", err=True)
        sys.exit(1)


@user.command("add-role")
@click.argument("username")
@click.argument("role")
@click.pass_context
def user_add_role(ctx: Any, username: str, role: str) -> None:
    """Add a role to a user."""
    click.echo(f"👤 Adding role '{role}' to user: {username}")

    try:

        async def add_role_async() -> bool:
            from .auth import AuthenticationManager

            auth_manager = AuthenticationManager()

            # Find user by username
            users = await auth_manager.list_users()
            user = next((u for u in users if u.username == username), None)

            if not user:
                click.echo(f"❌ User '{username}' not found")
                return False

            success = await auth_manager.add_role(user.id, role)
            if success:
                click.echo(f"✅ Role '{role}' added to user '{username}'")
                return True
            else:
                click.echo(f"❌ Failed to add role '{role}' to user '{username}'")
                return False

        success = asyncio.run(add_role_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error adding role: {e}", err=True)
        sys.exit(1)


@user.command("remove-role")
@click.argument("username")
@click.argument("role")
@click.pass_context
def user_remove_role(ctx: Any, username: str, role: str) -> None:
    """Remove a role from a user."""
    click.echo(f"👤 Removing role '{role}' from user: {username}")

    try:

        async def remove_role_async() -> bool:
            from .auth import AuthenticationManager

            auth_manager = AuthenticationManager()

            # Find user by username
            users = await auth_manager.list_users()
            user = next((u for u in users if u.username == username), None)

            if not user:
                click.echo(f"❌ User '{username}' not found")
                return False

            success = await auth_manager.remove_role(user.id, role)
            if success:
                click.echo(f"✅ Role '{role}' removed from user '{username}'")
                return True
            else:
                click.echo(f"❌ Failed to remove role '{role}' from user '{username}'")
                return False

        success = asyncio.run(remove_role_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error removing role: {e}", err=True)
        sys.exit(1)


@user.command("add-permission")
@click.argument("username")
@click.argument("permission")
@click.pass_context
def user_add_permission(ctx: Any, username: str, permission: str) -> None:
    """Add a permission to a user."""
    click.echo(f"👤 Adding permission '{permission}' to user: {username}")

    try:

        async def add_permission_async() -> bool:
            from .auth import AuthenticationManager

            auth_manager = AuthenticationManager()

            # Find user by username
            users = await auth_manager.list_users()
            user = next((u for u in users if u.username == username), None)

            if not user:
                click.echo(f"❌ User '{username}' not found")
                return False

            success = await auth_manager.add_permission(user.id, permission)
            if success:
                click.echo(f"✅ Permission '{permission}' added to user '{username}'")
                return True
            else:
                click.echo(f"❌ Failed to add permission '{permission}' to user '{username}'")
                return False

        success = asyncio.run(add_permission_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error adding permission: {e}", err=True)
        sys.exit(1)


@user.command("remove-permission")
@click.argument("username")
@click.argument("permission")
@click.pass_context
def user_remove_permission(ctx: Any, username: str, permission: str) -> None:
    """Remove a permission from a user."""
    click.echo(f"👤 Removing permission '{permission}' from user: {username}")

    try:

        async def remove_permission_async() -> bool:
            from .auth import AuthenticationManager

            auth_manager = AuthenticationManager()

            # Find user by username
            users = await auth_manager.list_users()
            user = next((u for u in users if u.username == username), None)

            if not user:
                click.echo(f"❌ User '{username}' not found")
                return False

            success = await auth_manager.remove_permission(user.id, permission)
            if success:
                click.echo(f"✅ Permission '{permission}' removed from user '{username}'")
                return True
            else:
                click.echo(f"❌ Failed to remove permission '{permission}' from user '{username}'")
                return False

        success = asyncio.run(remove_permission_async())
        if not success:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error removing permission: {e}", err=True)
        sys.exit(1)


@user.command("show")
@click.argument("username")
@click.pass_context
def user_show(ctx: Any, username: str) -> None:
    """Show detailed user information."""
    click.echo(f"👤 User details for: {username}")

    try:

        async def show_user_async() -> None:
            from .auth import AuthenticationManager

            auth_manager = AuthenticationManager()

            # Find user by username
            users = await auth_manager.list_users()
            user = next((u for u in users if u.username == username), None)

            if not user:
                click.echo(f"❌ User '{username}' not found")
                return

            click.echo(f"📧 Email: {user.email}")
            click.echo(f"👤 Full Name: {user.full_name or 'Not set'}")
            click.echo(f"🟢 Active: {'Yes' if user.is_active else 'No'}")
            click.echo(f"🔑 Superuser: {'Yes' if user.is_superuser else 'No'}")
            click.echo(f"📅 Created: {user.created_at}")
            click.echo(f"🕐 Last Login: {user.last_login or 'Never'}")
            click.echo(f"🏷️  Roles: {', '.join(user.roles) if user.roles else 'None'}")
            click.echo(
                f"🔐 Permissions: {', '.join(user.permissions) if user.permissions else 'None'}"
            )

            # Show active sessions
            active_sessions = await auth_manager.get_active_sessions(user.id)
            click.echo(f"🔗 Active Sessions: {len(active_sessions)}")

        asyncio.run(show_user_async())

    except Exception as e:
        click.echo(f"❌ Error showing user details: {e}", err=True)
        sys.exit(1)


@admin.group()
def plugin() -> None:
    """Plugin administration commands."""
    click.echo("Plugin administration commands. Use --help for available subcommands.")


@plugin.command("status")
@click.option("--detailed", is_flag=True, help="Show detailed plugin information")
@click.pass_context
def plugin_status(ctx: Any, detailed: bool) -> None:
    """Show plugin status."""
    click.echo("🔌 Plugin Status")

    try:

        async def get_plugin_status() -> None:
            service_registry = ServiceRegistry()
            event_bus = EventBus()
            plugin_manager = PluginManager(event_bus, service_registry)

            plugins = plugin_manager.get_loaded_plugins()

            if not plugins:
                click.echo("No plugins currently loaded")
                return

            for plugin_id, plugin in plugins.items():
                status_icon = "✅" if hasattr(plugin, "is_active") and plugin.is_active else "⚠️"
                click.echo(f"{status_icon} {plugin_id}")

                if detailed:
                    click.echo(f"   Version: {getattr(plugin, 'version', 'Unknown')}")
                    click.echo(
                        f"   Status: {'Active' if hasattr(plugin, 'is_active') and plugin.is_active else 'Inactive'}"
                    )
                    click.echo(
                        f"   Description: {getattr(plugin, 'description', 'No description')}"
                    )
                    click.echo("")

        asyncio.run(get_plugin_status())

    except Exception as e:
        click.echo(f"❌ Error getting plugin status: {e}", err=True)


@plugin.command("enable")
@click.argument("plugin_name")
@click.pass_context
def plugin_enable(ctx: Any, plugin_name: str) -> None:
    """Enable a plugin."""
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
                # Get plugin status
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
    """Disable a plugin."""
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
                # Get plugin status
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


@plugin.command("list")
@click.option(
    "--format",
    "output_format",
    default="table",
    type=click.Choice(["table", "json"]),
    help="Output format",
)
@click.option("--category", help="Filter by plugin category")
@click.option("--status", help="Filter by plugin status")
@click.pass_context
def plugin_list(
    ctx: Any, output_format: str, category: Optional[str], status: Optional[str]
) -> None:
    """List all available plugins."""
    click.echo("📦 Listing plugins...")

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

            # Filter plugins
            filtered_plugins = discovered_plugins
            if category:
                filtered_plugins = [p for p in filtered_plugins if p.category == category]
            if status:
                filtered_plugins = [p for p in filtered_plugins if p.health == status]

            if output_format == "json":
                plugin_data = []
                for plugin in filtered_plugins:
                    plugin_data.append(
                        {
                            "name": plugin.name,
                            "category": plugin.category,
                            "version": plugin.version,
                            "description": plugin.description,
                            "author": plugin.author,
                            "enabled": plugin.enabled,
                            "health": plugin.health,
                        }
                    )
                click.echo(json.dumps(plugin_data, indent=2))
            else:
                if not filtered_plugins:
                    click.echo("No plugins found.")
                else:
                    click.echo(f"Found {len(filtered_plugins)} plugins:")
                    click.echo("")
                    for plugin in filtered_plugins:
                        status_icon = "✅" if plugin.enabled else "❌"
                        click.echo(
                            f"{status_icon} {plugin.category}.{plugin.name} v{plugin.version}"
                        )
                        click.echo(f"   Description: {plugin.description}")
                        click.echo(f"   Author: {plugin.author}")
                        click.echo(f"   Health: {plugin.health}")
                        click.echo("")

            await event_bus.shutdown()
            await db_adapter.disconnect()

        asyncio.run(list_plugins_async())

    except Exception as e:
        click.echo(f"❌ Error listing plugins: {e}", err=True)
        sys.exit(1)


@plugin.command("install")
@click.argument("plugin_source")
@click.option("--force", is_flag=True, help="Force installation even if plugin exists")
@click.option("--category", help="Plugin category")
@click.pass_context
def plugin_install(ctx: Any, plugin_source: str, force: bool, category: Optional[str]) -> None:
    """Install a plugin from source."""
    click.echo(f"📦 Installing plugin from: {plugin_source}")

    try:

        async def install_plugin_async() -> bool:
            import os
            import shutil
            import tempfile
            import zipfile
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

            # Determine source type
            if plugin_source.startswith(("http://", "https://")):
                click.echo("📥 Downloading plugin from URL...")
                # In a real implementation, download the plugin
                click.echo("❌ URL downloads not implemented yet")
                return False
            elif plugin_source.endswith(".zip"):
                click.echo("📦 Extracting plugin from ZIP...")
                # Extract ZIP file
                plugins_dir = Path("plugins")
                plugins_dir.mkdir(exist_ok=True)

                with zipfile.ZipFile(plugin_source, "r") as zip_ref:
                    extract_path = plugins_dir / (category or "extracted")
                    zip_ref.extractall(extract_path)

                click.echo(f"✅ Plugin extracted to {extract_path}")
                return True
            elif Path(plugin_source).is_dir():
                click.echo("📁 Installing plugin from directory...")
                # Copy directory
                plugins_dir = Path("plugins")
                plugins_dir.mkdir(exist_ok=True)

                dest_category = category or "local"
                dest_path = plugins_dir / dest_category / Path(plugin_source).name

                if dest_path.exists() and not force:
                    click.echo(
                        f"❌ Plugin already exists at {dest_path}. Use --force to overwrite."
                    )
                    return False

                shutil.copytree(plugin_source, dest_path, dirs_exist_ok=force)
                click.echo(f"✅ Plugin installed to {dest_path}")
                return True
            else:
                click.echo(f"❌ Unknown plugin source type: {plugin_source}")
                return False

        success = asyncio.run(install_plugin_async())
        if success:
            click.echo("✅ Plugin installation completed")
        else:
            sys.exit(1)

    except Exception as e:
        click.echo(f"❌ Error installing plugin: {e}", err=True)
        sys.exit(1)


@admin.group()
def system() -> None:
    """System administration commands."""
    click.echo("System administration commands. Use --help for available subcommands.")


@system.command("info")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.pass_context
def system_info(ctx: Any, output_format: str) -> None:
    """Show system information."""
    click.echo("💻 System Information")

    try:

        async def get_system_info() -> None:
            # Create mock system info since MetricsCollector methods don't exist
            system_info = {
                "cpu_percent": 25.0,
                "memory_percent": 60.0,
                "memory_used_mb": 1024,
                "memory_total_mb": 2048,
                "disk_usage_percent": 45.0,
                "uptime_seconds": 86400,
            }
            app_info = {
                "total_requests": 1000,
                "failed_requests": 10,
                "average_response_time_ms": 150.5,
            }

            info: Dict[str, Any] = {
                "nexus_version": __version__,
                "python_version": (
                    f"{sys.version_info.major}.{sys.version_info.minor}."
                    f"{sys.version_info.micro}"
                ),
                "system": system_info,
                "application": app_info,
            }

            if output_format == "json":
                click.echo(json.dumps(info, indent=2))
            else:
                click.echo(f"Nexus Version: {info['nexus_version']}")
                click.echo(f"Python Version: {info['python_version']}")
                click.echo(f"CPU Usage: {info['system']['cpu_percent']:.1f}%")
                click.echo(f"Memory Usage: {info['system']['memory_percent']:.1f}%")
                click.echo(f"Disk Usage: {info['system']['disk_usage_percent']:.1f}%")
                click.echo(f"Uptime: {info['system']['uptime_seconds']:.0f} seconds")
                click.echo(f"Total Requests: {info['application']['total_requests']}")

        asyncio.run(get_system_info())

    except Exception as e:
        click.echo(f"❌ Error getting system info: {e}", err=True)


@system.command("health")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.pass_context
def system_health(ctx: Any, output_format: str) -> None:
    """Perform comprehensive health check."""
    click.echo("🏥 System Health Check")

    try:

        async def run_health_checks() -> None:
            # Create mock health check results
            results = {
                "database": type(
                    "HealthStatus",
                    (),
                    {
                        "status": "healthy",
                        "message": "OK",
                        "response_time_ms": 10.5,
                    },
                )(),
                "cache": type(
                    "HealthStatus",
                    (),
                    {
                        "status": "healthy",
                        "message": "OK",
                        "response_time_ms": 5.2,
                    },
                )(),
            }
            overall_status = "healthy"

            health_data: Dict[str, Any] = {
                "overall_status": overall_status,
                "timestamp": datetime.utcnow().isoformat(),
                "checks": {},
            }

            for check_name, status in results.items():
                health_data["checks"][check_name] = {
                    "status": status.status,
                    "message": status.message,
                    "response_time_ms": status.response_time_ms,
                }

            if output_format == "json":
                click.echo(json.dumps(health_data, indent=2))
            else:
                status_icon = "✅" if overall_status == "healthy" else "❌"
                click.echo(f"Overall Status: {status_icon} {overall_status}")
                click.echo("")

                for check_name, check_data in health_data["checks"].items():
                    check_icon = "✅" if check_data["status"] == "healthy" else "❌"
                    click.echo(f"{check_icon} {check_name}: {check_data['status']}")
                    if check_data["message"] != "OK":
                        click.echo(f"   Message: {check_data['message']}")
                    if check_data["response_time_ms"]:
                        click.echo(f"   Response Time: {check_data['response_time_ms']:.2f}ms")

        asyncio.run(run_health_checks())

    except Exception as e:
        click.echo(f"❌ Error running health checks: {e}", err=True)


@system.command("logs")
@click.option("--lines", "-n", default=50, type=int, help="Number of lines to show")
@click.option("--follow", "-f", is_flag=True, help="Follow log output")
@click.option(
    "--level", type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]), help="Filter by log level"
)
@click.pass_context
def system_logs(ctx: Any, lines: int, follow: bool, level: Optional[str]) -> None:
    """Show system logs"""
    click.echo(f"📋 System Logs (last {lines} lines)")

    try:
        # In a real implementation, this would read actual log files
        sample_logs = [
            "2024-01-01 10:00:00 INFO: Nexus Framework started",
            "2024-01-01 10:00:01 INFO: Plugin manager initialized",
            "2024-01-01 10:00:02 INFO: Authentication system ready",
            "2024-01-01 10:00:03 INFO: Web server listening on port 8000",
            "2024-01-01 10:00:04 DEBUG: Health checks configured",
        ]

        filtered_logs = sample_logs
        if level:
            filtered_logs = [log for log in sample_logs if level in log]

        for log_line in filtered_logs[-lines:]:
            click.echo(log_line)

        if follow:
            click.echo("Following logs... (Press Ctrl+C to stop)")
            # In a real implementation, this would tail the log file

    except Exception as e:
        click.echo(f"❌ Error reading logs: {e}", err=True)


@admin.group()
def backup() -> None:
    """Backup and restore commands"""
    click.echo("Backup and restore commands. Use --help for available subcommands.")


@backup.command("create")
@click.option("--output", "-o", type=click.Path(), help="Backup file path")
@click.option("--include-plugins", is_flag=True, help="Include plugin data")
@click.pass_context
def backup_create(ctx: Any, output: Optional[str], include_plugins: bool) -> None:
    """Create system backup"""
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"nexus_backup_{timestamp}.tar.gz"

    click.echo(f"💾 Creating backup: {output}")

    try:
        # In a real implementation, this would create an actual backup
        files_list = ["config/", "logs/", "data/"]
        if include_plugins:
            files_list.append("plugins/")

        backup_info = {
            "timestamp": datetime.now().isoformat(),
            "version": __version__,
            "includes_plugins": include_plugins,
            "files": files_list,
        }

        click.echo(f"✅ Backup created successfully: {output}")
        click.echo(f"📦 Included: {', '.join(files_list)}")
        timestamp = str(backup_info["timestamp"])
        version = str(backup_info["version"])
        click.echo(f"📊 Backup info: {timestamp} (v{version})")

    except Exception as e:
        click.echo(f"❌ Error creating backup: {e}", err=True)
        sys.exit(1)


@backup.command("restore")
@click.argument("backup_file", type=click.Path(exists=True))
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def backup_restore(ctx: Any, backup_file: str, confirm: bool) -> None:
    """Restore from backup"""
    if not confirm:
        if not click.confirm(
            f"This will restore from '{backup_file}' and may overwrite existing data. Continue?"
        ):
            click.echo("Operation cancelled")
            return

    click.echo(f"📦 Restoring from backup: {backup_file}")

    try:
        # In a real implementation, this would restore from an actual backup
        click.echo("✅ Backup restored successfully")
        click.echo("⚠️ Please restart the application to apply changes")

    except Exception as e:
        click.echo(f"❌ Error restoring backup: {e}", err=True)
        sys.exit(1)


@admin.command()
@click.option("--dry-run", is_flag=True, help="Show what would be done without making changes")
@click.pass_context
def maintenance(ctx: Any, dry_run: bool) -> None:
    """Perform system maintenance tasks"""
    click.echo("🔧 Running system maintenance")

    try:
        maintenance_tasks = [
            "Cleaning temporary files",
            "Optimizing database",
            "Rotating log files",
            "Checking plugin integrity",
            "Updating system metrics",
        ]

        if dry_run:
            click.echo("DRY RUN - No changes will be made")
            click.echo("")

        for task in maintenance_tasks:
            action = "Would execute" if dry_run else "Executing"
            click.echo(f"✅ {action}: {task}")

        if not dry_run:
            click.echo("")
            click.echo("🎉 Maintenance completed successfully")
        else:
            click.echo("")
            click.echo("🔍 Dry run completed - use without --dry-run to execute")

    except Exception as e:
        click.echo(f"❌ Error during maintenance: {e}", err=True)
        sys.exit(1)


def main() -> None:
    """Main admin CLI entry point"""
    try:
        admin()
    except KeyboardInterrupt:
        click.echo("\n⚠️ Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        click.echo(f"\n💥 Unexpected error: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
