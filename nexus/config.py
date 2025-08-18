"""
Configuration management module for Nexus Framework.

This module provides comprehensive configuration management including:
- Loading from multiple formats (YAML, JSON, TOML)
- Environment variable substitution
- Configuration validation
- Default values and merging
"""

import json
import logging
import os
import re
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import toml
import yaml
from pydantic import BaseModel, Field, validator

logger = logging.getLogger(__name__)


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"
    TESTING = "testing"


# Security constants
DEFAULT_JWT_SECRET = "change-me-in-production"


class DatabaseType(str, Enum):
    """Database types supported by the framework."""

    POSTGRESQL = "postgresql"
    MYSQL = "mysql"
    MONGODB = "mongodb"
    SQLITE = "sqlite"
    REDIS = "redis"


class LogLevel(str, Enum):
    """Logging levels."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Pydantic models for configuration validation


class CORSConfig(BaseModel):
    """CORS configuration."""

    enabled: bool = True
    origins: List[str] = ["*"]
    methods: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"]
    headers: List[str] = ["*"]
    credentials: bool = True
    max_age: int = 3600


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = "0.0.0.0"  # nosec B104 - Framework default, should be configured in production
    port: int = Field(8000, ge=1, le=65535)
    workers: int = Field(1, ge=1)
    reload: bool = False
    access_log: bool = True
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None


class DatabaseConnectionConfig(BaseModel):
    """Database connection configuration."""

    host: str = "localhost"
    port: int = Field(5432, ge=1, le=65535)
    database: str = "nexus_db"
    username: Optional[str] = None
    password: Optional[str] = None

    # SQLite specific
    path: Optional[str] = None

    # MongoDB specific
    replica_set: Optional[str] = None
    auth_source: Optional[str] = "admin"

    @validator("port")
    def validate_port_for_type(cls, v: int, values: Dict[str, Any]) -> int:
        """Set default ports based on database type."""
        return v


class DatabasePoolConfig(BaseModel):
    """Database connection pool configuration."""

    min_size: int = Field(10, ge=1)
    max_size: int = Field(20, ge=1)
    max_overflow: int = Field(10, ge=0)
    pool_timeout: int = Field(30, ge=1)
    pool_recycle: int = Field(3600, ge=60)
    pool_pre_ping: bool = True

    @validator("max_size")
    def validate_max_size(cls, v: int, values: Dict[str, Any]) -> int:
        """Ensure max_size is greater than min_size."""
        min_size = values.get("min_size", 10)
        if v < min_size:
            raise ValueError(f"max_size ({v}) must be >= min_size ({min_size})")
        return v


class DatabaseConfig(BaseModel):
    """Complete database configuration."""

    type: DatabaseType = DatabaseType.POSTGRESQL
    connection: DatabaseConnectionConfig = Field(default_factory=lambda: DatabaseConnectionConfig())  # type: ignore[call-arg]
    pool: DatabasePoolConfig = Field(default_factory=lambda: DatabasePoolConfig())  # type: ignore[call-arg]
    echo: bool = False
    echo_pool: bool = False

    @validator("connection")
    def set_default_port(
        cls, v: DatabaseConnectionConfig, values: Dict[str, Any]
    ) -> DatabaseConnectionConfig:
        """Set default port based on database type."""
        db_type = values.get("type")
        if db_type and v.port == 5432:  # Default PostgreSQL port
            default_ports = {
                DatabaseType.POSTGRESQL: 5432,
                DatabaseType.MYSQL: 3306,
                DatabaseType.MONGODB: 27017,
                DatabaseType.SQLITE: 0,  # SQLite doesn't use ports
                DatabaseType.REDIS: 6379,
            }
            if db_type in default_ports:
                v.port = default_ports[db_type]
        return v

    def get_connection_url(self) -> str:
        """Generate database connection URL."""
        if self.type == DatabaseType.SQLITE:
            return f"sqlite:///{self.connection.path or ':memory:'}"

        # Build connection string
        if self.connection.username and self.connection.password:
            auth = f"{self.connection.username}:{self.connection.password}@"
        else:
            auth = ""

        if self.type == DatabaseType.MONGODB:
            url = f"mongodb://{auth}{self.connection.host}:{self.connection.port}/{self.connection.database}"
            if self.connection.replica_set:
                url += f"?replicaSet={self.connection.replica_set}"
            if self.connection.auth_source:
                url += f"{'&' if '?' in url else '?'}authSource={self.connection.auth_source}"
            return url

        # PostgreSQL/MySQL
        driver = {
            DatabaseType.POSTGRESQL: "postgresql+asyncpg",
            DatabaseType.MYSQL: "mysql+aiomysql",
        }.get(self.type, str(self.type))

        return f"{driver}://{auth}{self.connection.host}:{self.connection.port}/{self.connection.database}"


class CacheConfig(BaseModel):
    """Cache configuration."""

    type: str = "redis"  # redis, memcached, memory
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    default_ttl: int = 300  # 5 minutes
    max_entries: int = 10000

    def get_redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"


class AuthConfig(BaseModel):
    """Authentication configuration."""

    jwt_secret: str = Field(DEFAULT_JWT_SECRET, min_length=32)
    jwt_algorithm: str = "HS256"
    token_expiry: int = 3600  # 1 hour
    refresh_token_expiry: int = 604800  # 7 days
    session_secret: Optional[str] = None
    session_max_age: int = 86400  # 24 hours
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digits: bool = True
    password_require_special: bool = True
    max_login_attempts: int = 5
    lockout_duration: int = 900  # 15 minutes

    @validator("jwt_secret")
    def validate_jwt_secret(cls, v: str) -> str:
        """Ensure JWT secret is secure in production."""
        if v == "change-me-in-production":
            logger.warning("Using default JWT secret. Please change in production!")
        return v


class SecurityConfig(BaseModel):
    """Security configuration."""

    https_redirect: bool = False
    hsts_enabled: bool = False
    hsts_max_age: int = 31536000  # 1 year
    csrf_enabled: bool = True
    csrf_token_length: int = 32
    rate_limiting_enabled: bool = True
    rate_limit_requests: int = 1000
    rate_limit_window: int = 3600  # 1 hour
    allowed_hosts: List[str] = ["*"]
    trusted_proxies: List[str] = []


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: LogLevel = LogLevel.INFO
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"
    file_enabled: bool = True
    file_path: str = "./logs/nexus.log"
    file_max_size: int = 10485760  # 10MB
    file_backup_count: int = 5
    console_enabled: bool = True
    console_colorize: bool = True

    def configure_logging(self) -> None:
        """Configure Python logging based on settings."""
        import logging.config

        config = {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "default": {
                    "format": self.format,
                    "datefmt": self.date_format,
                },
            },
            "handlers": {},
            "root": {
                "level": self.level.value,
                "handlers": [],
            },
        }

        if self.console_enabled:
            config["handlers"]["console"] = {  # type: ignore
                "class": "logging.StreamHandler",
                "level": self.level.value,
                "formatter": "default",
                "stream": "ext://sys.stdout",
            }
            config["root"]["handlers"].append("console")  # type: ignore

        if self.file_enabled:
            config["handlers"]["file"] = {  # type: ignore
                "class": "logging.handlers.RotatingFileHandler",
                "level": self.level.value,
                "formatter": "default",
                "filename": self.file_path,
                "maxBytes": self.file_max_size,
                "backupCount": self.file_backup_count,
            }
            config["root"]["handlers"].append("file")  # type: ignore

        logging.config.dictConfig(config)


class PluginConfig(BaseModel):
    """Plugin system configuration."""

    directory: str = "./plugins"
    auto_load: bool = True
    hot_reload: bool = False
    lazy_load: bool = False
    scan_interval: int = 60  # seconds
    max_load_time: int = 30  # seconds
    require_manifest: bool = True
    sandbox_enabled: bool = False
    allowed_imports: List[str] = ["*"]


class AppSettings(BaseModel):
    """Main application settings."""

    name: str = "Nexus Application"
    version: str = "1.0.0"
    description: str = "A Nexus Framework application"
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    testing: bool = False
    timezone: str = "UTC"
    locale: str = "en_US"

    @validator("debug")
    def validate_debug(cls, v: bool, values: Dict[str, Any]) -> bool:
        """Ensure debug is off in production."""
        env = values.get("environment")
        if env == Environment.PRODUCTION and v:
            logger.warning("Debug mode enabled in production!")
        return v


class AppConfig(BaseModel):
    """Complete application configuration."""

    app: AppSettings = Field(default_factory=AppSettings)
    server: ServerConfig = Field(default_factory=lambda: ServerConfig())  # type: ignore[call-arg]
    database: Optional[DatabaseConfig] = Field(default_factory=DatabaseConfig)
    cache: Optional[CacheConfig] = Field(default_factory=CacheConfig)
    auth: AuthConfig = Field(default_factory=lambda: AuthConfig())  # type: ignore[call-arg]
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    plugins: PluginConfig = Field(default_factory=PluginConfig)
    cors: CORSConfig = Field(default_factory=CORSConfig)

    # Custom configuration sections
    custom: Dict[str, Any] = {}

    class Config:
        """Pydantic configuration."""

        use_enum_values = True
        validate_assignment = True

    def merge(self, other: "AppConfig") -> "AppConfig":
        """Merge with another configuration."""
        merged_dict = self.dict()
        other_dict = other.dict()

        def deep_merge(d1: Dict[str, Any], d2: Dict[str, Any]) -> Dict[str, Any]:
            """Recursively merge two dictionaries."""
            result = d1.copy()
            for key, value in d2.items():
                if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result

        merged = deep_merge(merged_dict, other_dict)
        return AppConfig(**merged)


class ConfigLoader:
    """Configuration loader with environment variable substitution."""

    ENV_VAR_PATTERN = re.compile(r"\$\{([^}:]+)(?::([^}]*))?\}")

    @classmethod
    def load_file(cls, path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from file."""
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"Configuration file not found: {path}")

        # Determine file type and load
        if path.suffix in [".yaml", ".yml"]:
            with open(path) as f:
                data = yaml.safe_load(f)
        elif path.suffix == ".json":
            with open(path) as f:
                data = json.load(f)
        elif path.suffix == ".toml":
            with open(path) as f:
                data = toml.load(f)
        else:
            raise ValueError(f"Unsupported configuration file type: {path.suffix}")

        # Substitute environment variables
        return cls._substitute_env_vars(data)  # type: ignore

    @classmethod
    def _substitute_env_vars(cls, data: Any) -> Any:
        """Recursively substitute environment variables."""
        if isinstance(data, dict):
            return {k: cls._substitute_env_vars(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [cls._substitute_env_vars(item) for item in data]
        elif isinstance(data, str):

            def replacer(match: Any) -> str:
                var_name = match.group(1)
                default_value = match.group(2)
                value = os.environ.get(var_name)
                if value is None:
                    if default_value is not None:
                        return str(default_value)
                    raise ValueError(
                        f"Environment variable {var_name} not set and no default provided"
                    )
                return value

            return cls.ENV_VAR_PATTERN.sub(replacer, data)
        else:
            return data

    @classmethod
    def load_from_env(cls, prefix: str = "NEXUS") -> Dict[str, Any]:
        """Load configuration from environment variables."""
        config: Dict[str, Any] = {}
        prefix = f"{prefix}_"

        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Remove prefix and convert to lowercase
                config_key = key[len(prefix) :].lower()

                # Convert underscores to nested dict notation
                parts = config_key.split("__")
                current = config

                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]

                # Try to parse value as JSON
                try:
                    current[parts[-1]] = json.loads(value)
                except json.JSONDecodeError:
                    # If not JSON, treat as string
                    current[parts[-1]] = value

        return config


def load_config(
    path: Optional[Union[str, Path]] = None,
    env_prefix: str = "NEXUS",
    defaults: Optional[Dict[str, Any]] = None,
) -> AppConfig:
    """
    Load configuration from multiple sources.

    Args:
        path: Path to configuration file
        env_prefix: Prefix for environment variables
        defaults: Default configuration values

    Returns:
        Loaded and validated AppConfig

    Example:
        >>> config = load_config("config.yaml")
        >>> config = load_config(env_prefix="MYAPP")
    """
    config_dict = defaults or {}

    # Load from file if provided
    if path:
        file_config = ConfigLoader.load_file(path)
        config_dict = deep_merge(config_dict, file_config)

    # Load from environment variables
    env_config = ConfigLoader.load_from_env(env_prefix)
    if env_config:
        config_dict = deep_merge(config_dict, env_config)

    # Create and validate configuration
    config = AppConfig(**config_dict)

    # Configure logging
    config.logging.configure_logging()

    logger.info(f"Configuration loaded for environment: {config.app.environment}")

    return config


def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value

    return result


def create_default_config() -> AppConfig:
    """Create default configuration."""
    return AppConfig()


# Example configuration templates

DEVELOPMENT_CONFIG = {
    "app": {
        "environment": "development",
        "debug": True,
    },
    "server": {
        "reload": True,
    },
    "database": {
        "type": "sqlite",
        "connection": {"path": "./dev.db"},
        "echo": True,
    },
    "logging": {
        "level": "DEBUG",
    },
    "plugins": {
        "hot_reload": True,
    },
}

PRODUCTION_CONFIG = {
    "app": {
        "environment": "production",
        "debug": False,
    },
    "server": {
        "workers": 4,
        "reload": False,
    },
    "database": {
        "type": "postgresql",
        "pool": {
            "min_size": 20,
            "max_size": 100,
        },
        "echo": False,
    },
    "security": {
        "https_redirect": True,
        "hsts_enabled": True,
        "rate_limiting_enabled": True,
    },
    "logging": {
        "level": "WARNING",
    },
    "plugins": {
        "hot_reload": False,
    },
}

TESTING_CONFIG = {
    "app": {
        "environment": "testing",
        "testing": True,
    },
    "database": {
        "type": "sqlite",
        "connection": {"path": ":memory:"},
    },
    "auth": {
        "jwt_secret": "test-secret-key-for-testing-only",
    },
    "logging": {
        "level": "DEBUG",
        "file_enabled": False,
    },
}


# Database configuration examples
DATABASE_EXAMPLES = {
    "sqlite": {"type": "sqlite", "connection": {"path": "./nexus.db"}},
    "postgresql": {
        "type": "postgresql",
        "connection": {
            "host": "localhost",
            "port": 5432,
            "database": "nexus",
            "username": "nexus_user",
            "password": "nexus_password",
        },
        "pool_size": 20,
        "max_overflow": 30,
    },
    "mariadb": {
        "type": "mysql",
        "connection": {
            "host": "localhost",
            "port": 3306,
            "database": "nexus",
            "username": "nexus_user",
            "password": "nexus_password",
        },
        "pool_size": 20,
        "max_overflow": 30,
    },
    "mongodb": {
        "type": "mongodb",
        "connection": {
            "host": "localhost",
            "port": 27017,
            "database": "nexus",
            "username": "nexus_user",
            "password": "nexus_password",
        },
        "replica_set": None,
        "auth_source": "admin",
    },
}


def create_database_config_from_url(url: str) -> DatabaseConfig:
    """Create database configuration from connection URL."""
    if url.startswith("sqlite"):
        return DatabaseConfig(type=DatabaseType.SQLITE)
    elif url.startswith("postgresql"):
        return DatabaseConfig(type=DatabaseType.POSTGRESQL)
    elif url.startswith("mysql"):
        return DatabaseConfig(type=DatabaseType.MYSQL)
    elif url.startswith("mongodb"):
        return DatabaseConfig(type=DatabaseType.MONGODB)
    else:
        raise ValueError(f"Unsupported database URL: {url}")


class ConfigurationManager:
    """Configuration manager for runtime configuration operations."""

    def __init__(self, config: AppConfig):
        self.config = config
        self._watchers: List[Any] = []

    def get_config(self, section: Optional[str] = None) -> Dict[str, Any]:
        """Get configuration data."""
        config_dict = self.config.dict()

        if section:
            if section in config_dict:
                return {section: config_dict[section]}
            else:
                raise KeyError(f"Configuration section '{section}' not found")

        return config_dict

    def update_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """Update configuration values."""
        updated_keys = []
        restart_required = False

        for key, value in updates.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)
                updated_keys.append(key)

                # Check if restart is required for certain keys
                if key in ["server", "database", "plugins"]:
                    restart_required = True
            else:
                # Handle nested updates
                if "." in key:
                    section, field = key.split(".", 1)
                    if hasattr(self.config, section):
                        section_obj = getattr(self.config, section)
                        if hasattr(section_obj, field):
                            setattr(section_obj, field, value)
                            updated_keys.append(key)
                            restart_required = True

        return {"updated_keys": updated_keys, "restart_required": restart_required}

    def mask_secrets(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive configuration values."""
        masked = data.copy()

        secret_keys = ["password", "secret", "key", "token", "api_key"]

        def _mask_recursive(obj: Any) -> None:
            if isinstance(obj, dict):
                for k, v in obj.items():
                    if any(secret in k.lower() for secret in secret_keys):
                        obj[k] = "***"
                    else:
                        _mask_recursive(v)
            elif isinstance(obj, list):
                for item in obj:
                    _mask_recursive(item)

        _mask_recursive(masked)
        return masked

    def validate_config(self) -> List[str]:
        """Validate current configuration and return any errors."""
        errors = []

        # Basic validation
        if self.config.app.environment == Environment.PRODUCTION:
            if self.config.app.debug:
                errors.append("Debug mode should be disabled in production")
            if self.config.auth.jwt_secret == DEFAULT_JWT_SECRET:
                errors.append("JWT secret must be changed in production")

        return errors

    def reload_from_file(self, path: Union[str, Path]) -> None:
        """Reload configuration from file."""
        new_config_data = ConfigLoader.load_file(path)
        self.config = AppConfig(**new_config_data)

        # Notify watchers
        for callback in self._watchers:
            try:
                callback(self.config)
            except Exception as e:
                logger.warning(f"Error notifying config watcher: {e}")

    def add_watcher(self, callback: Any) -> None:
        """Add a configuration change watcher."""
        self._watchers.append(callback)

    def remove_watcher(self, callback: Any) -> None:
        """Remove a configuration change watcher."""
        if callback in self._watchers:
            self._watchers.remove(callback)
