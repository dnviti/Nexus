"""
Nexus Framework Utilities Module
Common utility functions and helpers.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


def setup_logging(
    level: str = "INFO",
    format_string: Optional[str] = None,
    log_file: Optional[str] = None,
    enable_json: bool = False,
) -> None:
    """Setup application logging configuration."""

    # Default format
    if format_string is None:
        if enable_json:
            format_string = "%(message)s"
        else:
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    # Configure root logger
    logging.basicConfig(level=getattr(logging, level.upper()), format=format_string, handlers=[])

    # Create formatters
    if enable_json:
        formatter: logging.Formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logging.getLogger().addHandler(console_handler)

    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)

    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)
    logging.getLogger("nexus").setLevel(logging.DEBUG)


class JsonFormatter(logging.Formatter):
    """JSON log formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in [
                "name",
                "msg",
                "args",
                "levelname",
                "levelno",
                "pathname",
                "filename",
                "module",
                "lineno",
                "funcName",
                "created",
                "msecs",
                "relativeCreated",
                "thread",
                "threadName",
                "processName",
                "process",
                "exc_info",
                "exc_text",
                "stack_info",
            ]:
                log_entry[key] = value

        return json.dumps(log_entry, default=str)


def load_config_file(file_path: str) -> Dict[str, Any]:
    """Load configuration from YAML or JSON file."""
    path_obj = Path(file_path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Configuration file not found: {path_obj}")

    with open(path_obj, "r") as f:
        if path_obj.suffix.lower() in [".yaml", ".yml"]:
            return yaml.safe_load(f) or {}
        elif path_obj.suffix.lower() == ".json":
            return json.load(f)  # type: ignore
        else:
            raise ValueError(f"Unsupported configuration file format: {path_obj.suffix}")


def save_config_file(config: Dict[str, Any], file_path: str) -> None:
    """Save configuration to YAML or JSON file."""
    path_obj = Path(file_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w") as f:
        if path_obj.suffix.lower() in [".yaml", ".yml"]:
            yaml.dump(config, f, default_flow_style=False)
        elif path_obj.suffix.lower() == ".json":
            json.dump(config, f, indent=2)
        else:
            raise ValueError(f"Unsupported configuration file format: {path_obj.suffix}")


def get_env_var(name: str, default: Any = None, required: bool = False) -> Any:
    """Get environment variable with optional default and validation."""
    value = os.getenv(name, default)

    if required and value is None:
        raise ValueError(f"Required environment variable '{name}' is not set")

    # Type conversion for common types
    if isinstance(value, str):
        # Boolean conversion
        if value.lower() in ["true", "false"]:
            return value.lower() == "true"

        # Integer conversion
        if value.isdigit():
            return int(value)

        # Float conversion
        try:
            return float(value)
        except ValueError:
            pass

    return value


def ensure_directory(path: str) -> Path:
    """Ensure directory exists, create if it doesn't."""
    dir_path = Path(path)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_project_root() -> Path:
    """Get the project root directory."""
    return Path(__file__).parent.parent.parent


def get_app_root() -> Path:
    """Get the application root directory."""
    return Path(__file__).parent.parent


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human readable format."""
    value = float(bytes_value)
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if value < 1024.0:
            return f"{value:.1f} {unit}"
        value /= 1024.0
    return f"{value:.1f} PB"


def format_duration(seconds: float) -> str:
    """Format duration in seconds to human readable format."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.1f}h"
    else:
        days = seconds / 86400
        return f"{days:.1f}d"


def sanitize_string(value: Any, max_length: int = 100) -> str:
    """Sanitize string for safe usage."""
    import re

    if value is None:
        return ""
    if not isinstance(value, str):
        return str(value)

    # Remove HTML tags but keep content
    sanitized = re.sub(r"<[^>]+>", "", value)

    # Normalize whitespace (replace tabs/newlines with spaces, collapse multiple spaces)
    sanitized = re.sub(r"\s+", " ", sanitized)

    # Trim whitespace from beginning and end
    sanitized = sanitized.strip()

    # Remove control characters
    sanitized = "".join(char for char in sanitized if ord(char) >= 32)

    # Truncate if too long
    if len(sanitized) > max_length:
        sanitized = sanitized[: max_length - 3] + "..."

    return sanitized


def deep_merge_dicts(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()

    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value

    return result


def validate_email(email: str) -> bool:
    """Basic email validation."""
    import re

    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def generate_id(prefix: str = "", length: int = 8) -> str:
    """Generate a random ID with optional prefix."""
    import secrets
    import string

    chars = string.ascii_lowercase + string.digits

    random_part = "".join(secrets.choice(chars) for _ in range(length))

    if prefix:
        return f"{prefix}_{random_part}"
    return random_part


def generate_random_string(length: int = 32) -> str:
    """Generate a random string of specified length."""
    import secrets
    import string

    chars = string.ascii_lowercase + string.digits

    return "".join(secrets.choice(chars) for _ in range(length))


def format_file_size(size_bytes: int) -> str:
    """Format file size into human readable format."""
    return format_bytes(size_bytes)


def validate_config(config: Dict[str, Any]) -> bool:
    """Validate configuration object."""
    if config is None:
        return False
    if not isinstance(config, dict):
        return False
    if "app" in config and config["app"] is None:
        return False
    return True


def merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries."""
    return deep_merge_dicts(dict1, dict2)


def safe_import(module_name: str, fallback: Any = None) -> Any:
    """Safely import a module, return fallback if import fails."""
    try:
        return __import__(module_name)
    except ImportError:
        return fallback


def get_environment_var(name: str, default: Optional[str] = None) -> Optional[str]:
    """Get environment variable with default."""
    return os.getenv(name, default)


def is_valid_email(email: str) -> bool:
    """Validate email address."""
    return validate_email(email)


def create_directory_if_not_exists(path: str) -> None:
    """Create directory if it doesn't exist."""
    ensure_directory(path)


def get_file_modification_time(file_path: str) -> Optional[float]:
    """Get file modification time."""
    try:
        return os.path.getmtime(file_path)
    except (OSError, FileNotFoundError):
        return None


__all__ = [
    "setup_logging",
    "JsonFormatter",
    "load_config_file",
    "save_config_file",
    "get_env_var",
    "ensure_directory",
    "get_project_root",
    "get_app_root",
    "format_bytes",
    "format_duration",
    "sanitize_string",
    "deep_merge_dicts",
    "validate_email",
    "generate_id",
    "generate_random_string",
    "format_file_size",
    "validate_config",
    "merge_dicts",
    "safe_import",
    "get_environment_var",
    "is_valid_email",
    "create_directory_if_not_exists",
    "get_file_modification_time",
]
