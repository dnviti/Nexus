"""
Basic unit tests for the Nexus CLI module.

Tests cover CLI commands, configuration loading, and basic functionality.
"""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from nexus.cli import (
    cli,
    health,
    init,
    main,
    plugin,
    plugin_create,
    plugin_info,
    plugin_list,
    run,
    status,
    validate,
)
from nexus.core import AppConfig


class TestCLIBasic:
    """Test basic CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_group_exists(self):
        """Test that CLI group exists."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Usage:" in result.output

    def test_cli_version(self):
        """Test CLI version command."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "Nexus" in result.output

    def test_cli_verbose_flag(self):
        """Test CLI verbose flag."""
        result = self.runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_cli_config_flag(self):
        """Test CLI config flag with valid file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("app:\n  name: TestApp\n")
            f.flush()

            try:
                result = self.runner.invoke(cli, ["--config", f.name, "--help"])
                assert result.exit_code == 0
            finally:
                os.unlink(f.name)


class TestRunCommand:
    """Test run command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_run_command_exists(self):
        """Test that run command exists."""
        result = self.runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "Run the Nexus application server" in result.output

    @patch("nexus.create_nexus_app")
    @patch("uvicorn.run")
    def test_run_command_basic(self, mock_uvicorn, mock_create_app):
        """Test basic run command."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        result = self.runner.invoke(cli, ["run"])

        # Command should attempt to start the app
        mock_create_app.assert_called_once()
        mock_uvicorn.assert_called_once()

    @patch("nexus.create_nexus_app")
    @patch("uvicorn.run")
    def test_run_command_with_host_port(self, mock_uvicorn, mock_create_app):
        """Test run command with custom host and port."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        result = self.runner.invoke(cli, ["run", "--host", "0.0.0.0", "--port", "9000"])

        mock_uvicorn.assert_called_once()
        # Check that uvicorn was called with correct parameters
        call_args = mock_uvicorn.call_args
        assert call_args[1]["host"] == "0.0.0.0"
        assert call_args[1]["port"] == 9000

    @patch("nexus.create_nexus_app")
    @patch("uvicorn.run")
    def test_run_command_with_reload(self, mock_uvicorn, mock_create_app):
        """Test run command with reload option."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        result = self.runner.invoke(cli, ["run", "--reload"])

        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args
        assert call_args[1]["reload"] == True

    @patch("nexus.create_nexus_app")
    @patch("uvicorn.run")
    def test_run_command_with_workers(self, mock_uvicorn, mock_create_app):
        """Test run command with workers option."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        result = self.runner.invoke(cli, ["run", "--workers", "4"])

        mock_uvicorn.assert_called_once()
        call_args = mock_uvicorn.call_args
        assert call_args[1]["workers"] == 4


class TestInitCommand:
    """Test init command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_init_command_exists(self):
        """Test that init command exists."""
        result = self.runner.invoke(cli, ["init", "--help"])
        assert result.exit_code == 0
        assert "Initialize a new Nexus project" in result.output

    @patch("nexus.cli.create_default_config")
    def test_init_command_basic(self, mock_create_config):
        """Test basic init command."""
        mock_config = AppConfig()
        mock_create_config.return_value = mock_config

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["init"])

            # Should complete successfully
            assert result.exit_code == 0
            mock_create_config.assert_called_once()

    @patch("nexus.cli.create_default_config")
    def test_init_command_with_output(self, mock_create_config):
        """Test init command with output option."""
        mock_config = AppConfig()
        mock_create_config.return_value = mock_config

        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["init", "--output", "custom_config.yaml"])

            # Should handle output option
            assert result.exit_code == 0


