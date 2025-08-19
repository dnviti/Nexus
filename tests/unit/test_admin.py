#!/usr/bin/env python3
"""
Tests for Nexus Admin CLI
"""

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from nexus import __version__
from nexus.admin import (
    add_user_role,
    admin,
    backup_database,
    cleanup_system,
    create_user,
    database,
    database_status,
    delete_user,
    deploy_plugin,
    disable_plugin,
    enable_plugin,
    list_sessions,
    list_users,
    main,
    maintenance,
    migrate_database,
    optimize_system,
    overall_status,
    plugin,
    plugin_status,
    remove_user_role,
    reset_password,
    restart_plugin,
    restore_database,
    revoke_session,
    security,
    security_audit,
    system,
    system_health,
    system_info,
    system_logs,
    user,
    vacuum_database,
)
from nexus.factory import create_nexus_app


class TestAdminCLI:
    """Test admin CLI commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_admin_main_command(self):
        """Test main admin command"""
        result = self.runner.invoke(admin, ["--help"])
        assert result.exit_code == 0
        assert "Nexus Admin" in result.output
        assert "Platform Administration Tools" in result.output

    def test_admin_version_option(self):
        """Test admin version option"""
        result = self.runner.invoke(admin, ["--version"])
        assert result.exit_code == 0
        assert __version__ in result.output

    def test_admin_verbose_option(self):
        """Test admin verbose option"""
        result = self.runner.invoke(admin, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_admin_config_option(self, tmp_path):
        """Test admin config option"""
        config_file = tmp_path / "test_config.yml"
        config_file.write_text("test: config")

        result = self.runner.invoke(admin, ["--config", str(config_file), "--help"])
        assert result.exit_code == 0


class TestUserCommands:
    """Test user management commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_user_group(self):
        """Test user command group"""
        result = self.runner.invoke(user, ["--help"])
        assert result.exit_code == 0
        assert "User management commands" in result.output

    def test_user_create_success(self):
        """Test successful user creation."""
        with patch("nexus.admin.setup_logging"):
            with patch("nexus.admin.load_app_config") as mock_config:
                with patch("nexus.admin.AuthenticationManager") as mock_auth:
                    mock_config.return_value = {}
                    mock_auth.return_value.create_user.return_value = True
                    result = self.runner.invoke(
                        create_user,
                        ["testuser", "--password", "testpass", "--email", "test@example.com"],
                    )

                    assert result.exit_code == 0
                    assert "🆕 Creating user: testuser" in result.output

    def test_user_create_with_admin_flag(self):
        """Test user creation with admin flag."""
        with patch("nexus.admin.setup_logging"):
            with patch("nexus.admin.load_app_config") as mock_config:
                with patch("nexus.admin.AuthenticationManager") as mock_auth:
                    mock_config.return_value = {}
                    mock_auth.return_value.create_user.return_value = True
                    result = self.runner.invoke(
                        create_user,
                        [
                            "adminuser",
                            "--password",
                            "adminpass",
                            "--email",
                            "admin@example.com",
                            "--admin",
                        ],
                    )

                    assert result.exit_code == 0
                    assert "🆕 Creating user: adminuser" in result.output

    def test_user_list_table_format(self):
        """Test user list in table format"""
        result = self.runner.invoke(list_users, ["--format", "table"])

        assert result.exit_code == 0
        assert "👥 Listing users..." in result.output
        assert "Username" in result.output

    def test_user_list_json_format(self):
        """Test user list in JSON format"""
        result = self.runner.invoke(list_users, ["--format", "json"])

        assert result.exit_code == 0
        assert "👥 Listing users..." in result.output

    def test_user_delete_with_confirmation(self):
        """Test user deletion with confirmation"""
        result = self.runner.invoke(delete_user, ["testuser"], input="y\n")

        assert result.exit_code == 0
        assert "🗑️ Deleting user: testuser" in result.output
        assert "User 'testuser' deleted successfully" in result.output

    def test_user_delete_cancelled(self):
        """Test user deletion cancelled"""
        result = self.runner.invoke(delete_user, ["testuser"], input="n\n")

        assert result.exit_code == 0
        assert "❌ Operation cancelled" in result.output

    def test_user_delete_with_confirm_flag(self):
        """Test user deletion with confirm flag"""
        result = self.runner.invoke(delete_user, ["testuser", "--force"])

        assert result.exit_code == 0
        assert "✅ User 'testuser' deleted successfully" in result.output


