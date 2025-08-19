"""
Nexus - The Ultimate Plugin-Based Application Platform.

A cutting-edge, plugin-based application platform that enables developers to
create highly modular, maintainable, and scalable applications.
"""

# Version declaration
__version__: str

try:
    import importlib.metadata as importlib_metadata

    __version__ = importlib_metadata.version("nexus-platform")
except Exception:
    # Fallback for development
    __version__ = "0.1.6-dev"

__author__ = "Nexus Team"
__license__ = "MIT"

# Core imports
from .app import NexusApp
from .config import AppConfig, create_default_config, load_config
from .core import (
    DatabaseAdapter,
    Event,
    EventBus,
    EventPriority,
    PluginInfo,
    PluginManager,
    PluginStatus,
    ServiceRegistry,
)
from .database import DatabaseConfig, create_database_adapter, create_default_database_config
from .factory import create_nexus_app, create_plugin
from .hot_reload import HotReloadManager, create_hot_reload_manager
from .plugins import (
    BasePlugin,
    PluginContext,
    PluginLifecycle,
    PluginMetadata,
    plugin_hook,
    requires_dependency,
    requires_permission,
)

# Export main classes and functions
__all__ = [
    # Version info
    "__version__",
    "__author__",
    "__license__",
    # Core classes
    "NexusApp",
    "BasePlugin",
    "PluginMetadata",
    "PluginLifecycle",
    "PluginContext",
    "PluginManager",
    "EventBus",
    "ServiceRegistry",
    "DatabaseAdapter",
    "DatabaseConfig",
    # Configuration
    "AppConfig",
    "create_default_config",
    "load_config",
    # Hot reload
    "HotReloadManager",
    "create_hot_reload_manager",
    # Database
    "create_database_adapter",
    "create_default_database_config",
    # Decorators and utilities
    "plugin_hook",
    "requires_permission",
    "requires_dependency",
    # Factory functions (framework entry points)
    "create_nexus_app",
    "create_plugin",
    "create_api_app",
    "create_microservice",
    "create_web_app",
    # Events
    "Event",
    "EventPriority",
    # Plugin info
    "PluginInfo",
    "PluginStatus",
]

# Import convenience factory functions for easy access
from .factory import create_api_app, create_microservice, create_web_app
