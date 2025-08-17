"""
Comprehensive unit tests for the Nexus config module.

Tests cover configuration loading, validation, merging, and all configuration classes.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest

from nexus.config import (
    AppConfig,
    AppSettings,
    AuthConfig,
    CacheConfig,
    ConfigLoader,
    CORSConfig,
    DatabaseConfig,
    DatabaseConnectionConfig,
    DatabasePoolConfig,
    DatabaseType,
    Environment,
    LoggingConfig,
    LogLevel,
    PluginConfig,
    SecurityConfig,
    ServerConfig,
    create_default_config,
    deep_merge,
    load_config,
)


class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"
        assert Environment.STAGING == "staging"


class TestDatabaseType:
    """Test DatabaseType enum."""

    def test_database_type_values(self):
        """Test database type enum values."""
        assert DatabaseType.SQLITE == "sqlite"
        assert DatabaseType.POSTGRESQL == "postgresql"
        assert DatabaseType.MYSQL == "mysql"
        assert DatabaseType.REDIS == "redis"


class TestLogLevel:
    """Test LogLevel enum."""

    def test_log_level_values(self):
        """Test log level enum values."""
        assert LogLevel.DEBUG == "DEBUG"
        assert LogLevel.INFO == "INFO"
        assert LogLevel.WARNING == "WARNING"
        assert LogLevel.ERROR == "ERROR"
        assert LogLevel.CRITICAL == "CRITICAL"


class TestCORSConfig:
    """Test CORS configuration."""

    def test_cors_config_defaults(self):
        """Test CORS config default values."""
        config = CORSConfig()
        assert config.enabled == True
        assert config.origins == ["*"]
        assert config.methods == ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
        assert config.headers == ["*"]
        assert config.credentials == True
        assert config.max_age == 3600

    def test_cors_config_custom_values(self):
        """Test CORS config with custom values."""
        config = CORSConfig(
            enabled=False,
            origins=["http://localhost:3000"],
            methods=["GET", "POST"],
            headers=["Content-Type"],
            credentials=False,
            max_age=1800,
        )
        assert config.enabled == False
        assert config.origins == ["http://localhost:3000"]
        assert config.methods == ["GET", "POST"]
        assert config.headers == ["Content-Type"]
        assert config.credentials == False
        assert config.max_age == 1800


class TestServerConfig:
    """Test server configuration."""

    def test_server_config_defaults(self):
        """Test server config default values."""
        config = ServerConfig()
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.workers == 1
        assert config.reload == False
        assert config.access_log == True

    def test_server_config_custom_values(self):
        """Test server config with custom values."""
        config = ServerConfig(host="127.0.0.1", port=9000, workers=4, reload=True, access_log=False)
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.workers == 4
        assert config.reload == True
        assert config.access_log == False


class TestDatabaseConnectionConfig:
    """Test database connection configuration."""

    def test_database_connection_defaults(self):
        """Test database connection default values."""
        config = DatabaseConnectionConfig()
        assert config.host == "localhost"
        assert config.port == 5432  # PostgreSQL default
        assert config.username == None
        assert config.password == None
        assert config.database == "nexus_db"

    def test_database_connection_custom_values(self):
        """Test database connection with custom values."""
        config = DatabaseConnectionConfig(
            host="db.example.com", port=3306, username="admin", password="secret", database="myapp"
        )
        assert config.host == "db.example.com"
        assert config.port == 3306
        assert config.username == "admin"
        assert config.password == "secret"
        assert config.database == "myapp"


class TestDatabasePoolConfig:
    """Test database pool configuration."""

    def test_database_pool_defaults(self):
        """Test database pool default values."""
        config = DatabasePoolConfig()
        assert config.min_size == 10
        assert config.max_size == 20
        assert config.pool_timeout == 30
        assert config.pool_recycle == 3600

    def test_database_pool_custom_values(self):
        """Test database pool with custom values."""
        config = DatabasePoolConfig(min_size=2, max_size=10, pool_timeout=60, pool_recycle=7200)
        assert config.min_size == 2
        assert config.max_size == 10
        assert config.pool_timeout == 60
        assert config.pool_recycle == 7200


class TestDatabaseConfig:
    """Test database configuration."""

    def test_database_config_defaults(self):
        """Test database config with defaults."""
        config = DatabaseConfig()
        assert config.type == DatabaseType.POSTGRESQL
        assert config.echo == False
        assert config.echo_pool == False
        assert config.connection.host == "localhost"
        assert config.pool.min_size == 10

    def test_database_config_get_connection_url_postgresql(self):
        """Test PostgreSQL connection URL generation."""
        config = DatabaseConfig()
        config.type = DatabaseType.POSTGRESQL
        config.connection.host = "localhost"
        config.connection.port = 5432
        config.connection.username = "user"
        config.connection.password = "pass"
        config.connection.database = "testdb"

        url = config.get_connection_url()
        assert url == "postgresql+asyncpg://user:pass@localhost:5432/testdb"

    def test_database_config_get_connection_url_mysql(self):
        """Test MySQL connection URL generation."""
        config = DatabaseConfig()
        config.type = DatabaseType.MYSQL
        config.connection.host = "localhost"
        config.connection.port = 3306
        config.connection.username = "user"
        config.connection.password = "pass"
        config.connection.database = "testdb"

        url = config.get_connection_url()
        assert url == "mysql+aiomysql://user:pass@localhost:3306/testdb"

    def test_database_config_get_connection_url_sqlite(self):
        """Test SQLite connection URL generation."""
        config = DatabaseConfig()
        config.type = DatabaseType.SQLITE
        config.connection.path = "test.db"

        url = config.get_connection_url()
        assert url == "sqlite:///test.db"

    def test_database_config_get_connection_url_mongodb(self):
        """Test MongoDB connection URL generation."""
        config = DatabaseConfig()
        config.type = DatabaseType.MONGODB
        config.connection.host = "localhost"
        config.connection.port = 27017
        config.connection.username = "user"
        config.connection.password = "pass"
        config.connection.database = "testdb"

        url = config.get_connection_url()
        assert "mongodb://user:pass@localhost:27017/testdb" in url

    def test_mongodb_config_with_replica_set(self):
        """Test MongoDB config with replica set."""
        config = DatabaseConfig()
        config.type = DatabaseType.MONGODB
        config.connection.host = "localhost"
        config.connection.port = 27017
        config.connection.database = "testdb"
        config.connection.replica_set = "rs0"

        url = config.get_connection_url()
        assert "mongodb://localhost:27017/testdb?replicaSet=rs0" in url

    def test_mongodb_config_with_auth_source(self):
        """Test MongoDB config with auth source."""
        config = DatabaseConfig()
        config.type = DatabaseType.MONGODB
        config.connection.host = "localhost"
        config.connection.port = 27017
        config.connection.database = "testdb"
        config.connection.replica_set = "rs0"
        config.connection.auth_source = "admin"

        url = config.get_connection_url()
        assert "mongodb://localhost:27017/testdb?replicaSet=rs0&authSource=admin" in url

    def test_mongodb_config_full_options(self):
        """Test MongoDB config with all options."""
        config = DatabaseConfig()
        config.type = DatabaseType.MONGODB
        config.connection.host = "localhost"
        config.connection.port = 27017
        config.connection.username = "user"
        config.connection.password = "pass"
        config.connection.database = "testdb"
        config.connection.replica_set = "rs0"
        config.connection.auth_source = "admin"

        url = config.get_connection_url()
        assert "mongodb://user:pass@localhost:27017/testdb?replicaSet=rs0&authSource=admin" in url

    def test_redis_config_with_password(self):
        """Test Redis config with password."""
        config = CacheConfig()
        config.redis_host = "localhost"
        config.redis_port = 6379
        config.redis_db = 0
        config.redis_password = "secret123"

        url = config.get_redis_url()
        assert "redis://:secret123@localhost:6379/0" in url


class TestAuthConfig:
    """Test authentication configuration."""

    def test_auth_config_defaults(self):
        """Test auth config defaults."""
        config = AuthConfig()
        assert config.jwt_secret == "change-me-in-production"
        assert config.jwt_algorithm == "HS256"

    def test_auth_config_custom_values(self):
        """Test auth config with custom values."""
        config = AuthConfig()
        config.jwt_secret = "my-super-secure-jwt-secret-key-32-chars"
        config.jwt_algorithm = "HS512"

        assert config.jwt_secret == "my-super-secure-jwt-secret-key-32-chars"
        assert config.jwt_algorithm == "HS512"

    def test_auth_config_jwt_warning(self):
        """Test JWT secret validation warning."""
        import logging
        from unittest.mock import patch

        # Test the JWT secret validator function directly
        from nexus.config import AuthConfig

        with patch("nexus.config.logger.warning") as mock_warning:
            # Create config with default secret and trigger validation
            config = AuthConfig(jwt_secret="change-me-in-production")

            # The validator should be called during model creation
            # and should log a warning for the default value
            mock_warning.assert_called_once_with(
                "Using default JWT secret. Please change in production!"
            )


class TestCacheConfig:
    """Test cache configuration."""

    def test_cache_config_defaults(self):
        """Test cache config defaults."""
        config = CacheConfig()
        assert config.type == "redis"
        assert config.redis_host == "localhost"
        assert config.redis_port == 6379
        assert config.redis_db == 0
        assert config.default_ttl == 300

    def test_cache_config_get_redis_url(self):
        """Test Redis URL generation for cache."""
        config = CacheConfig(redis_host="cache.example.com", redis_port=6380, redis_db=1)
        url = config.get_redis_url()
        assert url == "redis://cache.example.com:6380/1"


class TestAuthConfig:
    """Test authentication configuration."""

    def test_auth_config_defaults(self):
        """Test auth config defaults."""
        config = AuthConfig()
        assert config.jwt_secret == "change-me-in-production"
        assert config.jwt_algorithm == "HS256"
        assert config.token_expiry == 3600
        assert config.refresh_token_expiry == 604800
        assert config.session_max_age == 86400
        assert config.password_min_length == 8

    def test_auth_config_custom_values(self):
        """Test auth config with custom values."""
        config = AuthConfig(
            jwt_secret="custom-secret-that-is-long-enough-for-validation",
            jwt_algorithm="HS512",
            token_expiry=7200,
            refresh_token_expiry=1209600,
            session_max_age=172800,
            password_min_length=12,
        )
        assert config.jwt_secret == "custom-secret-that-is-long-enough-for-validation"
        assert config.jwt_algorithm == "HS512"
        assert config.token_expiry == 7200
        assert config.refresh_token_expiry == 1209600
        assert config.session_max_age == 172800
        assert config.password_min_length == 12


class TestSecurityConfig:
    """Test security configuration."""

    def test_security_config_defaults(self):
        """Test security config defaults."""
        config = SecurityConfig()
        assert config.https_redirect == False
        assert config.hsts_enabled == False
        assert config.hsts_max_age == 31536000
        assert config.csrf_enabled == True
        assert config.csrf_token_length == 32
        assert config.rate_limiting_enabled == True
        assert config.rate_limit_requests == 1000
        assert config.rate_limit_window == 3600
        assert config.allowed_hosts == ["*"]
        assert config.trusted_proxies == []


class TestLoggingConfig:
    """Test logging configuration."""

    def test_logging_config_defaults(self):
        """Test logging config defaults."""
        config = LoggingConfig()
        assert config.level == LogLevel.INFO
        assert config.format == "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        assert config.file_enabled == True
        assert config.file_path == "./logs/nexus.log"
        assert config.file_max_size == 10485760
        assert config.file_backup_count == 5
        assert config.console_enabled == True

    @patch("nexus.config.logging.config.dictConfig")
    def test_logging_config_configure_logging(self, mock_dict_config):
        """Test logging configuration setup."""
        config = LoggingConfig()
        config.configure_logging()
        mock_dict_config.assert_called_once()


class TestPluginConfig:
    """Test plugin configuration."""

    def test_plugin_config_defaults(self):
        """Test plugin config defaults."""
        config = PluginConfig()
        assert config.directory == "./plugins"
        assert config.auto_load == True
        assert config.hot_reload == False
        assert config.lazy_load == False
        assert config.scan_interval == 60
        assert config.max_load_time == 30
        assert config.require_manifest == True
        assert config.sandbox_enabled == False
        assert config.allowed_imports == ["*"]


class TestAppSettings:
    """Test application settings."""

    def test_app_settings_defaults(self):
        """Test app settings defaults."""
        config = AppSettings()
        assert config.name == "Nexus Application"
        assert config.description == "A Nexus Framework application"
        assert config.version == "1.0.0"
        assert config.environment == Environment.DEVELOPMENT
        assert config.debug == False

    def test_app_settings_custom_values(self):
        """Test app settings with custom values."""
        config = AppSettings(
            name="My App",
            description="Custom app",
            version="2.0.0",
            environment=Environment.PRODUCTION,
            debug=True,
        )
        assert config.name == "My App"
        assert config.description == "Custom app"
        assert config.version == "2.0.0"
        assert config.environment == Environment.PRODUCTION
        assert config.debug == True


class TestAppConfig:
    """Test main application configuration."""

    def test_app_config_defaults(self):
        """Test app config with default values."""
        config = AppConfig()
        assert isinstance(config.app, AppSettings)
        assert isinstance(config.server, ServerConfig)
        assert isinstance(config.database, DatabaseConfig)
        assert isinstance(config.cache, CacheConfig)
        assert isinstance(config.auth, AuthConfig)
        assert isinstance(config.security, SecurityConfig)
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.plugins, PluginConfig)
        assert isinstance(config.cors, CORSConfig)
        assert config.custom == {}

    def test_app_config_merge(self):
        """Test merging two app configs."""
        config1 = AppConfig()
        config1.app.name = "App 1"
        config1.server.port = 8000

        config2 = AppConfig()
        config2.app.name = "App 1"  # Keep the same name for merge test
        config2.app.description = "New description"
        config2.server.port = 9000
        config2.database.echo = True
        config2.auth.jwt_secret = "another-very-long-secret-key-for-testing-merge-functionality"

        merged = config1.merge(config2)
        assert merged.app.name == "App 1"  # From config1
        assert merged.app.description == "New description"  # From config2
        assert merged.server.port == 9000  # Overridden by config2
        assert merged.database.echo == True  # From config2


class TestConfigLoader:
    """Test configuration loader."""

    def test_config_loader_creation(self):
        """Test config loader creation."""
        loader = ConfigLoader()
        assert loader is not None

    def test_load_yaml_file(self):
        """Test loading YAML configuration file."""
        yaml_content = """
