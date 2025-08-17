"""
Comprehensive unit tests for the Nexus utils module.

Tests cover existing utility functions like logging setup, file operations, and basic utilities.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

from nexus.utils import (
    JsonFormatter,
    create_directory_if_not_exists,
    deep_merge_dicts,
    ensure_directory,
    format_bytes,
    format_duration,
    format_file_size,
    generate_id,
    generate_random_string,
    get_app_root,
    get_env_var,
    get_environment_var,
    get_file_modification_time,
    get_project_root,
    is_valid_email,
    load_config_file,
    merge_dicts,
    safe_import,
    sanitize_string,
    save_config_file,
    setup_logging,
    validate_config,
    validate_email,
)


class TestLoggingSetup:
    """Test logging setup functionality."""

    @patch("nexus.utils.logging.basicConfig")
    def test_setup_logging_default(self, mock_basic_config):
        """Test setup logging with default parameters."""
        setup_logging()
        mock_basic_config.assert_called_once()

    @patch("nexus.utils.logging.basicConfig")
    def test_setup_logging_with_level(self, mock_basic_config):
        """Test setup logging with custom level."""
        setup_logging(level="DEBUG")
        mock_basic_config.assert_called_once()

    @patch("nexus.utils.logging.basicConfig")
    def test_setup_logging_with_format(self, mock_basic_config):
        """Test setup logging with custom format."""
        custom_format = "%(asctime)s - %(message)s"
        setup_logging(format_string=custom_format)
        mock_basic_config.assert_called_once()

    @patch("nexus.utils.logging.basicConfig")
    def test_setup_logging_with_file(self, mock_basic_config):
        """Test setup logging with file output."""
        setup_logging(log_file="test.log")
        mock_basic_config.assert_called_once()

    @patch("nexus.utils.logging.basicConfig")
    def test_setup_logging_json_format(self, mock_basic_config):
        """Test setup logging with JSON format."""
        setup_logging(enable_json=True)
        mock_basic_config.assert_called_once()


class TestJsonFormatter:
    """Test JSON log formatter."""

    def test_json_formatter_creation(self):
        """Test creating JSON formatter."""
        formatter = JsonFormatter()
        assert formatter is not None

    def test_json_formatter_format_record(self):
        """Test formatting log record as JSON."""
        formatter = JsonFormatter()

        # Create a mock log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="/test/path",
            lineno=10,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)

        # Should be valid JSON
        parsed = json.loads(formatted)
        assert parsed["level"] == "INFO"
        assert parsed["message"] == "Test message"
        assert parsed["logger"] == "test"
        assert "timestamp" in parsed

    def test_json_formatter_with_exception(self):
        """Test JSON formatter with exception info."""
        formatter = JsonFormatter()

        try:
            raise ValueError("Test exception")
        except ValueError:
            import sys

            record = logging.LogRecord(
                name="test",
                level=logging.ERROR,
                pathname="/test/path",
                lineno=10,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

            formatted = formatter.format(record)
            parsed = json.loads(formatted)

            assert parsed["level"] == "ERROR"
            assert "exception" in parsed
            assert "ValueError" in parsed["exception"]


class TestFileOperations:
    """Test file operation utilities."""

    def test_load_config_file_yaml(self):
        """Test loading YAML configuration file."""
        yaml_content = """
app:
  name: "Test App"
  version: "1.0.0"
