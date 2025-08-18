"""
Nexus Framework Core Components
Essential building blocks for the plugin-based application framework.
"""

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Import DatabaseConfig from database module
from .database import DatabaseConfig

# Explicit exports
__all__ = [
    "AppConfig",
    "Event",
    "EventPriority",
    "EventBus",
    "PluginInfo",
    "PluginStatus",
    "PluginManager",
    "ServiceRegistry",
    "DatabaseAdapter",
    "MemoryAdapter",
    "TransactionContext",
    "create_database_adapter",
]


# Configuration Classes


@dataclass
class AppConfig:
    """Main application configuration."""

    @dataclass
    class App:
        name: str = "Nexus Application"
        description: str = "A modular application built with Nexus Framework"
        version: str = "1.0.0"
        host: str = "0.0.0.0"  # nosec B104 - Framework default, should be configured in production
        port: int = 8000
        reload: bool = False
        workers: int = 1
        debug: bool = False

    @dataclass
    class Auth:
        secret_key: str = "change-this-secret-key-in-production"
        algorithm: str = "HS256"
        access_token_expire_minutes: int = 30
        refresh_token_expire_days: int = 7
        create_default_admin: bool = True
        default_admin_email: str = "admin@nexus.local"
        default_admin_password: str = "admin"

    @dataclass
    class Security:
        cors_enabled: bool = True
        cors_origins: List[str] = field(default_factory=lambda: ["*"])
        trusted_hosts: List[str] = field(default_factory=list)
        rate_limiting_enabled: bool = True
        rate_limit_requests: int = 100
        rate_limit_period: int = 60
        api_key_header: str = "X-API-Key"

    @dataclass
    class Performance:
        compression_enabled: bool = True
        cache_enabled: bool = True
        cache_ttl: int = 300
        connection_pool_size: int = 100
        request_timeout: int = 30

    @dataclass
    class Monitoring:
        metrics_enabled: bool = True
        health_check_interval: int = 30
        log_requests: bool = True
        log_responses: bool = False
        tracing_enabled: bool = False

    @dataclass
    class Logging:
        level: str = "INFO"
        format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        file: Optional[str] = "nexus.log"
        max_bytes: int = 10485760  # 10MB
        backup_count: int = 5
        access_log: bool = True

    app: App = field(default_factory=App)
    auth: Auth = field(default_factory=Auth)
    security: Security = field(default_factory=Security)
    performance: Performance = field(default_factory=Performance)
    monitoring: Monitoring = field(default_factory=Monitoring)
    logging: Logging = field(default_factory=Logging)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    plugins_dir: str = "plugins"
    data_dir: str = "data"


def create_default_config() -> AppConfig:
    """Create a default application configuration."""
    return AppConfig()


# Event System
class Event(BaseModel):
    """Base event class."""

    name: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: Optional[str] = None
    correlation_id: Optional[str] = None


class EventPriority(Enum):
    """Event priority levels."""

    LOW = 1
    NORMAL = 5
    HIGH = 10
    CRITICAL = 20