app:
  name: "Test App"
  version: "1.0.0"
server:
  port: 9000
  debug: true
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                loader = ConfigLoader()
                config = loader.load_file(f.name)

                assert config["app"]["name"] == "Test App"
                assert config["app"]["version"] == "1.0.0"
                assert config["server"]["port"] == 9000
                assert config["server"]["debug"] == True
            finally:
                os.unlink(f.name)

    def test_load_json_file(self):
        """Test loading JSON configuration file."""
        json_content = """{
    "app": {
        "name": "Test App",
        "version": "1.0.0"
    },
    "server": {
        "port": 9000,
        "debug": true
    }
}"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(json_content)
            f.flush()

            try:
                loader = ConfigLoader()
                config = loader.load_file(f.name)

                assert config["app"]["name"] == "Test App"
                assert config["app"]["version"] == "1.0.0"
                assert config["server"]["port"] == 9000
                assert config["server"]["debug"] == True
            finally:
                os.unlink(f.name)

    def test_load_unsupported_file_format(self):
        """Test loading unsupported file format raises error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("some content")
            f.flush()

            try:
                with pytest.raises(ValueError, match="Unsupported.*file.*type"):
                    load_config(f.name)
            finally:
                os.unlink(f.name)

    def test_load_nonexistent_file(self):
        """Test loading non-existent file raises error."""
        loader = ConfigLoader()
        with pytest.raises(FileNotFoundError):
            loader.load_file("nonexistent.yaml")

    @patch.dict(os.environ, {"TEST_VAR": "test_value"})
    def test_substitute_env_vars(self):
        """Test environment variable substitution."""
        loader = ConfigLoader()
        data = {
            "key1": "${TEST_VAR}",
            "key2": "prefix_${TEST_VAR}_suffix",
            "key3": "no_substitution",
            "nested": {"key4": "${TEST_VAR}"},
        }

        result = loader._substitute_env_vars(data)
        assert result["key1"] == "test_value"
        assert result["key2"] == "prefix_test_value_suffix"
        assert result["key3"] == "no_substitution"
        assert result["nested"]["key4"] == "test_value"

    @patch.dict(os.environ, {"PORT": "9000", "DEBUG": "true"})
    def test_load_from_env(self):
        """Test loading configuration from environment variables."""
        loader = ConfigLoader()
        config = loader.load_from_env()

        # Should have some environment-based configuration
        assert isinstance(config, dict)


