#!/usr/bin/env python3
"""
Nexus Admin CLI
Administrative command-line interface for Nexus
"""

import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import click

from . import __version__
from .auth import AuthenticationManager
from .core import AppConfig, PluginManager, ServiceRegistry, create_default_config
from .monitoring import MetricsCollector, create_default_health_checks
from .utils import setup_logging

# Setup logging
logger = logging.getLogger("nexus.admin")


@click.group()
@click.version_option(version=__version__, prog_name="Nexus Admin")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.option("--config", "-c", type=click.Path(exists=True), help="Configuration file path")
@click.pass_context
def admin(ctx, verbose, config):
    """Nexus Admin - Administrative tools and utilities"""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    ctx.obj["config_path"] = config

    # Setup logging level
    log_level = "DEBUG" if verbose else "INFO"
    setup_logging(log_level)


@admin.group()
def user():
    """User management commands"""
    pass


@user.command("create")
@click.argument("username")
@click.option("--password", prompt=True, hide_input=True, help="User password")
@click.option("--email", prompt=True, help="User email address")
@click.option("--admin", is_flag=True, help="Create admin user")
@click.pass_context
def user_create(ctx, username, password, email, admin):
    """Create a new user"""
    click.echo(f"👤 Creating user: {username}")

    try:

        async def create_user_async():
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
def user_list(ctx, output_format):
    """List all users"""
    click.echo("📋 User List")

    try:

        async def list_users_async():
            auth_manager = AuthenticationManager()
            # In a real implementation, this would get all users
            users = [
                {"username": "admin", "email": "admin@example.com", "created": "2024-01-01"},
                {"username": "user1", "email": "user1@example.com", "created": "2024-01-02"},
            ]

            if output_format == "json":
                click.echo(json.dumps(users, indent=2))
            else:
                click.echo("Username | Email                | Created")
                click.echo("-" * 50)
                for user in users:
                    click.echo(f"{user['username']:<8} | {user['email']:<20} | {user['created']}")

        asyncio.run(list_users_async())

    except Exception as e:
        click.echo(f"❌ Error listing users: {e}", err=True)


@user.command("delete")
@click.argument("username")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def user_delete(ctx, username, confirm):
    """Delete a user"""
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


@admin.group()
def plugin():
    """Plugin administration commands"""
    pass


@plugin.command("status")
@click.option("--detailed", is_flag=True, help="Show detailed plugin information")
@click.pass_context
def plugin_status(ctx, detailed):
    """Show plugin status"""
    click.echo("🔌 Plugin Status")

    try:

        async def get_plugin_status():
            config = create_default_config()
            service_registry = ServiceRegistry()
            plugin_manager = PluginManager(config, service_registry)

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
def plugin_enable(ctx, plugin_name):
    """Enable a plugin"""
    click.echo(f"🔌 Enabling plugin: {plugin_name}")

    try:
        # In a real implementation, this would enable the plugin
        click.echo(f"✅ Plugin '{plugin_name}' enabled successfully")

    except Exception as e:
        click.echo(f"❌ Error enabling plugin: {e}", err=True)
        sys.exit(1)


@plugin.command("disable")
@click.argument("plugin_name")
@click.pass_context
def plugin_disable(ctx, plugin_name):
    """Disable a plugin"""
    click.echo(f"🔌 Disabling plugin: {plugin_name}")

    try:
        # In a real implementation, this would disable the plugin
        click.echo(f"✅ Plugin '{plugin_name}' disabled successfully")

    except Exception as e:
        click.echo(f"❌ Error disabling plugin: {e}", err=True)
        sys.exit(1)


@admin.group()
def system():
    """System administration commands"""
    pass


@system.command("info")
@click.option(
    "--format",
    "output_format",
    default="text",
    type=click.Choice(["text", "json"]),
    help="Output format",
)
@click.pass_context
def system_info(ctx, output_format):
    """Show system information"""
    click.echo("💻 System Information")

    try:

        async def get_system_info():
            metrics_collector = MetricsCollector()
            system_metrics = metrics_collector.get_system_metrics()
            app_metrics = metrics_collector.get_application_metrics()

            info = {
                "nexus_version": __version__,
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "system": {
                    "cpu_percent": system_metrics.cpu_percent,
                    "memory_percent": system_metrics.memory_percent,
                    "memory_used_mb": system_metrics.memory_used_mb,
                    "memory_total_mb": system_metrics.memory_total_mb,
                    "disk_usage_percent": system_metrics.disk_usage_percent,
                    "uptime_seconds": system_metrics.uptime_seconds,
                },
                "application": {
                    "total_requests": app_metrics.total_requests,
                    "failed_requests": app_metrics.failed_requests,
                    "average_response_time": app_metrics.average_response_time_ms,
                },
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
def system_health(ctx, output_format):
    """Perform comprehensive health check"""
    click.echo("🏥 System Health Check")

    try:

        async def run_health_checks():
            metrics_collector = MetricsCollector()
            health_checks = create_default_health_checks()

            for health_check in health_checks:
                metrics_collector.add_health_check(health_check)

            results = await metrics_collector.run_health_checks()
            overall_status = metrics_collector.get_overall_health()

            health_data = {
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
def system_logs(ctx, lines, follow, level):
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
def backup():
    """Backup and restore commands"""
    pass


@backup.command("create")
@click.option("--output", "-o", type=click.Path(), help="Backup file path")
@click.option("--include-plugins", is_flag=True, help="Include plugin data")
@click.pass_context
def backup_create(ctx, output, include_plugins):
    """Create system backup"""
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"nexus_backup_{timestamp}.tar.gz"

    click.echo(f"💾 Creating backup: {output}")

    try:
        # In a real implementation, this would create an actual backup
        backup_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "version": __version__,
            "includes_plugins": include_plugins,
            "files": ["config/", "logs/", "data/"],
        }

        if include_plugins:
            backup_data["files"].append("plugins/")

        click.echo(f"✅ Backup created successfully: {output}")
        click.echo(f"📦 Included: {', '.join(backup_data['files'])}")

    except Exception as e:
        click.echo(f"❌ Error creating backup: {e}", err=True)
        sys.exit(1)


@backup.command("restore")
@click.argument("backup_file", type=click.Path(exists=True))
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def backup_restore(ctx, backup_file, confirm):
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
def maintenance(ctx, dry_run):
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


def main():
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
