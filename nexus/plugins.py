"""
Nexus Framework Plugin System
Base classes and interfaces for plugin development.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type

from fastapi import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# Plugin Metadata
class PluginMetadata(BaseModel):
    """Plugin metadata and configuration."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    email: str = ""
    license: str = "MIT"
    homepage: str = ""
    repository: str = ""
    documentation: str = ""
    tags: List[str] = Field(default_factory=list)
    category: str = "general"
    dependencies: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    min_nexus_version: str = "1.0.0"
    max_nexus_version: Optional[str] = None
    enabled: bool = True
    config_schema: Dict[str, Any] = Field(default_factory=dict)


# Plugin Lifecycle
class PluginLifecycle(Enum):
    """Plugin lifecycle states."""

    INITIALIZING = "initializing"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


# Plugin Context
class PluginContext:
    """Plugin execution context."""

    def __init__(self, app_config: Dict[str, Any], service_registry: Any, event_bus: Any):
        self.app_config = app_config
        self.service_registry = service_registry
        self.event_bus = event_bus
        self.logger = logging.getLogger(__name__)

    def get_service(self, name: str) -> Any:
        """Get a service by name."""
        return self.service_registry.get(name)

    def get_config(
        self, plugin_name: str, default: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self.app_config.get("plugins", {}).get(plugin_name, default or {})  # type: ignore


# Plugin Dependency
class PluginDependency(BaseModel):
    """Plugin dependency specification."""

    name: str
    version: str = "*"
    optional: bool = False


# Plugin Permission
class PluginPermission(BaseModel):
    """Plugin permission specification."""

    name: str
    description: str = ""
    required: bool = True


# Plugin Hook
class PluginHook:
    """Plugin hook for event handling."""

    def __init__(self, name: str, priority: int = 0):
        self.name = name
        self.priority = priority


# Plugin Configuration Schema
class PluginConfigSchema(BaseModel):
    """Plugin configuration schema."""

    schema: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


# Plugin Decorators
def plugin_hook(
    name: str, priority: int = 0
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for plugin hook methods."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "_nexus_hook", name)
        setattr(func, "_nexus_priority", priority)
        return func

    return decorator


def requires_permission(permission: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for methods requiring permissions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "_required_permission", permission)
        return func

    return decorator


def requires_dependency(
    dependency: str, version: Optional[str] = None
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator for methods requiring dependencies."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        setattr(func, "_required_dependency", dependency)
        if version:
            setattr(func, "_dependency_version", version)
        return func

    return decorator


# Plugin Health Status
class HealthStatus(BaseModel):
    """Plugin health status."""

    healthy: bool = True
    message: str = "Plugin is running"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    components: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    metrics: Dict[str, float] = Field(default_factory=dict)


# Plugin Exceptions
class PluginError(Exception):
    """Base exception for plugin errors."""

    pass


class PluginInitializationError(PluginError):
    """Plugin initialization failed."""

    pass


class PluginConfigurationError(PluginError):
    """Plugin configuration error."""

    pass


class PluginDependencyError(PluginError):
    """Plugin dependency not satisfied."""

    pass


# Base Plugin Class
class BasePlugin(ABC):
    """
    Base class for all Nexus Framework plugins.

    All plugins must inherit from this class and implement the required abstract methods.
    """

    def __init__(self) -> None:
        """Initialize the base plugin."""
        # Plugin metadata
        self.name: str = ""
        self.category: str = ""
        self.version: str = "1.0.0"
        self.description: str = ""
        self.author: str = ""
        self.license: str = "MIT"

        # Plugin state
        self.enabled: bool = True
        self.initialized: bool = False
        self.config: Dict[str, Any] = {}

        # Dependencies injected by framework
        self.db_adapter = None
        self.event_bus = None
        self.service_registry = None
        self.cache_manager = None

        # Plugin resources
        self.logger = logging.getLogger(f"nexus.plugins.{self.category}.{self.name}")
        self._background_tasks: List[Any] = []
        self._event_subscriptions: Dict[str, Any] = {}
        self._registered_services: Set[str] = set()

        # Timing
        self._startup_time: Optional[datetime] = None
        self._shutdown_time: Optional[datetime] = None

    @abstractmethod
    async def initialize(self) -> bool:
        """
        Initialize the plugin.

        This method is called when the plugin is loaded. It should:
        - Validate configuration
        - Set up resources
        - Register event handlers
        - Initialize services

        Returns:
            bool: True if initialization was successful, False otherwise.

        Raises:
            PluginInitializationError: If initialization fails critically.
        """
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """
        Cleanup plugin resources.

        This method is called when the plugin is unloaded. It should:
        - Close connections
        - Cancel background tasks
        - Unregister services
        - Clean up resources

        Raises:
            PluginError: If shutdown fails.
        """
        pass

    @abstractmethod
    def get_api_routes(self) -> List[APIRouter]:
        """
        Return API routes for this plugin.

        Returns:
            List[APIRouter]: List of FastAPI routers defining the plugin's API endpoints.
        """
        pass

    @abstractmethod
    def get_database_schema(self) -> Dict[str, Any]:
        """
        Return the database schema for this plugin.

        This defines the structure of data that the plugin will store.

        Returns:
            Dict[str, Any]: Database schema definition.

        Example:
            {
                "collections": {
                    "items": {
                        "indexes": [{"field": "name", "unique": True}]
                    }
                },
                "initial_data": {
                    "settings": {"key": "value"}
                }
            }
        """
        pass

    async def health_check(self) -> HealthStatus:
        """
        Check plugin health status.

        Override this method to implement custom health checks.

        Returns:
            HealthStatus: Current health status of the plugin.
        """
        return HealthStatus(
            healthy=self.initialized,
            message="Plugin is running" if self.initialized else "Plugin not initialized",
            components={
                "database": {"status": "connected" if self.db_adapter else "disconnected"},
                "events": {"subscriptions": len(self._event_subscriptions)},
            },
        )

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate plugin configuration.

        Override this method to implement custom configuration validation.

        Args:
            config: Configuration dictionary to validate.

        Returns:
            bool: True if configuration is valid, False otherwise.
        """
        return True

    def get_info(self) -> Dict[str, Any]:
        """
        Get plugin information.

        Returns:
            Dict[str, Any]: Plugin metadata and status.
        """
        return {
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "license": self.license,
            "enabled": self.enabled,
            "initialized": self.initialized,
            "status": "running" if self.initialized else "stopped",
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
            "uptime": (
                (datetime.utcnow() - self._startup_time).total_seconds()
                if self._startup_time
                else 0
            ),
        }

    def get_metrics(self) -> Dict[str, float]:
        """
        Get plugin metrics.

        Override this method to provide custom metrics.

        Returns:
            Dict[str, float]: Plugin metrics.
        """
        return {
            "uptime": (
                (datetime.utcnow() - self._startup_time).total_seconds()
                if self._startup_time
                else 0
            ),
            "memory_usage": 0.0,  # Placeholder - would need psutil for real memory usage
            "event_subscriptions": len(self._event_subscriptions),
            "background_tasks": len(self._background_tasks),
            "registered_services": len(self._registered_services),
        }

    # Helper methods for plugin developers
    async def publish_event(self, event_name: str, data: Dict[str, Any]) -> None:
        """
        Publish an event to the event bus.

        Args:
            event_name: Name of the event.
            data: Event data.
        """
        if self.event_bus:
            await self.event_bus.publish(event_name, data, source=f"{self.category}.{self.name}")

    async def subscribe_to_event(self, event_name: str, handler: Any) -> None:
        """
        Subscribe to an event.

        Args:
            event_name: Name of the event to subscribe to.
            handler: Event handler function.
        """
        if self.event_bus:
            self.event_bus.subscribe(event_name, handler)
            self._event_subscriptions[event_name] = handler

    async def unsubscribe_from_event(self, event_name: str, handler: Any) -> None:
        """
        Unsubscribe from an event.

        Args:
            event_name: Name of the event to unsubscribe from.
            handler: Event handler function to unsubscribe.
        """
        if self.event_bus:
            self.event_bus.unsubscribe(event_name, handler)
        if event_name in self._event_subscriptions:
            del self._event_subscriptions[event_name]

    def register_service(self, name: str, service: Any) -> None:
        """
        Register a service with the service registry.

        Args:
            name: Service name.
            service: Service instance.
        """
        if self.service_registry:
            self.service_registry.register(name, service)
            self._registered_services.add(name)

    def get_service(self, name: str) -> Optional[Any]:
        """
        Get a service from the registry.

        Args:
            name: Service name.

        Returns:
            Service instance or None if not found.
        """
        if self.service_registry:
            return self.service_registry.get(name)
        return None

    async def get_config(self, key: str, default: Any = None) -> Any:
        """
        Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if key not found.

        Returns:
            Configuration value.
        """
        if self.db_adapter:
            import json
            try:
                result = await self.db_adapter.get(key)
                if result:
                    return json.loads(result)
            except Exception:
                pass
        return self.config.get(key, default)

    async def set_config(self, key: str, value: Any) -> None:
        """
        Set a configuration value.

        Args:
            key: Configuration key.
            value: Configuration value.
        """
        self.config[key] = value

        # Persist to database
        if self.db_adapter:
            config_key = f"plugins.{self.category}.{self.name}.config.{key}"
            await self.db_adapter.set(config_key, value)

    async def get_data(self, key: str, default: Any = None) -> Any:
        """
        Get plugin data from database.

        Args:
            key: Data key.
            default: Default value if key not found.

        Returns:
            Data value.
        """
        if self.db_adapter:
            full_key = f"plugin:{self.name}:{key}"
            return await self.db_adapter.get(full_key)
        return default

    async def set_data(self, key: str, value: Any) -> None:
        """
        Set plugin data in database.

        Args:
            key: Data key.
            value: Data value.
        """
        if self.db_adapter:
            full_key = f"plugin:{self.name}:{key}"
            await self.db_adapter.set(full_key, value)


# Plugin Category Interfaces
class BusinessPlugin(BasePlugin):
    """Base class for business logic plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "business"

    async def initialize(self) -> bool:
        """Initialize the business plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the business plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the business plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the business plugin."""
        return {}


class IntegrationPlugin(BasePlugin):
    """Base class for integration plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "integration"

    async def initialize(self) -> bool:
        """Initialize the integration plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the integration plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the integration plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the integration plugin."""
        return {}

    async def test_connection(self) -> bool:
        """Test connection to external service."""
        return False


class AnalyticsPlugin(BasePlugin):
    """Base class for analytics plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "analytics"

    async def initialize(self) -> bool:
        """Initialize the analytics plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the analytics plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the analytics plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the analytics plugin."""
        return {}

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect analytics metrics."""
        return {}

    async def generate_report(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate analytics report."""
        return {}


class SecurityPlugin(BasePlugin):
    """Base class for security plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "security"

    async def initialize(self) -> bool:
        """Initialize the security plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the security plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the security plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the security plugin."""
        return {}

    async def validate_request(self, request: Any) -> bool:
        """Validate a request for security concerns."""
        return True

    async def audit_log(self, action: str, event: Dict[str, Any]) -> None:
        """Log security audit event."""
        pass


class UIPlugin(BasePlugin):
    """Base class for UI plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "ui"

    async def initialize(self) -> bool:
        """Initialize the UI plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the UI plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the UI plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the UI plugin."""
        return {}

    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Get UI components provided by this plugin."""
        return []

    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Get menu items for the UI."""
        return []


class NotificationPlugin(BasePlugin):
    """Base class for notification plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "notification"

    async def initialize(self) -> bool:
        """Initialize the notification plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the notification plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the notification plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the notification plugin."""
        return {}

    async def send_notification(
        self, recipient: str, subject: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a notification."""
        return False


class StoragePlugin(BasePlugin):
    """Base class for storage plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "storage"

    async def initialize(self) -> bool:
        """Initialize the storage plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the storage plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the storage plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the storage plugin."""
        return {}

    async def store(self, key: str, data: bytes) -> str:
        """Store data and return identifier."""
        return ""

    async def retrieve(self, identifier: str) -> Optional[bytes]:
        """Retrieve stored data."""
        return None

    async def delete(self, identifier: str) -> bool:
        """Delete stored data."""
        return False


class WorkflowPlugin(BasePlugin):
    """Base class for workflow automation plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "workflow"

    async def initialize(self) -> bool:
        """Initialize the workflow plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the workflow plugin."""
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the workflow plugin."""
        return []

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the workflow plugin."""
        return {}

    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any]) -> None:
        """Execute a workflow."""
        return None

    async def get_workflow_status(self, execution_id: str) -> str:
        """Get workflow execution status."""
        return "unknown"


# Plugin Utilities
class PluginValidator:
    """Validates plugin implementations."""

    @staticmethod
    def validate_plugin(plugin: BasePlugin) -> bool:
        """
        Validate that a plugin properly implements the plugin interface.

        Args:
            plugin: Plugin instance to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        # Check if plugin has a valid name
        if not hasattr(plugin, 'name') or not plugin.name or plugin.name.strip() == "":
            logger.error("Plugin has invalid or empty name")
            return False

        required_methods = ["initialize", "shutdown", "get_api_routes", "get_database_schema"]

        for method in required_methods:
            if not hasattr(plugin, method):
                logger.error(f"Plugin missing required method: {method}")
                return False

        return True

    @staticmethod
    def validate_manifest(manifest: Dict[str, Any]) -> bool:
        """
        Validate plugin manifest.

        Args:
            manifest: Plugin manifest dictionary.

        Returns:
            bool: True if valid, False otherwise.
        """
        required_fields = ["name", "category", "version", "description"]

        for field in required_fields:
            if field not in manifest:
                logger.error(f"Manifest missing required field: {field}")
                return False

        # Validate category
        valid_categories = [
            "business",
            "integration",
            "analytics",
            "security",
            "ui",
            "notification",
            "storage",
            "workflow",
            "custom",
            "test",
        ]

        if manifest["category"] not in valid_categories:
            logger.error(f"Invalid plugin category: {manifest['category']}")
            return False

        return True


# Export main classes
__all__ = [
    "BasePlugin",
    "BusinessPlugin",
    "IntegrationPlugin",
    "AnalyticsPlugin",
    "SecurityPlugin",
    "UIPlugin",
    "NotificationPlugin",
    "StoragePlugin",
    "WorkflowPlugin",
    "PluginMetadata",
    "PluginLifecycle",
    "PluginContext",
    "PluginDependency",
    "PluginPermission",
    "PluginHook",
    "PluginConfigSchema",
    "plugin_hook",
    "requires_permission",
    "requires_dependency",
    "PluginError",
    "PluginInitializationError",
    "PluginConfigurationError",
    "PluginDependencyError",
    "HealthStatus",
    "PluginValidator",
]