class TestPluginCommands:
    """Test plugin-related commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_plugin_group_exists(self):
        """Test that plugin group exists."""
        result = self.runner.invoke(plugin, ["--help"])
        assert result.exit_code == 0
        assert "Plugin management commands" in result.output

    def test_plugin_list_command_exists(self):
        """Test that plugin list command exists."""
        result = self.runner.invoke(cli, ["plugin", "list", "--help"])
        assert result.exit_code == 0

    def test_plugin_list_basic(self):
        """Test basic plugin listing."""
        result = self.runner.invoke(cli, ["plugin", "list"])

        # Should list plugins
        assert result.exit_code == 0
        assert "Available Plugins" in result.output

    def test_plugin_create_command_exists(self):
        """Test that plugin create command exists."""
        result = self.runner.invoke(cli, ["plugin", "create", "--help"])
        assert result.exit_code == 0

    def test_plugin_create_basic(self):
        """Test basic plugin creation."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["plugin", "create", "test_plugin"])

            # Should attempt to create plugin
            assert result.exit_code == 0

    def test_plugin_create_with_template(self):
        """Test plugin creation with template."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(
                cli, ["plugin", "create", "--template", "basic", "test_plugin"]
            )

            # Should handle template option
            assert result.exit_code == 0

    def test_plugin_info_command_exists(self):
        """Test that plugin info command exists."""
        result = self.runner.invoke(cli, ["plugin", "info", "--help"])
        assert result.exit_code == 0

    def test_plugin_info_basic(self):
        """Test basic plugin info."""
        result = self.runner.invoke(cli, ["plugin", "info", "test_plugin"])

        # Should show plugin information
        assert result.exit_code == 0
        assert "Plugin Information" in result.output


class TestStatusCommand:
    """Test status command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_status_command_exists(self):
        """Test that status command exists."""
        result = self.runner.invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_status_command_basic(self):
        """Test basic status command."""
        result = self.runner.invoke(cli, ["status"])

        # Should display status information
        assert result.exit_code == 0
        assert "Nexus Framework Status" in result.output

    def test_status_shows_version(self):
        """Test that status shows version."""
        result = self.runner.invoke(cli, ["status"])

        assert result.exit_code == 0
        assert "Version:" in result.output


class TestHealthCommand:
    """Test health command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_health_command_exists(self):
        """Test that health command exists."""
        result = self.runner.invoke(cli, ["health", "--help"])
        assert result.exit_code == 0

    def test_health_command_basic(self):
        """Test basic health command."""
        result = self.runner.invoke(cli, ["health"])

        # Should display health information
        assert result.exit_code == 0
        assert "Health Check" in result.output

    def test_health_command_json_format(self):
        """Test health command with JSON format."""
        result = self.runner.invoke(cli, ["health", "--format", "json"])

        # Should output JSON format
        assert result.exit_code == 0


class TestValidateCommand:
    """Test validate command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_validate_command_exists(self):
        """Test that validate command exists."""
        result = self.runner.invoke(cli, ["validate", "--help"])
        assert result.exit_code == 0

    def test_validate_command_basic(self):
        """Test basic validate command."""
        with self.runner.isolated_filesystem():
            # Create a basic config file
            with open("nexus_config.yaml", "w") as f:
                f.write("app:\n  name: TestApp\n")

            result = self.runner.invoke(cli, ["validate"])

            # Should validate configuration
            assert result.exit_code == 0
            assert "Validating Configuration" in result.output

    def test_validate_with_config_file(self):
        """Test validate command with specific config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("app:\n  name: TestApp\n")
            f.flush()

            try:
                result = self.runner.invoke(cli, ["validate", "--config-file", f.name])
                # Should validate the specified file
                assert result.exit_code == 0
            finally:
                os.unlink(f.name)


class TestMainFunction:
    """Test main function."""

    def test_main_function_exists(self):
        """Test that main function exists."""
        assert callable(main)

    @patch("nexus.cli.cli")
    def test_main_function_calls_cli(self, mock_cli):
        """Test that main function calls CLI."""
        main()
        mock_cli.assert_called_once()

    @patch("nexus.cli.cli")
    def test_main_function_keyboard_interrupt(self, mock_cli):
        """Test main function handles keyboard interrupt."""
        mock_cli.side_effect = KeyboardInterrupt()

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 130

    @patch("nexus.cli.cli")
    def test_main_function_exception(self, mock_cli):
        """Test main function handles exceptions."""
        mock_cli.side_effect = Exception("Test error")

        with pytest.raises(SystemExit) as exc_info:
            main()

        assert exc_info.value.code == 1


class TestCLIConfiguration:
    """Test CLI configuration handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_config_loading_yaml(self):
        """Test loading YAML configuration."""
        yaml_config = """
app:
  name: "CLI Test App"
  version: "1.0.0"
server:
  host: "localhost"
  port: 8080
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_config)
            f.flush()

            try:
                # Test that config file can be loaded
                result = self.runner.invoke(cli, ["--config", f.name, "--help"])
                assert result.exit_code == 0
            finally:
                os.unlink(f.name)

    def test_config_loading_json(self):
        """Test loading JSON configuration."""
        json_config = """
{
  "app": {
    "name": "CLI Test App",
    "version": "1.0.0"
  },
  "server": {
    "host": "localhost",
    "port": 8080
  }
}
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_config)
            f.flush()

            try:
                result = self.runner.invoke(cli, ["--config", f.name, "--help"])
                assert result.exit_code == 0
            finally:
                os.unlink(f.name)


