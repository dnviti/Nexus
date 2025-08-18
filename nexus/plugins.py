"""
Nexus Framework Plugin System
Base classes and interfaces for plugin development.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

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

    config_schema: Dict[str, Any] = Field(default_factory=dict)
    required: List[str] = Field(default_factory=list)


# Plugin Decorators
def plugin_hook(name: str, priority: int = 0) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
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
        self.db_adapter: Optional[Any] = None
        self.event_bus: Optional[Any] = None
        self.service_registry: Optional[Any] = None
        self.cache_manager: Optional[Any] = None

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
            except (json.JSONDecodeError, TypeError, ValueError) as e:
                logger.debug(f"Failed to parse JSON config value for key '{key}': {e}")
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
        self._tasks: List[asyncio.Task[Any]] = []
        self._cache: Dict[str, Any] = {}
        self._business_rules: Dict[str, Any] = {}
        self._workflows: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the business plugin."""
        logger.info(f"Initializing business plugin: {self.name}")

        # Load business rules from configuration
        await self._load_business_rules()

        # Initialize workflow engine
        await self._initialize_workflows()

        # Set up business logic services
        await self._setup_business_services()

        logger.info(f"Business plugin {self.name} initialized successfully")
        return True

    async def _load_business_rules(self) -> None:
        """Load business rules from configuration."""
        try:
            rules_config = await self.get_config("business_rules", {})
            self._business_rules = rules_config
            logger.info(f"Loaded {len(self._business_rules)} business rules")
        except Exception as e:
            logger.warning(f"Failed to load business rules: {e}")

    async def _initialize_workflows(self) -> None:
        """Initialize business workflows."""
        try:
            workflow_config = await self.get_config("workflows", {})
            self._workflows = workflow_config
            logger.info(f"Initialized {len(self._workflows)} workflows")
        except Exception as e:
            logger.warning(f"Failed to initialize workflows: {e}")

    async def _setup_business_services(self) -> None:
        """Set up business logic services."""
        try:
            # Register business services
            if hasattr(self, "service_registry") and self.service_registry:
                self.service_registry.register(f"{self.name}_business_rules", self._business_rules)
                self.service_registry.register(f"{self.name}_workflows", self._workflows)
                logger.info("Business services registered")
            else:
                logger.info("Service registry not available, skipping service registration")
        except Exception as e:
            logger.warning(f"Failed to setup business services: {e}")

    async def validate_business_rule(self, rule_name: str, data: Dict[str, Any]) -> bool:
        """Validate data against business rule."""
        try:
            rule = self._business_rules.get(rule_name)
            if not rule:
                logger.warning(f"Business rule not found: {rule_name}")
                return False

            # Simple validation logic (extend as needed)
            if "required_fields" in rule:
                for field in rule["required_fields"]:
                    if field not in data:
                        return False

            if "validation_rules" in rule:
                for validation in rule["validation_rules"]:
                    field = validation.get("field")
                    rule_type = validation.get("type")

                    if field in data:
                        value = data[field]
                        if rule_type == "min_length" and len(str(value)) < validation.get(
                            "value", 0
                        ):
                            return False
                        elif rule_type == "max_length" and len(str(value)) > validation.get(
                            "value", float("inf")
                        ):
                            return False

            return True
        except Exception as e:
            logger.error(f"Error validating business rule {rule_name}: {e}")
            return False

    async def execute_business_workflow(
        self, workflow_name: str, context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a business workflow."""
        try:
            workflow = self._workflows.get(workflow_name)
            if not workflow:
                return {"error": f"Workflow not found: {workflow_name}"}

            result = {
                "workflow": workflow_name,
                "status": "completed",
                "steps_executed": [],
                "result": context,
            }

            # Execute workflow steps
            steps = workflow.get("steps", [])
            for step in steps:
                step_name = step.get("name", "unnamed_step")
                step_type = step.get("type", "action")

                if step_type == "validation":
                    rule_name = step.get("rule")
                    if rule_name and not await self.validate_business_rule(rule_name, context):
                        result["status"] = "failed"
                        result["error"] = f"Validation failed at step: {step_name}"
                        break

                if "steps_executed" not in result:
                    result["steps_executed"] = []
                steps_executed = result["steps_executed"]
                if isinstance(steps_executed, list):
                    steps_executed.append(step_name)

            return result
        except Exception as e:
            logger.error(f"Error executing workflow {workflow_name}: {e}")
            return {"error": str(e), "workflow": workflow_name, "status": "failed"}

    async def shutdown(self) -> None:
        """Shutdown the business plugin."""
        logger.info(f"Shutting down business plugin: {self.name}")
        # Cancel any running tasks
        if hasattr(self, "_tasks"):
            for task in self._tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        # Clear any cached data
        if hasattr(self, "_cache"):
            self._cache.clear()
        logger.info(f"Business plugin {self.name} shutdown complete")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the business plugin."""
        from fastapi import APIRouter
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-business"])

        class BusinessRuleRequest(BaseModel):
            rule_name: str
            data: Dict[str, Any]

        class WorkflowRequest(BaseModel):
            workflow_name: str
            context: Dict[str, Any]

        @router.get("/rules")
        async def list_business_rules() -> Dict[str, Any]:
            """List available business rules."""
            return {"rules": list(self._business_rules.keys())}

        @router.post("/rules/validate")
        async def validate_rule(request: BusinessRuleRequest) -> Dict[str, Any]:
            """Validate data against a business rule."""
            result = await self.validate_business_rule(request.rule_name, request.data)
            return {"valid": result, "rule": request.rule_name}

        @router.get("/workflows")
        async def list_workflows() -> Dict[str, Any]:
            """List available workflows."""
            return {"workflows": list(self._workflows.keys())}

        @router.post("/workflows/execute")
        async def execute_workflow(request: WorkflowRequest) -> Dict[str, Any]:
            """Execute a business workflow."""
            result = await self.execute_business_workflow(request.workflow_name, request.context)
            return result

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the business plugin."""
        return {
            "collections": {
                "business_rules": {
                    "indexes": [
                        {"field": "name", "unique": True},
                        {"field": "category"},
                        {"field": "created_at"},
                    ]
                },
                "workflows": {
                    "indexes": [
                        {"field": "name", "unique": True},
                        {"field": "status"},
                        {"field": "created_at"},
                    ]
                },
                "workflow_executions": {
                    "indexes": [
                        {"field": "execution_id", "unique": True},
                        {"field": "workflow_name"},
                        {"field": "status"},
                        {"field": "created_at"},
                    ]
                },
            },
            "initial_data": {
                "settings": {"default_workflow_timeout": 3600, "max_concurrent_workflows": 10}
            },
        }


class IntegrationPlugin(BasePlugin):
    """Base class for integration plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "integration"
        self._connections: List[Any] = []
        self._sync_tasks: List[asyncio.Task[Any]] = []
        self._external_apis: Dict[str, Any] = {}
        self._webhook_endpoints: List[str] = []
        self._sync_status: Dict[str, str] = {}

    async def initialize(self) -> bool:
        """Initialize the integration plugin."""
        logger.info(f"Initializing integration plugin: {self.name}")

        # Load integration configurations
        await self._load_integration_configs()

        # Initialize external API connections
        await self._initialize_external_connections()

        # Set up webhook endpoints
        await self._setup_webhook_endpoints()

        # Start background sync tasks
        await self._start_sync_tasks()

        logger.info(f"Integration plugin {self.name} initialized successfully")
        return True

    async def _load_integration_configs(self) -> None:
        """Load integration configurations."""
        try:
            config = await self.get_config("integrations", {})
            self._external_apis = config.get("apis", {})
            self._webhook_endpoints = config.get("webhooks", [])
            logger.info(f"Loaded {len(self._external_apis)} API integrations")
        except Exception as e:
            logger.warning(f"Failed to load integration configs: {e}")

    async def _initialize_external_connections(self) -> None:
        """Initialize connections to external services."""
        try:
            for api_name, api_config in self._external_apis.items():
                connection = await self._create_api_connection(api_name, api_config)
                if connection:
                    self._connections.append(connection)
                    self._sync_status[api_name] = "connected"
                    logger.info(f"Connected to external API: {api_name}")
                else:
                    self._sync_status[api_name] = "failed"
        except Exception as e:
            logger.error(f"Failed to initialize external connections: {e}")

    async def _create_api_connection(self, api_name: str, config: Dict[str, Any]) -> Optional[Any]:
        """Create connection to external API."""
        # Mock connection object for demonstration
        return {
            "name": api_name,
            "url": config.get("url"),
            "auth": config.get("auth", {}),
            "timeout": config.get("timeout", 30),
            "connected": True,
        }

    async def _setup_webhook_endpoints(self) -> None:
        """Set up webhook endpoints for external integrations."""
        try:
            for endpoint in self._webhook_endpoints:
                logger.info(f"Setting up webhook endpoint: {endpoint}")
                # In a real implementation, this would register webhook handlers
        except Exception as e:
            logger.error(f"Failed to setup webhook endpoints: {e}")

    async def _start_sync_tasks(self) -> None:
        """Start background synchronization tasks."""
        try:
            for api_name in self._external_apis.keys():
                task = asyncio.create_task(self._sync_data_periodically(api_name))
                self._sync_tasks.append(task)
                logger.info(f"Started sync task for: {api_name}")
        except Exception as e:
            logger.error(f"Failed to start sync tasks: {e}")

    async def _sync_data_periodically(self, api_name: str) -> None:
        """Periodically sync data with external API."""
        while True:
            try:
                await asyncio.sleep(300)  # Sync every 5 minutes
                await self._sync_with_external_api(api_name)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic sync for {api_name}: {e}")

    async def _sync_with_external_api(self, api_name: str) -> bool:
        """Sync data with a specific external API."""
        try:
            api_config = self._external_apis.get(api_name)
            if not api_config:
                return False

            # Mock data synchronization
            logger.info(f"Syncing data with {api_name}")
            self._sync_status[api_name] = "syncing"

            # Simulate API call
            await asyncio.sleep(0.1)

            self._sync_status[api_name] = "synced"
            return True
        except Exception as e:
            logger.error(f"Failed to sync with {api_name}: {e}")
            self._sync_status[api_name] = "error"
            return False

    async def shutdown(self) -> None:
        """Shutdown the integration plugin."""
        logger.info(f"Shutting down integration plugin: {self.name}")
        # Close any external connections
        if hasattr(self, "_connections"):
            for conn in self._connections:
                try:
                    if hasattr(conn, "close"):
                        await conn.close()
                    elif hasattr(conn, "disconnect"):
                        await conn.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
        # Stop any background sync tasks
        if hasattr(self, "_sync_tasks"):
            for task in self._sync_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        logger.info(f"Integration plugin {self.name} shutdown complete")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the integration plugin."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-integration"])

        class SyncRequest(BaseModel):
            api_name: str
            force: bool = False

        @router.get("/connections")
        async def list_connections() -> Dict[str, Any]:
            """List external API connections."""
            connections = []
            for conn in self._connections:
                connections.append(
                    {
                        "name": conn.get("name"),
                        "url": conn.get("url"),
                        "connected": conn.get("connected", False),
                    }
                )
            return {"connections": connections}

        @router.get("/status")
        async def get_sync_status() -> Dict[str, Any]:
            """Get synchronization status for all APIs."""
            return {"sync_status": self._sync_status}

        @router.post("/sync")
        async def trigger_sync(request: SyncRequest) -> Dict[str, Any]:
            """Trigger manual synchronization with external API."""
            success = await self._sync_with_external_api(request.api_name)
            if not success:
                raise HTTPException(status_code=500, detail=f"Sync failed for {request.api_name}")
            return {"message": f"Sync triggered for {request.api_name}"}

        @router.post("/test-connection")
        async def test_api_connection(api_name: str) -> Dict[str, Any]:
            """Test connection to external API."""
            result = await self.test_connection()
            return {"api_name": api_name, "connected": result}

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the integration plugin."""
        return {
            "collections": {
                "external_apis": {
                    "indexes": [
                        {"field": "name", "unique": True},
                        {"field": "status"},
                        {"field": "last_sync"},
                    ]
                },
                "sync_logs": {
                    "indexes": [{"field": "api_name"}, {"field": "timestamp"}, {"field": "status"}]
                },
                "webhook_events": {
                    "indexes": [{"field": "source"}, {"field": "timestamp"}, {"field": "processed"}]
                },
            },
            "initial_data": {"settings": {"sync_interval": 300, "max_retries": 3, "timeout": 30}},
        }

    async def test_connection(self) -> bool:
        """Test connection to external service."""
        try:
            # In a real implementation, this would test actual connections
            # For now, simulate a connection test
            logger.info(f"Testing connection for integration plugin: {self.name}")

            # Check if connection configuration exists
            if hasattr(self, "_connections") and self._connections:
                # Simulate testing each connection
                for i, conn in enumerate(self._connections):
                    if hasattr(conn, "ping"):
                        await conn.ping()
                    logger.info(f"Connection {i} test passed")
                return True
            else:
                # No connections configured, assume healthy
                logger.info("No connections configured, test passed")
                return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


class AnalyticsPlugin(BasePlugin):
    """Base class for analytics plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "analytics"
        self._metrics_buffer: List[Dict[str, Any]] = []
        self._collection_tasks: List[asyncio.Task[Any]] = []
        self._analytics_client: Optional[Any] = None

    async def initialize(self) -> bool:
        """Initialize the analytics plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the analytics plugin."""
        logger.info(f"Shutting down analytics plugin: {self.name}")
        # Flush any pending metrics
        if hasattr(self, "_metrics_buffer") and self._metrics_buffer:
            try:
                await self._flush_metrics()
            except Exception as e:
                logger.warning(f"Error flushing metrics: {e}")
        # Stop metric collection tasks
        if hasattr(self, "_collection_tasks"):
            for task in self._collection_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        # Close analytics connections
        if hasattr(self, "_analytics_client") and self._analytics_client:
            try:
                await self._analytics_client.close()
            except Exception as e:
                logger.warning(f"Error closing analytics client: {e}")
        logger.info(f"Analytics plugin {self.name} shutdown complete")

    async def _flush_metrics(self) -> None:
        """Flush pending metrics to storage."""
        if hasattr(self, "_metrics_buffer") and self._metrics_buffer:
            logger.info(f"Flushing {len(self._metrics_buffer)} metrics")
            self._metrics_buffer.clear()

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the analytics plugin."""
        from typing import Optional

        from fastapi import APIRouter, Query
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-analytics"])

        class ReportRequest(BaseModel):
            type: str = "summary"
            time_range: str = "24h"
            params: Optional[Dict[str, Any]] = {}

        @router.get("/metrics")
        async def get_current_metrics() -> Dict[str, Any]:
            """Get current analytics metrics."""
            return await self.collect_metrics()

        @router.post("/reports/generate")
        async def generate_analytics_report(request: ReportRequest) -> Dict[str, Any]:
            """Generate an analytics report."""
            return await self.generate_report(request.dict())

        @router.get("/reports")
        async def list_reports(
            limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)  # noqa: B008
        ) -> Dict[str, Any]:
            """List available reports."""
            # Mock report list
            reports = [
                {"id": f"report_{i}", "type": "summary", "created_at": "2024-01-01T12:00:00Z"}
                for i in range(offset, offset + limit)
            ]
            return {"reports": reports, "total": 50}

        @router.get("/dashboard")
        async def get_dashboard_data() -> Dict[str, Any]:
            """Get dashboard data for analytics plugin."""
            metrics = await self.collect_metrics()
            return {
                "summary": metrics.get("metrics", {}),
                "charts": {
                    "events_over_time": "chart_data_placeholder",
                    "performance_metrics": "chart_data_placeholder",
                },
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the analytics plugin."""
        return {
            "collections": {
                "metrics": {
                    "indexes": [
                        {"field": "timestamp"},
                        {"field": "plugin_name"},
                        {"field": "metric_type"},
                    ]
                },
                "reports": {
                    "indexes": [
                        {"field": "report_id", "unique": True},
                        {"field": "type"},
                        {"field": "created_at"},
                    ]
                },
                "events": {
                    "indexes": [
                        {"field": "event_type"},
                        {"field": "timestamp"},
                        {"field": "source"},
                    ]
                },
            },
            "initial_data": {
                "settings": {
                    "retention_days": 90,
                    "aggregation_interval": 3600,
                    "max_metrics_per_batch": 1000,
                }
            },
        }

    async def collect_metrics(self) -> Dict[str, Any]:
        """Collect analytics metrics."""
        try:
            import time
            from datetime import datetime

            metrics = {
                "timestamp": datetime.utcnow().isoformat(),
                "plugin_name": self.name,
                "collection_time": time.time(),
                "metrics": {
                    "events_processed": getattr(self, "_events_processed", 0),
                    "data_points_collected": len(getattr(self, "_metrics_buffer", [])),
                    "active_sessions": getattr(self, "_active_sessions", 0),
                    "error_count": getattr(self, "_error_count", 0),
                    "performance": {
                        "avg_processing_time_ms": getattr(self, "_avg_processing_time", 0.0),
                        "throughput_per_second": getattr(self, "_throughput", 0.0),
                    },
                },
            }

            # Add to metrics buffer
            if not hasattr(self, "_metrics_buffer"):
                self._metrics_buffer = []
            self._metrics_buffer.append(metrics)

            metrics_data = metrics.get("metrics", [])
            if isinstance(metrics_data, list):
                logger.info(f"Collected metrics for {self.name}: {len(metrics_data)} data points")
            else:
                logger.info(f"Collected metrics for {self.name}: metrics data available")
            return metrics

        except Exception as e:
            logger.error(f"Failed to collect metrics: {e}")
            from datetime import datetime

            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}

    async def generate_report(self, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate analytics report."""
        try:
            from datetime import datetime

            # Default parameters
            if params is None:
                params = {}

            time_range = params.get("time_range", "24h")
            report_type = params.get("type", "summary")

            # Collect current metrics
            current_metrics = await self.collect_metrics()

            # Generate report based on type
            if report_type == "summary":
                report = {
                    "report_id": f"report_{int(datetime.utcnow().timestamp())}",
                    "type": "summary",
                    "generated_at": datetime.utcnow().isoformat(),
                    "time_range": time_range,
                    "plugin": self.name,
                    "summary": {
                        "total_events": current_metrics.get("metrics", {}).get(
                            "events_processed", 0
                        ),
                        "total_data_points": len(getattr(self, "_metrics_buffer", [])),
                        "average_performance": current_metrics.get("metrics", {}).get(
                            "performance", {}
                        ),
                        "status": (
                            "healthy"
                            if current_metrics.get("metrics", {}).get("error_count", 0) == 0
                            else "degraded"
                        ),
                    },
                    "charts": {
                        "performance_trend": "data_placeholder",
                        "event_distribution": "data_placeholder",
                    },
                }
            else:
                report = {
                    "report_id": f"detailed_report_{int(datetime.utcnow().timestamp())}",
                    "type": "detailed",
                    "generated_at": datetime.utcnow().isoformat(),
                    "raw_metrics": current_metrics,
                    "historical_data": getattr(self, "_metrics_buffer", [])[
                        -100:
                    ],  # Last 100 entries
                }

            logger.info(f"Generated {report_type} report for {self.name}")
            return report

        except Exception as e:
            logger.error(f"Failed to generate report: {e}")
            from datetime import datetime

            return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}


class SecurityPlugin(BasePlugin):
    """Base class for security plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "security"
        self._auth_cache: Dict[str, Any] = {}
        self._session_cache: Dict[str, Any] = {}
        self._monitoring_tasks: List[asyncio.Task[Any]] = []
        self._audit_buffer: List[Dict[str, Any]] = []

    async def initialize(self) -> bool:
        """Initialize the security plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the security plugin."""
        logger.info(f"Shutting down security plugin: {self.name}")
        # Clear security caches
        if hasattr(self, "_auth_cache"):
            self._auth_cache.clear()
        if hasattr(self, "_session_cache"):
            self._session_cache.clear()
        # Stop security monitoring tasks
        if hasattr(self, "_monitoring_tasks"):
            for task in self._monitoring_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        # Flush any pending audit logs
        if hasattr(self, "_audit_buffer") and self._audit_buffer:
            try:
                await self._flush_audit_logs()
            except Exception as e:
                logger.warning(f"Error flushing audit logs: {e}")
        logger.info(f"Security plugin {self.name} shutdown complete")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the security plugin."""
        from fastapi import APIRouter
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-security"])

        class ValidationRequest(BaseModel):
            request_data: Dict[str, Any]

        class AuditLogRequest(BaseModel):
            action: str
            event: Dict[str, Any]

        @router.post("/validate")
        async def validate_security_request(request: ValidationRequest) -> Dict[str, Any]:
            """Validate a request for security concerns."""
            # Create a mock request object for validation
            mock_request = type("MockRequest", (), request.request_data)()
            result = await self.validate_request(mock_request)
            return {"valid": result, "timestamp": "2024-01-01T12:00:00Z"}

        @router.post("/audit")
        async def create_audit_log(request: AuditLogRequest) -> Dict[str, Any]:
            """Create an audit log entry."""
            await self.audit_log(request.action, request.event)
            return {"message": "Audit log created successfully"}

        @router.get("/audit")
        async def get_audit_logs(
            limit: int = 100, offset: int = 0, action: Optional[str] = None
        ) -> Dict[str, Any]:
            """Get audit logs."""
            # Return mock audit logs
            logs = getattr(self, "_audit_buffer", [])
            filtered_logs = logs
            if action:
                filtered_logs = [log for log in logs if log.get("action") == action]

            paginated = filtered_logs[offset : offset + limit]
            return {
                "logs": paginated,
                "total": len(filtered_logs),
                "limit": limit,
                "offset": offset,
            }

        @router.get("/status")
        async def get_security_status() -> Dict[str, Any]:
            """Get security plugin status."""
            return {
                "status": "active",
                "audit_logs_count": len(getattr(self, "_audit_buffer", [])),
                "cache_status": {
                    "auth_cache_size": len(getattr(self, "_auth_cache", {})),
                    "session_cache_size": len(getattr(self, "_session_cache", {})),
                },
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the security plugin."""
        return {
            "collections": {
                "audit_logs": {
                    "indexes": [
                        {"field": "timestamp"},
                        {"field": "action"},
                        {"field": "severity"},
                        {"field": "plugin"},
                    ]
                },
                "security_events": {
                    "indexes": [
                        {"field": "event_type"},
                        {"field": "timestamp"},
                        {"field": "ip_address"},
                        {"field": "user_id"},
                    ]
                },
                "failed_attempts": {
                    "indexes": [
                        {"field": "ip_address"},
                        {"field": "timestamp"},
                        {"field": "attempt_type"},
                    ]
                },
            },
            "initial_data": {
                "settings": {
                    "max_login_attempts": 5,
                    "lockout_duration": 900,
                    "audit_retention_days": 365,
                }
            },
        }

    async def validate_request(self, request: Any) -> bool:
        """Validate a request for security concerns."""
        try:
            # Basic security validation
            validation_results = []

            # Check for common security headers
            if hasattr(request, "headers"):
                headers = getattr(request, "headers", {})

                # Check for suspicious headers
                suspicious_headers = ["x-forwarded-for", "x-real-ip"]
                for header in suspicious_headers:
                    if header in headers:
                        validation_results.append(f"Suspicious header detected: {header}")

            # Check request method
            if hasattr(request, "method"):
                method = getattr(request, "method", "GET")
                if method not in ["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"]:
                    validation_results.append(f"Invalid HTTP method: {method}")
                    return False

            # Check for potential path traversal
            if hasattr(request, "url") or hasattr(request, "path"):
                path = getattr(request, "path", "") or str(getattr(request, "url", ""))
                if ".." in path or "/etc/" in path or "/proc/" in path:
                    validation_results.append("Potential path traversal detected")
                    await self.audit_log(
                        "security_validation_failed",
                        {"reason": "path_traversal", "path": path, "severity": "high"},
                    )
                    return False

            # Log validation results
            if validation_results:
                await self.audit_log(
                    "security_validation_warning",
                    {"warnings": validation_results, "severity": "medium"},
                )

            # Request is valid
            return True

        except Exception as e:
            logger.error(f"Security validation error: {e}")
            await self.audit_log("security_validation_error", {"error": str(e), "severity": "high"})
            return False

    async def audit_log(self, action: str, event: Dict[str, Any]) -> None:
        """Log security audit event."""
        from datetime import datetime

        audit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "plugin": self.name,
            "event": event,
            "severity": event.get("severity", "info"),
        }

        # Initialize audit buffer if it doesn't exist
        if not hasattr(self, "_audit_buffer"):
            self._audit_buffer = []

        self._audit_buffer.append(audit_entry)

        # Log to standard logger as well
        logger.info(f"Security audit: {action}", extra=audit_entry)

        # Auto-flush if buffer is getting large
        if len(self._audit_buffer) >= 100:
            try:
                await self._flush_audit_logs()
            except Exception as e:
                logger.warning(f"Error auto-flushing audit logs: {e}")

    async def _flush_audit_logs(self) -> None:
        """Flush pending audit logs to persistent storage."""
        if not hasattr(self, "_audit_buffer") or not self._audit_buffer:
            return

        try:
            # In a real implementation, this would write to a secure audit log file
            # or send to a centralized logging system
            audit_data = self._audit_buffer.copy()
            self._audit_buffer.clear()

            # For now, just log the count
            logger.info(f"Flushed {len(audit_data)} audit log entries")

        except Exception as e:
            logger.error(f"Failed to flush audit logs: {e}")
            raise