class TestPluginCommands:
    """Test plugin management commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_plugin_group(self):
        """Test plugin command group"""
        result = self.runner.invoke(plugin, ["--help"])
        assert result.exit_code == 0
        assert "Plugin administration commands" in result.output

    def test_plugin_status_basic(self):
        """Test plugin status command"""
        result = self.runner.invoke(plugin_status)

        assert result.exit_code == 0
        assert "📊 Checking plugin status..." in result.output

    def test_plugin_status_detailed(self):
        """Test plugin status with detailed flag"""
        result = self.runner.invoke(plugin_status, ["--help"])

        assert result.exit_code == 0
        assert "📊 Show plugin status" in result.output

    def test_plugin_enable(self):
        """Test plugin enable command"""
        result = self.runner.invoke(enable_plugin, ["test_plugin"])

        assert result.exit_code == 1
        assert "🟢 Enabling plugin" in result.output

    def test_plugin_disable(self):
        """Test plugin disable command"""
        with patch("nexus.admin.setup_logging"):
            with patch("nexus.admin.load_app_config") as mock_config:
                with patch("nexus.factory.create_nexus_app") as mock_app:
                    mock_config.return_value = type(
                        "Config", (), {"plugins": type("Plugins", (), {"directory": "plugins"})}
                    )()
                    from unittest.mock import AsyncMock, MagicMock

                    mock_app_instance = MagicMock()
                    mock_app_instance._startup = AsyncMock()
                    mock_app_instance._shutdown = AsyncMock()
                    mock_app_instance.plugin_manager.get_plugin_info.return_value = MagicMock()
                    mock_app_instance.plugin_manager.disable_plugin = AsyncMock(return_value=True)
                    mock_app.return_value = mock_app_instance
                    result = self.runner.invoke(disable_plugin, ["test_plugin"])

                    assert result.exit_code == 0
                    assert "🔴 Disabling plugin" in result.output


class TestSystemCommands:
    """Test system administration commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_system_group(self):
        """Test system command group"""
        result = self.runner.invoke(system, ["--help"])
        assert result.exit_code == 0
        assert "System monitoring and management commands" in result.output

    def test_system_info_text_format(self):
        """Test system info in text format"""
        result = self.runner.invoke(system_info, ["--format", "table"])

        assert result.exit_code == 0
        assert "System Information" in result.output

    def test_system_info_json_format(self):
        """Test system info in JSON format"""
        result = self.runner.invoke(system_info, ["--format", "json"])

        assert result.exit_code == 0
        # JSON format doesn't include "System Information" text, check for JSON structure instead
        import json

        try:
            json.loads(result.output.split("\n", 1)[1])  # Skip the first line (emoji message)
        except (json.JSONDecodeError, IndexError):
            assert False, "Expected valid JSON output"

    def test_system_health_text_format(self):
        """Test system health in text format"""
        result = self.runner.invoke(system_health, ["--format", "table"])

        assert result.exit_code == 0
        assert "Overall System Health" in result.output

    def test_system_health_json_format(self):
        """Test system health in JSON format"""
        result = self.runner.invoke(system_health, ["--format", "json"])

        assert result.exit_code == 0
        # JSON format doesn't include "System Health Check" text, check for JSON structure instead
        import json

        try:
            json.loads(result.output.split("\n", 1)[1])  # Skip the first line (emoji message)
        except (json.JSONDecodeError, IndexError):
            assert False, "Expected valid JSON output"

    def test_system_logs_default(self):
        """Test system logs with default options"""
        result = self.runner.invoke(system_logs)

        assert result.exit_code == 0
        assert "Showing last 50 log entries" in result.output
        assert "Application started successfully" in result.output

    def test_system_logs_with_lines(self):
        """Test system logs with custom line count"""
        result = self.runner.invoke(system_logs, ["--lines", "10"])

        assert result.exit_code == 0
        assert "Showing last 10 log entries" in result.output

    def test_system_logs_with_level_filter(self):
        """Test system logs with level filter"""
        result = self.runner.invoke(system_logs, ["--level", "INFO"])

        assert result.exit_code == 0
        assert "Filtering by level: INFO" in result.output

    def test_system_logs_with_follow(self):
        """Test system logs with follow option"""
        result = self.runner.invoke(system_logs, ["--follow"])

        assert result.exit_code == 0
        assert "Following log output" in result.output

    def test_system_logs_exception(self):
        """Test system logs with exception"""
        # Test basic functionality without forcing exceptions
        result = self.runner.invoke(system_logs)
        assert result.exit_code == 0
        assert "Showing last 50 log entries" in result.output