class EventBus:
    """Central event bus for inter-component communication."""

    def __init__(self) -> None:
        self._subscribers: Dict[str, List[Callable[..., Any]]] = {}
        self._queue: asyncio.Queue[tuple[int, Event]] = asyncio.Queue()
        self._running = False
        self._processor_task: Optional[asyncio.Task[None]] = None

    async def start(self) -> None:
        """Start the event bus processor."""
        if not self._processor_task:
            self._processor_task = asyncio.create_task(self.process_events())

    async def publish(
        self,
        event_name: str,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
        source: Optional[str] = None,
    ) -> None:
        """Publish an event to the bus."""
        event = Event(name=event_name, data=data or {}, source=source)

        await self._queue.put((priority.value, event))
        logger.debug(f"Published event: {event_name} from {source}")

    def subscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        """Subscribe to an event."""
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []

        self._subscribers[event_name].append(handler)
        logger.debug(f"Subscribed to event: {event_name}")

    def unsubscribe(self, event_name: str, handler: Callable[..., Any]) -> None:
        """Unsubscribe from an event."""
        if event_name in self._subscribers:
            self._subscribers[event_name].remove(handler)

    async def process_events(self) -> None:
        """Process events from the queue."""
        self._running = True

        try:
            while self._running:
                if not await self._check_event_loop():
                    break

                if not await self._process_single_event():
                    break

        finally:
            # Clean shutdown
            self._running = False
            logger.info("Event bus stopped")

    async def _check_event_loop(self) -> bool:
        """Check if event loop is still running."""
        try:
            loop = asyncio.get_running_loop()
            return not loop.is_closed()
        except RuntimeError:
            # No event loop running, exit gracefully
            return False

    async def _process_single_event(self) -> bool:
        """Process a single event from the queue. Returns False if should stop."""
        try:
            # Get event with priority
            priority, event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
            await self._call_event_handlers(event)
            return True

        except asyncio.TimeoutError:
            return True
        except asyncio.CancelledError:
            # Task was cancelled, exit gracefully
            self._running = False
            return False
        except RuntimeError as e:
            return self._handle_runtime_error(e)
        except Exception as e:
            self._safe_log(f"Error processing events: {e}")
            return True

    async def _call_event_handlers(self, event: Event) -> None:
        """Call all subscribers for an event."""
        if event.name not in self._subscribers:
            return

        for handler in self._subscribers[event.name]:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                self._safe_log(f"Error in event handler for {event.name}: {e}")

    def _handle_runtime_error(self, error: RuntimeError) -> bool:
        """Handle runtime errors during event processing."""
        if "no running event loop" in str(error) or "event loop is closed" in str(error):
            # Event loop is shutting down, exit gracefully
            self._running = False
            return False
        else:
            self._safe_log(f"Unexpected runtime error in event processing: {error}")
            return True

    def _safe_log(self, message: str) -> None:
        """Safely log a message, suppressing errors if logger is closed."""
        try:
            logger.error(message)
        except (ValueError, RuntimeError):
            # Logger or event loop is closed, ignore
            pass

    async def shutdown(self) -> None:
        """Shutdown the event bus."""
        self._running = False
        if self._processor_task:
            self._processor_task.cancel()
            try:
                await self._processor_task
            except asyncio.CancelledError:
                pass