class UIPlugin(BasePlugin):
    """Base class for UI plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "ui"
        self._component_cache: Dict[str, Any] = {}
        self._websocket_connections: List[Any] = []
        self._ui_tasks: List[asyncio.Task[Any]] = []

    async def initialize(self) -> bool:
        """Initialize the UI plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the UI plugin."""
        logger.info(f"Shutting down UI plugin: {self.name}")
        # Clear UI component caches
        if hasattr(self, "_component_cache"):
            self._component_cache.clear()
        # Close any WebSocket connections
        if hasattr(self, "_websocket_connections"):
            for ws in self._websocket_connections:
                try:
                    await ws.close()
                except Exception as e:
                    logger.warning(f"Error closing WebSocket: {e}")
        # Stop UI update tasks
        if hasattr(self, "_ui_tasks"):
            for task in self._ui_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        logger.info(f"UI plugin {self.name} shutdown complete")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the UI plugin."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-ui"])

        class ComponentRequest(BaseModel):
            component_id: str
            config: Optional[Dict[str, Any]] = {}

        @router.get("/components")
        async def list_ui_components() -> Dict[str, Any]:
            """List available UI components."""
            components = self.get_ui_components()
            return {"components": components}

        @router.get("/menu")
        async def get_menu_items() -> Dict[str, Any]:
            """Get menu items for the UI."""
            menu_items = self.get_menu_items()
            return {"menu_items": menu_items}

        @router.post("/components/render")
        async def render_component(request: ComponentRequest) -> Dict[str, Any]:
            """Render a UI component."""
            components = self.get_ui_components()
            component = next((c for c in components if c["id"] == request.component_id), None)
            if not component:
                raise HTTPException(status_code=404, detail="Component not found")

            return {
                "component": component,
                "rendered_html": f"<div id='{request.component_id}'>Component content</div>",
                "assets": {
                    "css": [f"/static/{self.name}/component.css"],
                    "js": [f"/static/{self.name}/component.js"],
                },
            }

        @router.get("/theme")
        async def get_theme() -> Dict[str, Any]:
            """Get UI theme configuration."""
            return {
                "name": f"{self.name}_theme",
                "colors": {
                    "primary": "#007bff",
                    "secondary": "#6c757d",
                    "success": "#28a745",
                    "danger": "#dc3545",
                },
                "typography": {
                    "font_family": "Inter, sans-serif",
                    "font_sizes": {"sm": "14px", "md": "16px", "lg": "18px"},
                },
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the UI plugin."""
        return {
            "collections": {
                "ui_components": {
                    "indexes": [
                        {"field": "component_id", "unique": True},
                        {"field": "type"},
                        {"field": "created_at"},
                    ]
                },
                "ui_themes": {
                    "indexes": [
                        {"field": "theme_name", "unique": True},
                        {"field": "active"},
                        {"field": "updated_at"},
                    ]
                },
                "user_preferences": {
                    "indexes": [
                        {"field": "user_id"},
                        {"field": "preference_type"},
                        {"field": "updated_at"},
                    ]
                },
            },
            "initial_data": {
                "settings": {
                    "default_theme": "light",
                    "component_cache_ttl": 3600,
                    "enable_dark_mode": True,
                }
            },
        }

    def get_ui_components(self) -> List[Dict[str, Any]]:
        """Get UI components provided by this plugin."""
        try:
            components = [
                {
                    "id": f"{self.name}_dashboard",
                    "type": "dashboard",
                    "title": f"{self.name.title()} Dashboard",
                    "description": f"Main dashboard for {self.name} plugin",
                    "path": f"/ui/{self.name}/dashboard",
                    "icon": "dashboard",
                    "permissions": ["read"],
                    "config": {"refreshInterval": 30000, "showStats": True, "showCharts": True},
                },
                {
                    "id": f"{self.name}_settings",
                    "type": "settings",
                    "title": f"{self.name.title()} Settings",
                    "description": f"Configuration settings for {self.name} plugin",
                    "path": f"/ui/{self.name}/settings",
                    "icon": "settings",
                    "permissions": ["admin"],
                    "config": {"sections": ["general", "advanced"], "validation": True},
                },
            ]

            # Add to component cache
            if not hasattr(self, "_component_cache"):
                self._component_cache = {}
            self._component_cache[f"{self.name}_components"] = components

            return components

        except Exception as e:
            logger.error(f"Failed to get UI components: {e}")
            return []

    def get_menu_items(self) -> List[Dict[str, Any]]:
        """Get menu items for this plugin."""
        try:
            menu_items = [
                {
                    "id": f"{self.name}_menu",
                    "label": self.name.title(),
                    "icon": "puzzle-piece",
                    "order": 100,
                    "children": [
                        {
                            "id": f"{self.name}_dashboard",
                            "label": "Dashboard",
                            "path": f"/ui/{self.name}/dashboard",
                            "icon": "dashboard",
                            "permissions": ["read"],
                        },
                        {
                            "id": f"{self.name}_settings",
                            "label": "Settings",
                            "path": f"/ui/{self.name}/settings",
                            "icon": "settings",
                            "permissions": ["admin"],
                        },
                    ],
                }
            ]

            return menu_items

        except Exception as e:
            logger.error(f"Failed to get menu items: {e}")
            return []


