"""
Common Utilities for Nexus Plugins

This module provides shared utilities that can be used across all plugins
to maintain consistency and reduce code duplication.
"""

from .models import BasePluginModel, PluginResponse, PluginError
from .auth import AuthHelper, require_auth, get_current_user
from .validators import validate_email, validate_username, sanitize_input
from .decorators import log_execution, handle_errors, cache_result
from .database import DatabaseHelper, get_db_connection

__all__ = [
    # Models
    "BasePluginModel",
    "PluginResponse",
    "PluginError",
    # Auth
    "AuthHelper",
    "require_auth",
    "get_current_user",
    # Validators
    "validate_email",
    "validate_username",
    "sanitize_input",
    # Decorators
    "log_execution",
    "handle_errors",
    "cache_result",
    # Database
    "DatabaseHelper",
    "get_db_connection",
]