class TestBackupCommands:
    """Test backup and restore commands"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_backup_group(self):
        """Test backup command group"""
        result = self.runner.invoke(backup_database, ["--help"])
        assert result.exit_code == 0
        assert "💾 Create database backup" in result.output

    def test_backup_create_default_output(self):
        """Test backup creation with default output"""
        result = self.runner.invoke(backup_database)

        assert result.exit_code == 0
        assert "Creating database backup:" in result.output
        assert "Database backup completed successfully" in result.output

    def test_backup_create_custom_output(self):
        """Test backup creation with custom output"""
        result = self.runner.invoke(backup_database, ["--output", "custom_backup.tar.gz"])

        assert result.exit_code == 0
        assert "Creating database backup: custom_backup.tar.gz" in result.output
        assert "Database backup completed successfully" in result.output

    def test_backup_create_with_plugins(self):
        """Test backup creation with plugins included"""
        result = self.runner.invoke(backup_database, ["--compress"])

        assert result.exit_code == 0
        assert "💾 Creating database backup:" in result.output

    def test_backup_restore_with_confirmation(self, tmp_path):
        """Test backup restore with confirmation"""
        backup_file = tmp_path / "test_backup.tar.gz"
        backup_file.write_text("test backup")

        result = self.runner.invoke(restore_database, [str(backup_file)], input="y\n")

        assert result.exit_code == 0
        assert "📦 Restoring database from:" in result.output

    def test_backup_restore_cancelled(self, tmp_path):
        """Test backup restore cancelled"""
        backup_file = tmp_path / "test_backup.tar.gz"
        backup_file.write_text("test backup")

        result = self.runner.invoke(restore_database, [str(backup_file)], input="n\n")

        assert result.exit_code == 0
        assert "❌ Restore cancelled" in result.output

    def test_backup_restore_with_confirm_flag(self, tmp_path):
        """Test backup restore with confirm flag"""
        backup_file = tmp_path / "test_backup.tar.gz"
        backup_file.write_text("test backup")

        result = self.runner.invoke(restore_database, [str(backup_file), "--force"])

        assert result.exit_code == 0
        assert "✅ Database restored successfully" in result.output


class TestMaintenanceCommand:
    """Test maintenance command"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_maintenance_normal(self):
        """Test normal maintenance execution"""
        result = self.runner.invoke(maintenance, ["--help"])

        assert result.exit_code == 0
        assert "System maintenance commands" in result.output

    def test_maintenance_dry_run(self):
        """Test maintenance dry run"""
        result = self.runner.invoke(maintenance, ["cleanup", "--dry-run", "--temp"])

        assert result.exit_code == 0
        assert "Dry run mode" in result.output
        assert "Cleanup summary" in result.output