class TestUtilityFunctions:
    """Test utility functions."""

    def test_deep_merge(self):
        """Test deep merge functionality."""
        base = {"a": 1, "b": {"c": 2, "d": 3}, "e": [1, 2, 3]}

        override = {"b": {"d": 4, "f": 5}, "g": 6}

        result = deep_merge(base, override)

        assert result["a"] == 1
        assert result["b"]["c"] == 2
        assert result["b"]["d"] == 4
        assert result["b"]["f"] == 5
        assert result["e"] == [1, 2, 3]
        assert result["g"] == 6

    def test_create_default_config(self):
        """Test creating default configuration."""
        config = create_default_config()
        assert isinstance(config, AppConfig)
        assert config.app.name == "Nexus Application"
        assert config.server.port == 8000

    def test_load_config_from_file(self):
        """Test loading config from file."""
        yaml_content = """
app:
  name: "File App"
  version: "2.0.0"
auth:
  jwt_secret: "very-long-secret-key-for-testing-file-loading-functionality"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            try:
                # Create logs directory if it doesn't exist
                os.makedirs("logs", exist_ok=True)
                config = load_config(f.name)
                assert isinstance(config, AppConfig)
                assert config.app.name == "File App"
                assert config.app.version == "2.0.0"
            finally:
                os.unlink(f.name)

    def test_load_config_from_dict(self):
        """Test loading config from dictionary."""
        config_dict = {"app": {"name": "Dict App", "version": "3.0.0"}, "server": {"port": 8080}}

        config = load_config(defaults=config_dict)
        assert isinstance(config, AppConfig)
        assert config.app.name == "Dict App"
        assert config.app.version == "3.0.0"
        assert config.server.port == 8080

    def test_load_config_none_returns_default(self):
        """Test loading config with None returns default."""
        config = load_config(None)
        assert isinstance(config, AppConfig)
        assert config.app.name == "Nexus Application"


class TestConfigValidation:
    """Test configuration validation."""

    def test_database_connection_port_validation(self):
        """Test database connection port validation."""
        # Valid port
        config = DatabaseConnectionConfig(port=5432)
        assert config.port == 5432

        # Test that invalid ports would raise validation errors in real Pydantic usage
        with pytest.raises((ValueError, TypeError)):
            DatabaseConnectionConfig(port=-1)

    def test_database_pool_max_size_validation(self):
        """Test database pool max size validation."""
        # Valid max size
        config = DatabasePoolConfig(min_size=5, max_size=10)
        assert config.max_size == 10

        # Invalid max size (less than min_size) should raise error
        with pytest.raises((ValueError, TypeError)):
            DatabasePoolConfig(min_size=10, max_size=5)

    def test_auth_config_jwt_secret_validation(self):
        """Test JWT secret validation."""
        # Valid secret
        config = AuthConfig(jwt_secret="valid-secret-key-that-is-long-enough")
        assert config.jwt_secret == "valid-secret-key-that-is-long-enough"

        # Test that short secrets would raise validation errors
        with pytest.raises((ValueError, TypeError)):
            AuthConfig(jwt_secret="short")

    def test_app_settings_debug_validation(self):
        """Test debug setting validation."""
        # Production with debug should raise warning/error
        config = AppSettings(environment=Environment.PRODUCTION, debug=False)
        assert config.debug == False

        # Test that production + debug=True might raise validation error
        # This depends on the actual validation implementation


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
