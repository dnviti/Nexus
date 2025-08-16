"""
Nexus Framework Plugin System
Base classes and interfaces for plugin development.
"""

import logging
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Type

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
    config_schema: Optional[Dict[str, Any]] = None


# Plugin Lifecycle
class PluginLifecycle:
    """Plugin lifecycle states."""
    DISCOVERED = "discovered"
    LOADED = "loaded"
    INITIALIZED = "initialized"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


# Plugin Context
class PluginContext:
    """Plugin execution context."""
    def __init__(self, app_config: Dict[str, Any], services: Dict[str, Any]):
        self.app_config = app_config
        self.services = services
        self.logger = logging.getLogger(__name__)

    def get_service(self, name: str) -> Any:
        """Get a service by name."""
        return self.services.get(name)

    def get_config(self, plugin_name: str, default: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get plugin configuration."""
        return self.app_config.get("plugins", {}).get(plugin_name, default or {})


# Plugin Dependency
class PluginDependency(BaseModel):
    """Plugin dependency specification."""
    name: str
    version: Optional[str] = None
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
    def __init__(self, event_name: str, priority: int = 0):
        self.event_name = event_name
        self.priority = priority


# Plugin Configuration Schema
class PluginConfigSchema(BaseModel):
    """Plugin configuration schema."""
    type: str = "object"
    properties: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)
    additionalProperties: bool = True


# Plugin Decorators
def plugin_hook(event_name: str, priority: int = 0):
    """Decorator for plugin hook methods."""
    def decorator(func):
        func._plugin_hook = PluginHook(event_name, priority)
        return func
    return decorator


def requires_permission(permission: str):
    """Decorator for methods requiring permissions."""
    def decorator(func):
        func._required_permission = permission
        return func
    return decorator


def requires_dependency(dependency: str, version: Optional[str] = None):
    """Decorator for methods requiring dependencies."""
    def decorator(func):
        func._required_dependency = PluginDependency(name=dependency, version=version)
        return func
    return decorator


# Plugin Health Status
class HealthStatus(BaseModel):
    """Plugin health status."""
    healthy: bool = True
    message: str = "OK"
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

    def __init__(self):
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
                "events": {"subscriptions": len(self._event_subscriptions)}
            }
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
            "startup_time": self._startup_time.isoformat() if self._startup_time else None,
            "uptime": (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0
        }

    def get_metrics(self) -> Dict[str, float]:
        """
        Get plugin metrics.

        Override this method to provide custom metrics.

        Returns:
            Dict[str, float]: Plugin metrics.
        """
        return {
            "uptime_seconds": (datetime.utcnow() - self._startup_time).total_seconds() if self._startup_time else 0,
            "event_subscriptions": len(self._event_subscriptions),
            "background_tasks": len(self._background_tasks),
            "registered_services": len(self._registered_services)
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
            await self.event_bus.publish(
                event_name,
                data,
                source=f"{self.category}.{self.name}"
            )

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

    async def unsubscribe_from_event(self, event_name: str) -> None:
        """
        Unsubscribe from an event.

        Args:
            event_name: Name of the event to unsubscribe from.
        """
        if event_name in self._event_subscriptions:
            if self.event_bus:
                self.event_bus.unsubscribe(event_name, self._event_subscriptions[event_name])
            del self._event_subscriptions[event_name]

    def register_service(self, name: str, service: Any) -> None:
        """
        Register a service with the service registry.

        Args:
            name: Service name.
            service: Service instance.
        """
        if self.service_registry:
            full_name = f"{self.category}.{self.name}.{name}"
            self.service_registry.register(full_name, service)
            self._registered_services.add(full_name)

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
            full_key = f"plugins.{self.category}.{self.name}.data.{key}"
            return await self.db_adapter.get(full_key, default)
        return default

    async def set_data(self, key: str, value: Any) -> None:
        """
        Set plugin data in database.

        Args:
            key: Data key.
            value: Data value.
        """
        if self.db_adapter:
            full_key = f"plugins.{self.category}.{self.name}.data.{key}"
            await self.db_adapter.set(full_key, value)


# Plugin Category Interfaces
class BusinessPlugin(BasePlugin):
    """Base class for business logic plugins."""

    def __init__(self):
        super().__init__()
        self.category = "business"


class IntegrationPlugin(BasePlugin):
    """Base class for integration plugins."""

    def __init__(self):
        super().__init__()
        self.category = "integration"

    @abstractmethod
    async def test_connection(self) -> bool:
        """Test connection to external service."""
        pass


class AnalyticsPlugin(BasePlugin):
    """Base class for analytics plugins."""

    def __init__(self):
        super().__init__()
        self.category = "analytics"

    @abstractmethod
    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect analytics metrics."""
        pass

    @abstractmethod
    async def generate_report(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate analytics report."""
        pass


class SecurityPlugin(BasePlugin):
    """Base class for security plugins."""

    def __init__(self):
        super().__init__()
        self.category = "security"

    @abstractmethod
    async def validate_request(self, request: Any) -> bool:
        """Validate a request for security concerns."""
        pass

    @abstractmethod
    async def audit_log(self, event: Dict[str, Any]) -> None:
        """Log security audit event."""
        pass


class UIPlugin(BasePlugin):
    """Base class for UI plugins."""

    def __init__(self):
        super().__init__()
        self.category = "ui"

    @abstractmethod
    def get_ui_components(self) -> Dict[str, Any]:
        """Get UI components provided by this plugin."""
        pass

    @abstractmethod
    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Get menu items for the UI."""
        pass


class NotificationPlugin(BasePlugin):
    """Base class for notification plugins."""

    def __init__(self):
        super().__init__()
        self.category = "notification"

    @abstractmethod
    async def send_notification(
        self,
        recipient: str,
        subject: str,
        message: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a notification."""
        pass


class StoragePlugin(BasePlugin):
    """Base class for storage plugins."""

    def __init__(self):
        super().__init__()
        self.category = "storage"

    @abstractmethod
    async def store(self, key: str, data: bytes) -> str:
        """Store data and return identifier."""
        pass

    @abstractmethod
    async def retrieve(self, identifier: str) -> bytes:
        """Retrieve stored data."""
        pass

    @abstractmethod
    async def delete(self, identifier: str) -> bool:
        """Delete stored data."""
        pass


class WorkflowPlugin(BasePlugin):
    """Base class for workflow automation plugins."""

    def __init__(self):
        super().__init__()
        self.category = "workflow"

    @abstractmethod
    async def execute_workflow(
        self,
        workflow_id: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a workflow."""
        pass

    @abstractmethod
    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get workflow execution status."""
        pass


# Plugin Utilities
class PluginValidator:
    """Validates plugin implementations."""

    @staticmethod
    def validate_plugin(plugin_class: Type[BasePlugin]) -> bool:
        """
        Validate that a class properly implements the plugin interface.

        Args:
            plugin_class: Plugin class to validate.

        Returns:
            bool: True if valid, False otherwise.
        """
        required_methods = [
            'initialize',
            'shutdown',
            'get_api_routes',
            'get_database_schema'
        ]

        for method in required_methods:
            if not hasattr(plugin_class, method):
                logger.error(f"Plugin class missing required method: {method}")
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
        required_fields = ['name', 'category', 'version', 'description']

        for field in required_fields:
            if field not in manifest:
                logger.error(f"Manifest missing required field: {field}")
                return False

        # Validate category
        valid_categories = [
            'business', 'integration', 'analytics', 'security',
            'ui', 'notification', 'storage', 'workflow', 'custom'
        ]

        if manifest['category'] not in valid_categories:
            logger.error(f"Invalid plugin category: {manifest['category']}")
            return False

        return True


# Export main classes
__all__ = [
    'BasePlugin',
    'BusinessPlugin',
    'IntegrationPlugin',
    'AnalyticsPlugin',
    'SecurityPlugin',
    'UIPlugin',
    'NotificationPlugin',
    'StoragePlugin',
    'WorkflowPlugin',
    'PluginMetadata',
    'PluginLifecycle',
    'PluginContext',
    'PluginDependency',
    'PluginPermission',
    'PluginHook',
    'PluginConfigSchema',
    'plugin_hook',
    'requires_permission',
    'requires_dependency',
    'PluginError',
    'PluginInitializationError',
    'PluginConfigurationError',
    'PluginDependencyError',
    'HealthStatus',
    'PluginValidator'
]