# Service Registry
class ServiceRegistry:
    """Central registry for services."""

    def __init__(self) -> None:
        self._services: Dict[str, Any] = {}
        self._interfaces: Dict[Type[Any], List[str]] = {}

    def register(self, name: str, service: Any, interface: Optional[Type[Any]] = None) -> None:
        """Register a service."""
        self._services[name] = service

        if interface:
            if interface not in self._interfaces:
                self._interfaces[interface] = []
            self._interfaces[interface].append(name)

        logger.debug(f"Registered service: {name}")

    def unregister(self, name: str) -> None:
        """Unregister a service."""
        if name in self._services:
            # Remove from interface mappings
            for interface, services in self._interfaces.items():
                if name in services:
                    services.remove(name)

            del self._services[name]
            logger.debug(f"Unregistered service: {name}")

    def get(self, name: str) -> Optional[Any]:
        """Get a service by name."""
        return self._services.get(name)

    def get_by_interface(self, interface: Type[Any]) -> List[Any]:
        """Get all services implementing an interface."""
        service_names = self._interfaces.get(interface, [])
        return [self._services[name] for name in service_names if name in self._services]

    def has_service(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services

    def list_services(self) -> List[str]:
        """List all registered services."""
        return list(self._services.keys())


# Import database components from the new database module
from .database import (
    DatabaseAdapter,
    DatabaseConfig,
    MemoryAdapter,
    TransactionContext,
    create_database_adapter,
)


# Plugin Manager
class PluginInfo(BaseModel):
    """Plugin metadata."""

    name: str
    display_name: str
    category: str
    version: str
    description: str
    author: str
    license: str = "MIT"
    homepage: Optional[str] = None
    repository: Optional[str] = None
    dependencies: Dict[str, List[str]] = Field(default_factory=dict)
    permissions: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    enabled: bool = True
    loaded: bool = False
    health: str = "unknown"


class PluginStatus(Enum):
    """Plugin status."""

    UNLOADED = "unloaded"
    LOADING = "loading"
    LOADED = "loaded"
    ENABLED = "enabled"
    DISABLED = "disabled"
    ERROR = "error"


class PluginManager:
    """Manages plugin lifecycle and operations."""

    def __init__(self, event_bus: EventBus, service_registry: ServiceRegistry):
        self.event_bus = event_bus
        self.service_registry = service_registry
        self._plugins: Dict[str, Any] = {}
        self._plugin_info: Dict[str, PluginInfo] = {}
        self._plugin_status: Dict[str, PluginStatus] = {}
        self.db_adapter: Optional[DatabaseAdapter] = None

    def set_database(self, db_adapter: DatabaseAdapter) -> None:
        """Set the database adapter for plugins."""
        self.db_adapter = db_adapter

    async def discover_plugins(self, path: Path) -> List[PluginInfo]:
        """Discover available plugins in a directory."""
        discovered: List[PluginInfo] = []

        if not path.exists():
            return discovered

        for category_dir in path.iterdir():
            if not category_dir.is_dir():
                continue

            for plugin_dir in category_dir.iterdir():
                if not plugin_dir.is_dir():
                    continue

                manifest_path = plugin_dir / "manifest.json"
                if manifest_path.exists():
                    try:
                        with open(manifest_path) as f:
                            manifest = json.load(f)

                        info = PluginInfo(
                            name=manifest["name"],
                            display_name=manifest.get("display_name", manifest["name"]),
                            category=manifest["category"],
                            version=manifest["version"],
                            description=manifest.get("description", ""),
                            author=manifest.get("author", "Unknown"),
                            license=manifest.get("license", "MIT"),
                            homepage=manifest.get("homepage"),
                            repository=manifest.get("repository"),
                            dependencies=manifest.get("dependencies", {}),
                            permissions=manifest.get("permissions", []),
                            tags=manifest.get("tags", []),
                        )

                        self._plugin_info[f"{info.category}.{info.name}"] = info
                        discovered.append(info)

                        logger.info(f"Discovered plugin: {info.category}.{info.name}")

                    except Exception as e:
                        logger.error(f"Failed to load manifest from {plugin_dir}: {e}")

        return discovered

    async def load_plugin(self, plugin_id: str) -> bool:
        """Load and initialize a plugin."""
        if plugin_id in self._plugins:
            logger.warning(f"Plugin {plugin_id} is already loaded")
            return True

        try:
            self._plugin_status[plugin_id] = PluginStatus.LOADING

            # Ensure plugins directory is in Python path and properly structured
            self._setup_plugins_path()

            # Import plugin module dynamically
            parts = plugin_id.split(".")
            if len(parts) == 2:
                category, name = parts
                module_path = f"plugins.{category}.{name}.plugin"
            else:
                # Handle simple plugin names without category
                # First try to find the plugin in any category
                name = plugin_id
                found_path = self._find_plugin_module_path(name)
                if found_path:
                    module_path = found_path
                else:
                    module_path = f"plugins.{name}.plugin"

            import importlib

            # Clear any cached modules to ensure fresh import
            if module_path in sys.modules:
                importlib.reload(sys.modules[module_path])

            module = importlib.import_module(module_path)

            # Find plugin class (assumes it ends with 'Plugin')
            plugin_class = None
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr_name.endswith("Plugin")
                    and attr_name != "BasePlugin"
                ):
                    plugin_class = attr
                    break

            if not plugin_class:
                raise ValueError(f"No plugin class found in {module_path}")

            # Instantiate plugin
            plugin = plugin_class()

            # Set dependencies
            plugin.db_adapter = self.db_adapter
            plugin.event_bus = self.event_bus
            plugin.service_registry = self.service_registry

            # Initialize plugin
            if await plugin.initialize():
                self._plugins[plugin_id] = plugin
                self._plugin_status[plugin_id] = PluginStatus.LOADED

                # Publish event
                await self.event_bus.publish(
                    "plugin.loaded", {"plugin_id": plugin_id}, source="PluginManager"
                )

                logger.info(f"Successfully loaded plugin: {plugin_id}")
                return True
            else:
                self._plugin_status[plugin_id] = PluginStatus.ERROR
                logger.error(f"Failed to initialize plugin: {plugin_id}")
                return False

        except Exception as e:
            self._plugin_status[plugin_id] = PluginStatus.ERROR
            logger.error(f"Failed to load plugin {plugin_id}: {e}")
            return False

    async def unload_plugin(self, plugin_id: str) -> bool:
        """Unload a plugin."""
        if plugin_id not in self._plugins:
            logger.warning(f"Plugin {plugin_id} is not loaded")
            return True

        try:
            plugin = self._plugins[plugin_id]

            # Shutdown plugin
            await plugin.shutdown()

            # Remove from registry
            del self._plugins[plugin_id]
            self._plugin_status[plugin_id] = PluginStatus.UNLOADED

            # Publish event
            await self.event_bus.publish(
                "plugin.unloaded", {"plugin_id": plugin_id}, source="PluginManager"
            )

            logger.info(f"Successfully unloaded plugin: {plugin_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to unload plugin {plugin_id}: {e}")
            return False

    async def enable_plugin(self, plugin_id: str) -> bool:
        """Enable a plugin."""
        if plugin_id not in self._plugins:
            # Try to load it first
            if not await self.load_plugin(plugin_id):
                return False

        self._plugin_status[plugin_id] = PluginStatus.ENABLED

        # Save to database
        if self.db_adapter:
            enabled_plugins = await self.db_adapter.get("core.plugins.enabled", [])
            if plugin_id not in enabled_plugins:
                enabled_plugins.append(plugin_id)
                await self.db_adapter.set("core.plugins.enabled", enabled_plugins)

        await self.event_bus.publish(
            "plugin.enabled", {"plugin_id": plugin_id}, source="PluginManager"
        )

        return True

    async def disable_plugin(self, plugin_id: str) -> bool:
        """Disable a plugin."""
        if plugin_id in self._plugins:
            await self.unload_plugin(plugin_id)

        self._plugin_status[plugin_id] = PluginStatus.DISABLED

        # Save to database
        if self.db_adapter:
            enabled_plugins = await self.db_adapter.get("core.plugins.enabled", [])
            if plugin_id in enabled_plugins:
                enabled_plugins.remove(plugin_id)
                await self.db_adapter.set("core.plugins.enabled", enabled_plugins)

        await self.event_bus.publish(
            "plugin.disabled", {"plugin_id": plugin_id}, source="PluginManager"
        )

        return True

    def get_loaded_plugins(self) -> Dict[str, Any]:
        """Get all loaded plugins."""
        return self._plugins.copy()

    def get_plugin_info(self, plugin_id: str) -> Optional[PluginInfo]:
        """Get plugin information."""
        return self._plugin_info.get(plugin_id)

    def get_plugin_status(self, plugin_id: str) -> PluginStatus:
        """Get plugin status."""
        return self._plugin_status.get(plugin_id, PluginStatus.UNLOADED)

    async def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin_id in list(self._plugins.keys()):
            await self.unload_plugin(plugin_id)

    def _setup_plugins_path(self) -> None:
        """Setup plugins directory structure and Python path."""
        # Get current working directory
        cwd = Path.cwd()
        plugins_dir = cwd / "plugins"

        # Add current directory to Python path if not already there
        cwd_str = str(cwd)
        if cwd_str not in sys.path:
            sys.path.insert(0, cwd_str)

        # Create plugins directory if it doesn't exist
        plugins_dir.mkdir(exist_ok=True)

        # Create __init__.py files dynamically
        self._ensure_init_files(plugins_dir)

    def _ensure_init_files(self, plugins_dir: Path) -> None:
        """Ensure all necessary __init__.py files exist."""
        # Create main plugins/__init__.py
        init_file = plugins_dir / "__init__.py"
        if not init_file.exists():
            init_file.write_text("# Auto-generated plugins package\n")

        # Create __init__.py for all category directories
        for category_dir in plugins_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("."):
                category_init = category_dir / "__init__.py"
                if not category_init.exists():
                    category_init.write_text(
                        f"# Auto-generated {category_dir.name} category package\n"
                    )

                # Create __init__.py for all plugin directories
                for plugin_dir in category_dir.iterdir():
                    if plugin_dir.is_dir() and not plugin_dir.name.startswith("."):
                        plugin_init = plugin_dir / "__init__.py"
                        if not plugin_init.exists():
                            plugin_init.write_text(
                                f"# Auto-generated {plugin_dir.name} plugin package\n"
                            )

    def _find_plugin_module_path(self, plugin_name: str) -> Optional[str]:
        """Find the full module path for a plugin by searching all categories."""
        plugins_dir = Path.cwd() / "plugins"

        if not plugins_dir.exists():
            return None

        # Search in all category directories
        for category_dir in plugins_dir.iterdir():
            if category_dir.is_dir() and not category_dir.name.startswith("."):
                plugin_dir = category_dir / plugin_name
                if plugin_dir.exists() and (plugin_dir / "plugin.py").exists():
                    return f"plugins.{category_dir.name}.{plugin_name}.plugin"

        return None