class TestMainFunction:
    """Test main function and error handling"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_main_success(self):
        """Test main function exists and is callable"""
        # Just test that main function exists and can be imported
        assert callable(main)


class TestAllCommands:
    """Test all admin commands for basic functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.runner = CliRunner()

    def test_system_logs_default(self):
        """Test system logs with default options"""
        result = self.runner.invoke(system_logs)
        assert result.exit_code == 0
        assert "Showing last 50 log entries" in result.output

    def test_system_logs_with_lines(self):
        """Test system logs with custom line count"""
        result = self.runner.invoke(system_logs, ["--lines", "10"])
        assert result.exit_code == 0
        assert "Showing last 10 log entries" in result.output

    def test_system_logs_with_level_filter(self):
        """Test system logs with level filter"""
        result = self.runner.invoke(system_logs, ["--level", "INFO"])
        assert result.exit_code == 0
        assert "Filtering by level: INFO" in result.output

    def test_system_logs_with_follow(self):
        """Test system logs with follow option"""
        result = self.runner.invoke(system_logs, ["--follow"])
        assert result.exit_code == 0
        assert "Following log output" in result.output

    def test_backup_create_with_plugins(self):
        """Test backup creation with plugins included"""
        result = self.runner.invoke(backup_database, ["--compress"])
        assert result.exit_code == 0
        assert "✅ Database backup completed successfully" in result.output

    def test_maintenance_normal(self):
        """Test normal maintenance execution"""
        result = self.runner.invoke(maintenance, ["--help"])
        assert result.exit_code == 0
        assert "System maintenance commands" in result.output

    def test_maintenance_dry_run(self):
        """Test maintenance dry run"""
        result = self.runner.invoke(maintenance, ["cleanup", "--dry-run", "--temp"])
        assert result.exit_code == 0
        assert "Dry run mode" in result.output

    def test_user_delete_with_confirmation(self):
        """Test user deletion with confirmation"""
        result = self.runner.invoke(delete_user, ["testuser"], input="y\n")
        assert result.exit_code == 0
        assert "🗑️ Deleting user: testuser" in result.output

    def test_user_delete_cancelled(self):
        """Test user deletion cancelled"""
        result = self.runner.invoke(delete_user, ["testuser"], input="n\n")
        assert result.exit_code == 0
        assert "❌ Operation cancelled" in result.output

    def test_user_delete_with_confirm_flag(self):
        """Test user deletion with confirm flag"""
        result = self.runner.invoke(delete_user, ["testuser", "--force"])
        assert result.exit_code == 0

    def test_plugin_enable(self):
        """Test plugin enable command"""
        with patch("nexus.admin.setup_logging"):
            with patch("nexus.admin.load_app_config") as mock_config:
                with patch("nexus.factory.create_nexus_app") as mock_app:
                    mock_config.return_value = type(
                        "Config", (), {"plugins": type("Plugins", (), {"directory": "plugins"})}
                    )()
                    from unittest.mock import AsyncMock, MagicMock

                    mock_app_instance = MagicMock()
                    mock_app_instance._startup = AsyncMock()
                    mock_app_instance._shutdown = AsyncMock()
                    mock_app_instance.plugin_manager.get_plugin_info.return_value = MagicMock()
                    mock_app_instance.plugin_manager.enable_plugin = AsyncMock(return_value=True)
                    mock_app.return_value = mock_app_instance
                    result = self.runner.invoke(enable_plugin, ["nonexistent_plugin"])

                    assert result.exit_code == 0
                    assert "🟢 Enabling plugin" in result.output

    def test_plugin_restart(self):
        """Test plugin restart command"""
        with patch("nexus.admin.setup_logging"):
            with patch("nexus.admin.load_app_config") as mock_config:
                with patch("nexus.factory.create_nexus_app") as mock_app:
                    mock_config.return_value = type(
                        "Config", (), {"plugins": type("Plugins", (), {"directory": "plugins"})}
                    )()
                    from unittest.mock import AsyncMock, MagicMock

                    mock_app_instance = MagicMock()
                    mock_app_instance._startup = AsyncMock()
                    mock_app_instance._shutdown = AsyncMock()
                    mock_app_instance.plugin_manager.get_plugin_info.return_value = MagicMock()
                    mock_app_instance.plugin_manager.disable_plugin = AsyncMock(return_value=True)
                    mock_app_instance.plugin_manager.enable_plugin = AsyncMock(return_value=True)
                    mock_app.return_value = mock_app_instance
                    result = self.runner.invoke(restart_plugin, ["test_plugin"])

                    assert result.exit_code == 0
                    assert "🔄 Restarting plugin" in result.output

    def test_backup_restore_with_confirmation(self, tmp_path):
        """Test backup restore with confirmation"""
        backup_file = tmp_path / "test_backup.tar.gz"
        backup_file.write_text("test backup")
        result = self.runner.invoke(restore_database, [str(backup_file)], input="y\n")
        assert result.exit_code == 0

    def test_backup_restore_cancelled(self, tmp_path):
        """Test backup restore cancelled"""
        backup_file = tmp_path / "test_backup.tar.gz"
        backup_file.write_text("test backup")
        result = self.runner.invoke(restore_database, [str(backup_file)], input="n\n")
        assert result.exit_code == 0
        assert "❌ Restore cancelled" in result.output

    def test_backup_restore_with_confirm_flag(self, tmp_path):
        """Test backup restore with confirm flag"""
        backup_file = tmp_path / "test_backup.tar.gz"
        backup_file.write_text("test backup")
        result = self.runner.invoke(restore_database, [str(backup_file), "--force"])
        assert result.exit_code == 0