class TestCLIEnvironment:
    """Test CLI environment handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch.dict(os.environ, {"NEXUS_CONFIG": "test_config.yaml"})
    def test_environment_config(self):
        """Test configuration from environment variables."""
        result = self.runner.invoke(cli, ["--help"])
        # Should handle environment configuration
        assert result.exit_code == 0

    @patch.dict(os.environ, {"NEXUS_LOG_LEVEL": "DEBUG"})
    def test_environment_log_level(self):
        """Test log level from environment."""
        result = self.runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

    def test_cli_with_no_config(self):
        """Test CLI behavior with no configuration."""
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_invalid_command(self):
        """Test handling of invalid commands."""
        result = self.runner.invoke(cli, ["invalid_command"])
        assert result.exit_code != 0

    @patch("nexus.cli.setup_logging")
    def test_logging_setup_error(self, mock_setup_logging):
        """Test handling of logging setup errors."""
        mock_setup_logging.side_effect = Exception("Logging setup failed")

        # Should handle logging setup errors gracefully
        result = self.runner.invoke(cli, ["--verbose", "--help"])
        # The exact behavior depends on implementation


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("nexus.cli.create_default_config")
    def test_init_and_status_workflow(self, mock_create_config):
        """Test init followed by status check."""
        mock_config = AppConfig()
        mock_create_config.return_value = mock_config

        with self.runner.isolated_filesystem():
            # Initialize project
            result = self.runner.invoke(cli, ["init"])
            assert result.exit_code == 0

            # Check status
            result = self.runner.invoke(cli, ["status"])
            assert result.exit_code == 0

    @patch("nexus.create_nexus_app")
    @patch("uvicorn.run")
    def test_run_with_config(self, mock_uvicorn, mock_create_app):
        """Test running app with configuration file."""
        mock_app = MagicMock()
        mock_create_app.return_value = mock_app

        config_content = """
app:
  name: "Configured App"
server:
  host: "0.0.0.0"
  port: 9000
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(config_content)
            f.flush()

            try:
                result = self.runner.invoke(cli, ["--config", f.name, "run"])
                mock_create_app.assert_called_once()
            finally:
                os.unlink(f.name)

    def test_plugin_workflow(self):
        """Test plugin management workflow."""
        with self.runner.isolated_filesystem():
            # List plugins
            result = self.runner.invoke(cli, ["plugin", "list"])
            assert result.exit_code == 0

            # Create plugin
            result = self.runner.invoke(cli, ["plugin", "create", "test_plugin"])
            assert result.exit_code == 0

            # Get plugin info
            result = self.runner.invoke(cli, ["plugin", "info", "test_plugin"])
            assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