class NotificationPlugin(BasePlugin):
    """Base class for notification plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "notification"
        self._notification_queue: List[Dict[str, Any]] = []
        self._notification_clients: List[Any] = []
        self._notification_tasks: List[asyncio.Task[Any]] = []

    async def initialize(self) -> bool:
        """Initialize the notification plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the notification plugin."""
        logger.info(f"Shutting down notification plugin: {self.name}")
        # Send any pending notifications
        if hasattr(self, "_notification_queue") and self._notification_queue:
            try:
                await self._flush_notifications()
            except Exception as e:
                logger.warning(f"Error flushing notifications: {e}")
        # Close notification service connections
        if hasattr(self, "_notification_clients"):
            for client in self._notification_clients:
                try:
                    if hasattr(client, "close"):
                        await client.close()
                except Exception as e:
                    logger.warning(f"Error closing notification client: {e}")
        # Stop notification tasks
        if hasattr(self, "_notification_tasks"):
            for task in self._notification_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        logger.info(f"Notification plugin {self.name} shutdown complete")

    async def _flush_notifications(self) -> None:
        """Flush pending notifications."""
        if hasattr(self, "_notification_queue") and self._notification_queue:
            logger.info(f"Flushing {len(self._notification_queue)} notifications")
            self._notification_queue.clear()

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the notification plugin."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-notifications"])

        class NotificationRequest(BaseModel):
            recipient: str
            subject: str
            message: str
            type: str = "email"
            metadata: Optional[Dict[str, Any]] = {}

        @router.post("/send")
        async def send_notification_endpoint(request: NotificationRequest) -> Dict[str, Any]:
            """Send a notification."""
            success = await self.send_notification(
                request.recipient, request.subject, request.message, request.metadata
            )
            if not success:
                raise HTTPException(status_code=500, detail="Failed to send notification")
            return {"message": "Notification sent successfully"}

        @router.get("/queue")
        async def get_notification_queue() -> Dict[str, Any]:
            """Get pending notifications in queue."""
            queue = getattr(self, "_notification_queue", [])
            return {
                "queue_size": len(queue),
                "pending_notifications": queue[:10],  # Return first 10
            }

        @router.get("/history")
        async def get_notification_history(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
            """Get notification history."""
            # Mock history for demonstration
            history = [
                {
                    "id": f"notif_{i}",
                    "recipient": f"user{i}@example.com",
                    "subject": f"Test notification {i}",
                    "status": "sent",
                    "created_at": "2024-01-01T12:00:00Z",
                }
                for i in range(offset, offset + limit)
            ]
            return {"history": history, "total": 100}

        @router.get("/status")
        async def get_notification_status() -> Dict[str, Any]:
            """Get notification service status."""
            queue = getattr(self, "_notification_queue", [])
            clients = getattr(self, "_notification_clients", [])
            return {
                "status": "active",
                "queue_size": len(queue),
                "active_clients": len(clients),
                "supported_types": ["email", "sms", "webhook"],
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the notification plugin."""
        return {
            "collections": {
                "notifications": {
                    "indexes": [
                        {"field": "notification_id", "unique": True},
                        {"field": "recipient"},
                        {"field": "status"},
                        {"field": "created_at"},
                    ]
                },
                "notification_templates": {
                    "indexes": [
                        {"field": "template_name", "unique": True},
                        {"field": "type"},
                        {"field": "updated_at"},
                    ]
                },
                "delivery_logs": {
                    "indexes": [
                        {"field": "notification_id"},
                        {"field": "delivery_status"},
                        {"field": "timestamp"},
                    ]
                },
            },
            "initial_data": {
                "settings": {"retry_attempts": 3, "retry_delay": 60, "batch_size": 100}
            },
        }

    async def send_notification(
        self, recipient: str, subject: str, message: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Send a notification to a recipient."""
        try:
            from datetime import datetime

            if metadata is None:
                metadata = {}

            notification = {
                "id": f"notif_{int(datetime.utcnow().timestamp())}",
                "recipient": recipient,
                "subject": subject,
                "message": message,
                "metadata": metadata,
                "created_at": datetime.utcnow().isoformat(),
                "status": "pending",
                "attempts": 0,
                "plugin": self.name,
            }

            # Add to notification queue
            if not hasattr(self, "_notification_queue"):
                self._notification_queue = []
            self._notification_queue.append(notification)

            # Simulate sending notification
            # In a real implementation, this would send via email, SMS, webhook, etc.
            notification_type = metadata.get("type", "email")

            logger.info(f"Sending {notification_type} notification to {recipient}: {subject}")

            # Simulate different notification channels
            if notification_type == "email":
                success = await self._send_email_notification(notification)
            elif notification_type == "sms":
                success = await self._send_sms_notification(notification)
            elif notification_type == "webhook":
                success = await self._send_webhook_notification(notification)
            else:
                logger.warning(f"Unknown notification type: {notification_type}")
                success = False

            # Update notification status
            notification["status"] = "sent" if success else "failed"
            notification["sent_at"] = datetime.utcnow().isoformat()

            logger.info(f"Notification {notification['id']} status: {notification['status']}")
            return success

        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            return False

    async def _send_email_notification(self, notification: Dict[str, Any]) -> bool:
        """Send email notification."""
        # Simulate email sending
        await asyncio.sleep(0.1)  # Simulate network delay
        logger.info(f"Email sent to {notification['recipient']}")
        return True

    async def _send_sms_notification(self, notification: Dict[str, Any]) -> bool:
        """Send SMS notification."""
        # Simulate SMS sending
        await asyncio.sleep(0.05)  # Simulate network delay
        logger.info(f"SMS sent to {notification['recipient']}")
        return True

    async def _send_webhook_notification(self, notification: Dict[str, Any]) -> bool:
        """Send webhook notification."""
        # Simulate webhook sending
        await asyncio.sleep(0.2)  # Simulate network delay
        logger.info(f"Webhook sent to {notification['recipient']}")
        return True


class StoragePlugin(BasePlugin):
    """Base class for storage plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "storage"
        self._write_buffer: List[Dict[str, Any]] = []
        self._storage_clients: List[Any] = []
        self._cleanup_tasks: List[asyncio.Task[Any]] = []

    async def initialize(self) -> bool:
        """Initialize the storage plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the storage plugin."""
        logger.info(f"Shutting down storage plugin: {self.name}")
        # Flush any pending writes
        if hasattr(self, "_write_buffer") and self._write_buffer:
            try:
                await self._flush_writes()
            except Exception as e:
                logger.warning(f"Error flushing writes: {e}")
        # Close storage connections
        if hasattr(self, "_storage_clients"):
            for client in self._storage_clients:
                try:
                    if hasattr(client, "close"):
                        await client.close()
                    elif hasattr(client, "disconnect"):
                        await client.disconnect()
                except Exception as e:
                    logger.warning(f"Error closing storage client: {e}")
        # Stop background cleanup tasks
        if hasattr(self, "_cleanup_tasks"):
            for task in self._cleanup_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        logger.info(f"Storage plugin {self.name} shutdown complete")

    async def _flush_writes(self) -> None:
        """Flush pending writes to storage."""
        if hasattr(self, "_write_buffer") and self._write_buffer:
            logger.info(f"Flushing {len(self._write_buffer)} writes")
            self._write_buffer.clear()

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the storage plugin."""
        from fastapi import APIRouter, File, HTTPException, UploadFile
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-storage"])

        class StorageRequest(BaseModel):
            key: str
            data: str  # Base64 encoded data

        @router.post("/store")
        async def store_data_endpoint(request: StorageRequest) -> Dict[str, Any]:
            """Store data with a key."""
            import base64

            try:
                data_bytes = base64.b64decode(request.data)
                identifier = await self.store(request.key, data_bytes)
                return {"identifier": identifier, "key": request.key}
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid data: {e}")

        @router.post("/upload")
        async def upload_file(file: UploadFile = File(...)) -> Dict[str, Any]:  # noqa: B008
            """Upload a file to storage."""
            try:
                data = await file.read()
                identifier = await self.store(file.filename or "uploaded_file", data)
                return {
                    "identifier": identifier,
                    "filename": file.filename,
                    "size": len(data),
                    "content_type": file.content_type,
                }
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Upload failed: {e}")

        @router.get("/retrieve/{identifier}")
        async def retrieve_data_endpoint(identifier: str) -> Dict[str, Any]:
            """Retrieve data by identifier."""
            data = await self.retrieve(identifier)
            if data is None:
                raise HTTPException(status_code=404, detail="Data not found")

            import base64

            return {
                "identifier": identifier,
                "data": base64.b64encode(data).decode(),
                "size": len(data),
            }

        @router.delete("/delete/{identifier}")
        async def delete_data_endpoint(identifier: str) -> Dict[str, Any]:
            """Delete data by identifier."""
            success = await self.delete(identifier)
            if not success:
                raise HTTPException(status_code=404, detail="Data not found")
            return {"message": "Data deleted successfully"}

        @router.get("/status")
        async def get_storage_status() -> Dict[str, Any]:
            """Get storage plugin status."""
            storage_data = getattr(self, "_storage_data", {})
            return {
                "status": "active",
                "stored_items": len(storage_data),
                "total_size_bytes": sum(len(item["data"]) for item in storage_data.values()),
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the storage plugin."""
        return {
            "collections": {
                "stored_files": {
                    "indexes": [
                        {"field": "identifier", "unique": True},
                        {"field": "key"},
                        {"field": "created_at"},
                        {"field": "size"},
                    ]
                },
                "file_metadata": {
                    "indexes": [{"field": "file_id"}, {"field": "content_type"}, {"field": "tags"}]
                },
                "storage_usage": {
                    "indexes": [{"field": "date"}, {"field": "total_size"}, {"field": "file_count"}]
                },
            },
            "initial_data": {
                "settings": {
                    "max_file_size": 10485760,  # 10MB
                    "allowed_types": ["image/*", "text/*", "application/json"],
                    "compression_enabled": True,
                }
            },
        }

    async def store(self, key: str, data: bytes) -> str:
        """Store data and return identifier."""
        try:
            import hashlib
            from datetime import datetime

            # Generate unique identifier
            timestamp = int(datetime.utcnow().timestamp())
            data_hash = hashlib.sha256(data).hexdigest()[:8]
            identifier = f"{key}_{timestamp}_{data_hash}"

            # Initialize storage if needed
            if not hasattr(self, "_storage_data"):
                self._storage_data = {}

            # Store data with metadata
            storage_entry = {
                "key": key,
                "data": data,
                "identifier": identifier,
                "size": len(data),
                "created_at": datetime.utcnow().isoformat(),
                "content_type": "application/octet-stream",
                "checksum": data_hash,
            }

            self._storage_data[identifier] = storage_entry

            logger.info(f"Stored data with identifier: {identifier} (size: {len(data)} bytes)")
            return identifier

        except Exception as e:
            logger.error(f"Failed to store data: {e}")
            return ""

    async def retrieve(self, identifier: str) -> Optional[bytes]:
        """Retrieve stored data."""
        try:
            if not hasattr(self, "_storage_data"):
                self._storage_data = {}

            storage_entry = self._storage_data.get(identifier)
            if not storage_entry:
                logger.warning(f"Data not found for identifier: {identifier}")
                return None

            data = storage_entry["data"]
            if isinstance(data, (bytes, str)):
                logger.info(
                    f"Retrieved data for identifier: {identifier} (size: {len(data)} bytes)"
                )
                return data if isinstance(data, bytes) else data.encode()
            return None

        except Exception as e:
            logger.error(f"Failed to retrieve data: {e}")
            return None

    async def delete(self, identifier: str) -> bool:
        """Delete stored data."""
        try:
            if not hasattr(self, "_storage_data"):
                self._storage_data = {}

            if identifier in self._storage_data:
                del self._storage_data[identifier]
                logger.info(f"Deleted data for identifier: {identifier}")
                return True
            else:
                logger.warning(f"Data not found for deletion: {identifier}")
                return False

        except Exception as e:
            logger.error(f"Failed to delete data: {e}")
            return False


class WorkflowPlugin(BasePlugin):
    """Base class for workflow automation plugins."""

    def __init__(self) -> None:
        super().__init__()
        self.category = "workflow"
        self._active_workflows: Dict[str, Any] = {}
        self._execution_tasks: List[asyncio.Task[Any]] = []
        self._workflow_state: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize the workflow plugin."""
        return True

    async def shutdown(self) -> None:
        """Shutdown the workflow plugin."""
        logger.info(f"Shutting down workflow plugin: {self.name}")
        # Stop running workflows gracefully
        if hasattr(self, "_active_workflows") and self._active_workflows:
            for workflow_id, workflow in self._active_workflows.items():
                try:
                    logger.info(f"Stopping workflow: {workflow_id}")
                    if hasattr(workflow, "stop"):
                        await workflow.stop()
                except Exception as e:
                    logger.warning(f"Error stopping workflow {workflow_id}: {e}")
        # Cancel workflow execution tasks
        if hasattr(self, "_execution_tasks"):
            for task in self._execution_tasks:
                if not task.done():
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass
        # Save workflow state if needed
        if hasattr(self, "_workflow_state") and self._workflow_state:
            try:
                await self._save_workflow_state()
            except Exception as e:
                logger.warning(f"Error saving workflow state: {e}")
        logger.info(f"Workflow plugin {self.name} shutdown complete")

    async def _save_workflow_state(self) -> None:
        """Save workflow state to persistent storage."""
        if hasattr(self, "_workflow_state") and self._workflow_state:
            logger.info(f"Saving workflow state for {len(self._workflow_state)} workflows")
            # In a real implementation, this would save to database

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for the workflow plugin."""
        from fastapi import APIRouter, HTTPException
        from pydantic import BaseModel

        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}-workflow"])

        class WorkflowExecutionRequest(BaseModel):
            workflow_id: str
            context: Dict[str, Any]

        @router.post("/execute")
        async def execute_workflow_endpoint(request: WorkflowExecutionRequest) -> Dict[str, Any]:
            """Execute a workflow."""
            execution_id = await self.execute_workflow(request.workflow_id, request.context)
            if not execution_id:
                raise HTTPException(status_code=500, detail="Failed to start workflow execution")
            return {"execution_id": execution_id, "workflow_id": request.workflow_id}

        @router.get("/status/{execution_id}")
        async def get_workflow_status_endpoint(execution_id: str) -> Dict[str, Any]:
            """Get workflow execution status."""
            status = await self.get_workflow_status(execution_id)
            details = await self.get_workflow_details(execution_id)
            return {"execution_id": execution_id, "status": status, "details": details}

        @router.get("/executions")
        async def list_workflow_executions(limit: int = 50, offset: int = 0) -> Dict[str, Any]:
            """List workflow executions."""
            executions = getattr(self, "_workflow_executions", {})
            execution_list = list(executions.values())[offset : offset + limit]
            return {"executions": execution_list, "total": len(executions)}

        @router.get("/active")
        async def list_active_workflows() -> Dict[str, Any]:
            """List currently running workflows."""
            active = getattr(self, "_active_workflows", {})
            return {"active_workflows": list(active.values())}

        @router.post("/cancel/{execution_id}")
        async def cancel_workflow_execution(execution_id: str) -> Dict[str, Any]:
            """Cancel a running workflow execution."""
            executions = getattr(self, "_workflow_executions", {})
            active = getattr(self, "_active_workflows", {})

            if execution_id not in executions:
                raise HTTPException(status_code=404, detail="Execution not found")

            if execution_id in active:
                del active[execution_id]
                executions[execution_id]["status"] = "cancelled"
                return {"message": "Workflow cancelled successfully"}
            else:
                return {"message": "Workflow is not currently running"}

        @router.get("/definitions")
        async def list_workflow_definitions() -> Dict[str, Any]:
            """List available workflow definitions."""
            # Mock workflow definitions
            definitions = [
                {
                    "id": "user_onboarding",
                    "name": "User Onboarding",
                    "description": "Process for new user registration",
                    "steps": 5,
                },
                {
                    "id": "data_processing",
                    "name": "Data Processing",
                    "description": "Batch data processing workflow",
                    "steps": 3,
                },
            ]
            return {"workflows": definitions}

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for the workflow plugin."""
        return {
            "collections": {
                "workflow_definitions": {
                    "indexes": [
                        {"field": "workflow_id", "unique": True},
                        {"field": "name"},
                        {"field": "version"},
                        {"field": "created_at"},
                    ]
                },
                "workflow_executions": {
                    "indexes": [
                        {"field": "execution_id", "unique": True},
                        {"field": "workflow_id"},
                        {"field": "status"},
                        {"field": "started_at"},
                    ]
                },
                "execution_steps": {
                    "indexes": [
                        {"field": "execution_id"},
                        {"field": "step_name"},
                        {"field": "status"},
                        {"field": "started_at"},
                    ]
                },
                "workflow_logs": {
                    "indexes": [
                        {"field": "execution_id"},
                        {"field": "timestamp"},
                        {"field": "level"},
                    ]
                },
            },
            "initial_data": {
                "settings": {
                    "max_concurrent_executions": 10,
                    "execution_timeout": 3600,
                    "log_retention_days": 30,
                }
            },
        }

    async def execute_workflow(self, workflow_id: str, context: Dict[str, Any]) -> str:
        """Execute a workflow."""
        try:
            import uuid
            from datetime import datetime

            # Generate execution ID
            execution_id = str(uuid.uuid4())

            # Initialize workflow state if needed
            if not hasattr(self, "_workflow_executions"):
                self._workflow_executions = {}

            execution_record = {
                "execution_id": execution_id,
                "workflow_id": workflow_id,
                "status": "running",
                "context": context,
                "started_at": datetime.utcnow().isoformat(),
                "steps_completed": 0,
                "total_steps": context.get("total_steps", 1),
                "current_step": "initialization",
                "result": None,
                "error": None,
            }

            self._workflow_executions[execution_id] = execution_record

            # Add to active workflows
            if not hasattr(self, "_active_workflows"):
                self._active_workflows = {}
            self._active_workflows[execution_id] = execution_record

            logger.info(f"Starting workflow execution: {workflow_id} with ID: {execution_id}")

            # Simulate workflow execution
            try:
                # Step 1: Initialization
                execution_record["current_step"] = "initialization"
                await asyncio.sleep(0.1)
                execution_record["steps_completed"] += 1

                # Step 2: Processing
                execution_record["current_step"] = "processing"
                await asyncio.sleep(0.2)
                execution_record["steps_completed"] += 1

                # Step 3: Finalization
                execution_record["current_step"] = "finalization"
                await asyncio.sleep(0.1)
                execution_record["steps_completed"] += 1

                # Complete execution
                execution_record["status"] = "completed"
                execution_record["completed_at"] = datetime.utcnow().isoformat()
                execution_record["result"] = {
                    "success": True,
                    "output": f"Workflow {workflow_id} completed successfully",
                    "execution_time_ms": 400,
                }

                # Remove from active workflows
                if execution_id in self._active_workflows:
                    del self._active_workflows[execution_id]

                logger.info(f"Workflow execution completed: {execution_id}")

            except Exception as workflow_error:
                execution_record["status"] = "failed"
                execution_record["error"] = str(workflow_error)
                execution_record["failed_at"] = datetime.utcnow().isoformat()

                # Remove from active workflows
                if execution_id in self._active_workflows:
                    del self._active_workflows[execution_id]

                logger.error(f"Workflow execution failed: {execution_id} - {workflow_error}")

            return execution_id

        except Exception as e:
            logger.error(f"Failed to execute workflow {workflow_id}: {e}")
            return ""

    async def get_workflow_status(self, execution_id: str) -> str:
        """Get workflow execution status."""
        try:
            if not hasattr(self, "_workflow_executions"):
                self._workflow_executions = {}

            execution_record = self._workflow_executions.get(execution_id)
            if not execution_record:
                logger.warning(f"Workflow execution not found: {execution_id}")
                return "not_found"

            status = execution_record["status"]
            logger.info(f"Workflow {execution_id} status: {status}")
            return str(status)

        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}")
            return "error"

    async def get_workflow_details(self, execution_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed workflow execution information."""
        try:
            if not hasattr(self, "_workflow_executions"):
                self._workflow_executions = {}

            execution_record = self._workflow_executions.get(execution_id)
            if not execution_record:
                return None

            return execution_record.copy()

        except Exception as e:
            logger.error(f"Failed to get workflow details: {e}")
            return None


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
        if not hasattr(plugin, "name") or not plugin.name or plugin.name.strip() == "":
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