server:
  port: 8080
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                config = load_config_file(f.name)
                assert config["app"]["name"] == "Test App"
                assert config["app"]["version"] == "1.0.0"
                assert config["server"]["port"] == 8080
            finally:
                os.unlink(f.name)

    def test_load_config_file_json(self):
        """Test loading JSON configuration file."""
        json_content = {"app": {"name": "Test App", "version": "1.0.0"}, "server": {"port": 8080}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(json_content, f)
            f.flush()

            try:
                config = load_config_file(f.name)
                assert config["app"]["name"] == "Test App"
                assert config["app"]["version"] == "1.0.0"
                assert config["server"]["port"] == 8080
            finally:
                os.unlink(f.name)

    def test_load_config_file_nonexistent(self):
        """Test loading non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_config_file("nonexistent.yaml")

    def test_load_config_file_unsupported_format(self):
        """Test loading unsupported file format raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("some content")
            f.flush()

            try:
                with pytest.raises(ValueError, match="Unsupported configuration file format"):
                    load_config_file(f.name)
            finally:
                os.unlink(f.name)

    def test_save_config_file_yaml(self):
        """Test saving configuration to YAML file."""
        config = {"app": {"name": "Test App"}, "server": {"port": 8080}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                save_config_file(config, f.name)

                # Verify file was saved correctly
                loaded = load_config_file(f.name)
                assert loaded == config
            finally:
                os.unlink(f.name)

    def test_save_config_file_json(self):
        """Test saving configuration to JSON file."""
        config = {"app": {"name": "Test App"}, "server": {"port": 8080}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            try:
                save_config_file(config, f.name)

                # Verify file was saved correctly
                loaded = load_config_file(f.name)
                assert loaded == config
            finally:
                os.unlink(f.name)

    def test_save_config_file_unsupported_format(self):
        """Test saving to unsupported format raises error."""
        config = {"test": "data"}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            try:
                with pytest.raises(ValueError, match="Unsupported configuration file format"):
                    save_config_file(config, f.name)
            finally:
                os.unlink(f.name)


class TestEnvironmentVariables:
    """Test environment variable utilities."""

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_get_env_var_exists(self):
        """Test getting existing environment variable."""
        value = get_env_var("TEST_VAR")
        assert value == "test_value"

    def test_get_env_var_not_exists(self):
        """Test getting non-existent environment variable."""
        value = get_env_var("NON_EXISTENT_VAR")
        assert value is None

    def test_get_env_var_with_default(self):
        """Test getting environment variable with default."""
        default_value = "default"
        value = get_env_var("NON_EXISTENT_VAR", default_value)
        assert value == default_value

    def test_get_env_var_required_exists(self):
        """Test getting required environment variable that exists."""
        with patch.dict(os.environ, {"REQUIRED_VAR": "required_value"}):
            value = get_env_var("REQUIRED_VAR", required=True)
            assert value == "required_value"

    def test_get_env_var_required_missing(self):
        """Test getting required environment variable that doesn't exist."""
        with pytest.raises(ValueError, match="Required environment variable"):
            get_env_var("MISSING_REQUIRED_VAR", required=True)

    @patch.dict(os.environ, {"BOOL_VAR": "true"})
    def test_get_env_var_boolean_conversion(self):
        """Test boolean conversion in environment variables."""
        value = get_env_var("BOOL_VAR")
        assert value is True

    @patch.dict(os.environ, {"INT_VAR": "42"})
    def test_get_env_var_int_conversion(self):
        """Test integer conversion in environment variables."""
        value = get_env_var("INT_VAR")
        assert value == 42

    @patch.dict(os.environ, {"FLOAT_VAR": "3.14"})
    def test_get_env_var_float_conversion(self):
        """Test float conversion in environment variables."""
        value = get_env_var("FLOAT_VAR")
        assert value == 3.14


class TestDirectoryUtilities:
    """Test directory utility functions."""

    def test_ensure_directory_new(self):
        """Test creating new directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            assert not new_dir.exists()

            result = ensure_directory(str(new_dir))
            assert new_dir.exists()
            assert new_dir.is_dir()
            assert result == new_dir

    def test_ensure_directory_existing(self):
        """Test with existing directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            result = ensure_directory(temp_dir)
            assert Path(temp_dir).exists()
            assert result == Path(temp_dir)

    def test_ensure_directory_nested(self):
        """Test creating nested directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            nested_path = Path(temp_dir) / "level1" / "level2" / "level3"
            result = ensure_directory(str(nested_path))
            assert nested_path.exists()
            assert nested_path.is_dir()
            assert result == nested_path

    def test_get_project_root(self):
        """Test getting project root."""
        root = get_project_root()
        assert isinstance(root, Path)
        assert root.exists()

    def test_get_app_root(self):
        """Test getting app root."""
        root = get_app_root()
        assert isinstance(root, Path)
        assert root.exists()

    def test_create_directory_if_not_exists_new(self):
        """Test creating new directory via convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            new_dir = Path(temp_dir) / "new_directory"
            assert not new_dir.exists()

            create_directory_if_not_exists(str(new_dir))
            assert new_dir.exists()
            assert new_dir.is_dir()

    def test_create_directory_if_not_exists_existing(self):
        """Test with existing directory via convenience function."""
        with tempfile.TemporaryDirectory() as temp_dir:
            # Should not raise error
            create_directory_if_not_exists(temp_dir)
            assert Path(temp_dir).exists()


class TestFormattingUtilities:
    """Test formatting utility functions."""

    def test_format_bytes_small(self):
        """Test formatting small byte values."""
        assert format_bytes(512) == "512.0 B"
        assert format_bytes(0) == "0.0 B"

    def test_format_bytes_kilobytes(self):
        """Test formatting kilobyte values."""
        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(2048) == "2.0 KB"

    def test_format_bytes_megabytes(self):
        """Test formatting megabyte values."""
        assert format_bytes(1048576) == "1.0 MB"
        assert format_bytes(5242880) == "5.0 MB"

    def test_format_bytes_gigabytes(self):
        """Test formatting gigabyte values."""
        assert format_bytes(1073741824) == "1.0 GB"

    def test_format_bytes_terabytes(self):
        """Test formatting terabyte values."""
        assert format_bytes(1099511627776) == "1.0 TB"

    def test_format_file_size(self):
        """Test file size formatting wrapper."""
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1048576) == "1.0 MB"

    def test_format_duration_seconds(self):
        """Test formatting durations in seconds."""
        assert format_duration(30.5) == "30.5s"
        assert format_duration(59.9) == "59.9s"

    def test_format_duration_minutes(self):
        """Test formatting durations in minutes."""
        assert format_duration(60) == "1.0m"
        assert format_duration(150) == "2.5m"

    def test_format_duration_hours(self):
        """Test formatting durations in hours."""
        assert format_duration(3600) == "1.0h"
        assert format_duration(7200) == "2.0h"

    def test_format_duration_days(self):
        """Test formatting durations in days."""
        assert format_duration(86400) == "1.0d"
        assert format_duration(172800) == "2.0d"


class TestStringUtilities:
    """Test string utility functions."""

    def test_sanitize_string_basic(self):
        """Test basic string sanitization."""
        dirty_string = "  Hello World!  "
        clean = sanitize_string(dirty_string)
        assert clean == "Hello World!"

    def test_sanitize_string_special_chars(self):
        """Test string sanitization with special characters."""
        dirty_string = "<script>alert('xss')</script>"
        clean = sanitize_string(dirty_string)
        assert "<script>" not in clean
        assert clean == "alert('xss')"  # Tags removed but content remains

    def test_sanitize_string_whitespace(self):
        """Test sanitizing whitespace."""
        test_cases = [
            ("  hello  ", "hello"),
            ("\thello\n", "hello"),
            ("  hello\t\nworld  ", "hello world"),
        ]

        for input_str, expected in test_cases:
            assert sanitize_string(input_str) == expected

    def test_sanitize_string_empty(self):
        """Test sanitizing empty string."""
        assert sanitize_string("") == ""
        assert sanitize_string(None) == ""

    def test_sanitize_string_non_string(self):
        """Test sanitizing non-string values."""
        assert sanitize_string(123) == "123"
        assert sanitize_string(True) == "True"

    def test_sanitize_string_max_length(self):
        """Test string sanitization with max length."""
        long_string = "a" * 200
        clean = sanitize_string(long_string, max_length=50)
        assert len(clean) <= 50
        assert clean.endswith("...")

    def test_validate_email_valid(self):
        """Test email validation with valid emails."""
        valid_emails = [
            "user@example.com",
            "test.email@domain.co.uk",
            "user+tag@example.org",
            "user123@test-domain.com",
        ]

        for email in valid_emails:
            assert validate_email(email) == True
            assert is_valid_email(email) == True

    def test_validate_email_invalid(self):
        """Test email validation with invalid emails."""
        invalid_emails = ["invalid-email", "@example.com", "user@", "user@example", ""]

        for email in invalid_emails:
            assert validate_email(email) == False
            assert is_valid_email(email) == False

    def test_generate_id_default(self):
        """Test generating ID with default parameters."""
        id_str = generate_id()
        assert len(id_str) == 8
        assert isinstance(id_str, str)

    def test_generate_id_with_prefix(self):
        """Test generating ID with prefix."""
        id_str = generate_id("test", 6)
        assert id_str.startswith("test_")
        assert len(id_str) == 11  # "test_" + 6 chars

    def test_generate_id_custom_length(self):
        """Test generating ID with custom length."""
        id_str = generate_id(length=12)
        assert len(id_str) == 12

    def test_generate_id_uniqueness(self):
        """Test that generated IDs are unique."""
        id1 = generate_id()
        id2 = generate_id()
        assert id1 != id2

    def test_generate_random_string_default_length(self):
        """Test generating random string with default length."""
        string = generate_random_string()
        assert len(string) == 32
        assert isinstance(string, str)

    def test_generate_random_string_custom_length(self):
        """Test generating random string with custom length."""
        string = generate_random_string(16)
        assert len(string) == 16
        assert isinstance(string, str)

    def test_generate_random_string_uniqueness(self):
        """Test that generated strings are unique."""
        string1 = generate_random_string()
        string2 = generate_random_string()
        assert string1 != string2


class TestDictionaryUtilities:
    """Test dictionary utility functions."""

    def test_deep_merge_dicts_basic(self):
        """Test basic dictionary merging."""
        dict1 = {"a": 1, "b": 2}
        dict2 = {"c": 3, "d": 4}

        result = deep_merge_dicts(dict1, dict2)
        expected = {"a": 1, "b": 2, "c": 3, "d": 4}
        assert result == expected

    def test_deep_merge_dicts_nested(self):
        """Test nested dictionary merging."""
        dict1 = {"app": {"name": "Test", "version": "1.0"}}
        dict2 = {"app": {"port": 8080}, "server": {"host": "localhost"}}

        result = deep_merge_dicts(dict1, dict2)
        assert result["app"]["name"] == "Test"
        assert result["app"]["port"] == 8080
        assert result["server"]["host"] == "localhost"

    def test_deep_merge_dicts_override(self):
        """Test dictionary merging with value override."""
        dict1 = {"key": "value1"}
        dict2 = {"key": "value2"}

        result = deep_merge_dicts(dict1, dict2)
        assert result["key"] == "value2"

    def test_merge_dicts_wrapper(self):
        """Test merge_dicts wrapper function."""
        dict1 = {"a": 1}
        dict2 = {"b": 2}

        result = merge_dicts(dict1, dict2)
        assert result == {"a": 1, "b": 2}

    def test_validate_config_valid(self):
        """Test config validation with valid config."""
        config = {"app": {"name": "Test App"}, "server": {"port": 8080}}
        assert validate_config(config) == True

    def test_validate_config_invalid(self):
        """Test config validation with invalid config."""
        invalid_configs = [None, "not a dict", [], {"app": None}]

        for config in invalid_configs:
            assert validate_config(config) == False


class TestImportUtilities:
    """Test import utility functions."""

    def test_safe_import_valid_module(self):
        """Test safe import with valid module."""
        module = safe_import("json")
        assert module is not None
        assert hasattr(module, "loads")

    def test_safe_import_invalid_module(self):
        """Test safe import with invalid module."""
        module = safe_import("nonexistent_module_12345")
        assert module is None

    def test_safe_import_with_fallback(self):
        """Test safe import with fallback value."""
        fallback = "fallback_value"
        result = safe_import("nonexistent_module", fallback)
        assert result == fallback


class TestEnvironmentUtilities:
    """Test environment utility functions."""

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_get_environment_var_exists(self):
        """Test getting existing environment variable."""
        value = get_environment_var("TEST_VAR")
        assert value == "test_value"

    def test_get_environment_var_not_exists(self):
        """Test getting non-existent environment variable."""
        value = get_environment_var("NON_EXISTENT_VAR")
        assert value is None

    def test_get_environment_var_with_default(self):
        """Test getting environment variable with default."""
        default_value = "default"
        value = get_environment_var("NON_EXISTENT_VAR", default_value)
        assert value == default_value


class TestFileUtilities:
    """Test file utility functions."""

    def test_get_file_modification_time_existing(self):
        """Test getting modification time of existing file."""
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(b"test content")
            f.flush()

            try:
                mod_time = get_file_modification_time(f.name)
                assert isinstance(mod_time, float)
                assert mod_time > 0
            finally:
                os.unlink(f.name)

    def test_get_file_modification_time_nonexistent(self):
        """Test getting modification time of non-existent file."""
        mod_time = get_file_modification_time("nonexistent_file.txt")
        assert mod_time is None


class TestFormatUtilities:
    """Test format utility functions."""

    def test_format_bytes_small_values(self):
        """Test format_bytes with small values."""
        from nexus.utils import format_bytes

        assert format_bytes(0) == "0.0 B"
        assert format_bytes(512) == "512.0 B"
        assert format_bytes(1023) == "1023.0 B"

    def test_format_bytes_kilobytes(self):
        """Test format_bytes with kilobyte values."""
        from nexus.utils import format_bytes

        assert format_bytes(1024) == "1.0 KB"
        assert format_bytes(2048) == "2.0 KB"
        assert format_bytes(1536) == "1.5 KB"

    def test_format_bytes_megabytes(self):
        """Test format_bytes with megabyte values."""
        from nexus.utils import format_bytes

        assert format_bytes(1024 * 1024) == "1.0 MB"
        assert format_bytes(1024 * 1024 * 2) == "2.0 MB"

    def test_format_bytes_gigabytes(self):
        """Test format_bytes with gigabyte values."""
        from nexus.utils import format_bytes

        assert format_bytes(1024 * 1024 * 1024) == "1.0 GB"
        assert format_bytes(1024 * 1024 * 1024 * 3) == "3.0 GB"

    def test_format_bytes_terabytes(self):
        """Test format_bytes with terabyte values."""
        from nexus.utils import format_bytes

        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.0 TB"

    def test_format_bytes_petabytes(self):
        """Test format_bytes with huge values (petabytes)."""
        from nexus.utils import format_bytes

        # This should hit the final return statement (line 184)
        huge_value = 1024 * 1024 * 1024 * 1024 * 1024 * 2  # 2 PB
        result = format_bytes(huge_value)
        assert "PB" in result
        assert "2.0 PB" == result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
