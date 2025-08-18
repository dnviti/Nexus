"""
Nexus - The Ultimate Plugin-Based Application Platform.

A cutting-edge, plugin-based application platform that enables developers to
create highly modular, maintainable, and scalable applications.
"""

__version__ = "0.1.3"
__author__ = "Nexus Team"
__license__ = "MIT"

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Callable, Dict, List, Optional, Type, Union

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# API imports
from .api import create_api_router, create_core_api_router
from .config import AppConfig, create_default_config, load_config

# Core imports
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

# Database imports
from .database import DatabaseConfig as DatabaseConfigImpl
from .database import create_database_adapter, create_default_database_config
from .plugins import (
    BasePlugin,
    PluginContext,
    PluginLifecycle,
    PluginMetadata,
    plugin_hook,
    requires_dependency,
    requires_permission,
)

# Logging setup
logger = logging.getLogger(__name__)

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
    # Configuration
    "AppConfig",
    "create_default_config",
    "load_config",
    # Decorators and utilities
    "plugin_hook",
    "requires_permission",
    "requires_dependency",
    # Factory functions
    "create_nexus_app",
    "create_plugin",
    # Events
    "Event",
    "EventPriority",
    # Plugin info
    "PluginInfo",
    "PluginStatus",
]


def _convert_config_to_database_config(config_db_config: Any) -> DatabaseConfigImpl:
    """Convert config.DatabaseConfig to database.DatabaseConfig."""
    from .config import DatabaseType

    # Map database types
    type_mapping = {
        DatabaseType.SQLITE: "sqlite",
        DatabaseType.POSTGRESQL: "postgresql",
        DatabaseType.MYSQL: "mysql",
        DatabaseType.MONGODB: "mongodb",
        DatabaseType.REDIS: "redis",
    }

    db_type = type_mapping.get(config_db_config.type, "sqlite")

    # Create database config for database module
    db_config = DatabaseConfigImpl(
        type=db_type,
        host=config_db_config.connection.host,
        port=config_db_config.connection.port,
        database=config_db_config.connection.database,
        username=config_db_config.connection.username,
        password=config_db_config.connection.password,
        path=config_db_config.connection.path or "./nexus.db",
        pool_size=config_db_config.pool.min_size,
        max_overflow=config_db_config.pool.max_overflow,
        pool_timeout=config_db_config.pool.pool_timeout,
    )

    return db_config


class NexusApp:
    """
    Main Nexus Framework application class.

    This class orchestrates the entire application lifecycle, manages plugins,
    handles events, and provides the core functionality of the framework.
    """

    def __init__(
        self,
        title: str = "Nexus Application",
        version: str = "1.0.0",
        description: str = "A Nexus Framework Application",
        config: Optional[AppConfig] = None,
        **kwargs: Any,
    ) -> None:
        """
        Initialize a new Nexus application.

        Args:
            title: Application title
            version: Application version
            description: Application description
            config: Application configuration object
            **kwargs: Additional FastAPI configuration
        """
        self.title = title
        self.version = version
        self.description = description
        self.config = config or create_default_config()

        # Initialize core components
        self.event_bus = EventBus()
        self.service_registry = ServiceRegistry()
        self.plugin_manager = PluginManager(
            event_bus=self.event_bus, service_registry=self.service_registry
        )

        # Initialize database adapter
        self.database: Optional[DatabaseAdapter] = None
        if hasattr(self.config, "database") and self.config.database:
            # Create database adapter from configuration
            if hasattr(self.config.database, "type"):
                converted_config = _convert_config_to_database_config(self.config.database)
                self.database = create_database_adapter(converted_config)
            else:
                # Fallback to default SQLite
                default_config = create_default_database_config()
                self.database = create_database_adapter(default_config)
        else:
            # Use default SQLite database
            default_config = create_default_database_config()
            self.database = create_database_adapter(default_config)

        # Set database for plugin manager
        if self.database:
            self.plugin_manager.set_database(self.database)

        # Create FastAPI application with lifespan management
        self.app = FastAPI(
            title=self.title,
            version=self.version,
            description=self.description,
            lifespan=self._lifespan,
            **kwargs,
        )

        # Setup middleware
        self._setup_middleware()

        # Setup core routes
        self._setup_core_routes()

        # Setup comprehensive core API
        self._setup_core_api()

        # Setup legacy API for backward compatibility
        self._setup_legacy_api()

        # Store startup and shutdown handlers
        self._startup_handlers: List[Callable[[], Any]] = []
        self._shutdown_handlers: List[Callable[[], Any]] = []

        logger.info(f"Initialized Nexus application: {self.title} v{self.version}")

    @asynccontextmanager
    async def _lifespan(self, app: FastAPI) -> AsyncGenerator[None, None]:
        """Manage application lifecycle."""
        # Startup
        await self._startup()
        yield
        # Shutdown
        await self._shutdown()

    async def _startup(self) -> None:
        """Handle application startup."""
        logger.info(f"Starting {self.title}...")

        # Connect to database
        if self.database:
            try:
                await self.database.connect()
                health = await self.database.health_check()
                logger.info(
                    f"Database connected: {health.get('type', 'unknown')} ({health.get('status', 'unknown')})"
                )
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")
                # Fall back to memory adapter
                from .core import MemoryAdapter

                self.database = MemoryAdapter()
                await self.database.connect()
                logger.info("Fell back to in-memory database")

        # Start event bus
        asyncio.create_task(self.event_bus.process_events())
        logger.info("Event bus started")

        # Discover and load plugins
        plugins_path = Path(getattr(self.config.plugins, "directory", "plugins"))
        if plugins_path.exists():
            discovered = await self.plugin_manager.discover_plugins(plugins_path)
            logger.info(f"Discovered {len(discovered)} plugins")

            # Load enabled plugins
            loaded_count = len(self.plugin_manager.get_loaded_plugins())
            logger.info(f"Loaded {loaded_count} plugins")

        # Register plugin routes
        self._register_plugin_routes()

        # Run custom startup handlers
        for handler in self._startup_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

        # Publish startup event
        await self.event_bus.publish(
            event_name="app.started",
            data={"app": self.title, "version": self.version},
        )

        logger.info(f"{self.title} started successfully")

    async def _shutdown(self) -> None:
        """Handle application shutdown."""
        logger.info(f"Shutting down {self.title}...")

        # Publish shutdown event
        await self.event_bus.publish(event_name="app.stopping", data={"app": self.title})

        # Run custom shutdown handlers
        for handler in self._shutdown_handlers:
            if asyncio.iscoroutinefunction(handler):
                await handler()
            else:
                handler()

        # Shutdown plugins
        await self.plugin_manager.shutdown_all()
        logger.info("Plugins shut down")

        # Shutdown event bus
        await self.event_bus.shutdown()
        logger.info("Event bus shut down")

        # Disconnect database
        if self.database:
            await self.database.disconnect()
            logger.info("Database disconnected")

        logger.info(f"{self.title} shut down successfully")

    def _setup_middleware(self) -> None:
        """Set up application middleware."""
        # CORS middleware
        # CORS middleware configuration - handle both config formats
        cors_enabled = False
        cors_origins = ["*"]
        cors_credentials = True
        cors_methods = ["*"]
        cors_headers = ["*"]

        # Check for new config format (nexus.config.AppConfig)
        if hasattr(self.config, "cors") and hasattr(self.config.cors, "enabled"):
            cors_enabled = self.config.cors.enabled
            cors_origins = self.config.cors.origins
            cors_credentials = self.config.cors.credentials
            cors_methods = self.config.cors.methods
            cors_headers = self.config.cors.headers
        # Check for old config format (nexus.core.AppConfig)
        elif hasattr(self.config, "security"):
            cors_enabled = getattr(self.config.security, "cors_enabled", False)
            cors_origins = getattr(self.config.security, "cors_origins", ["*"])
            cors_credentials = True
            cors_methods = ["*"]
            cors_headers = ["*"]

        if cors_enabled:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=cors_origins,
                allow_credentials=cors_credentials,
                allow_methods=cors_methods,
                allow_headers=cors_headers,
            )

        # Custom error handler
        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": {
                        "code": exc.status_code,
                        "message": exc.detail,
                        "path": str(request.url.path),
                    }
                },
            )

        # Global exception handler
        @self.app.exception_handler(Exception)
        async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
            logger.error(f"Unhandled exception: {exc}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": 500,
                        "message": "Internal server error",
                        "path": str(request.url.path),
                    }
                },
            )

    def _setup_core_routes(self) -> None:
        """Set up core application routes."""

        @self.app.get("/health")
        async def health_check() -> Dict[str, Any]:
            """Health check endpoint."""
            return {
                "status": "healthy",
                "app": self.title,
                "version": self.version,
                "plugins": len(self.plugin_manager.get_loaded_plugins()),
            }

        @self.app.get("/api/system/info")
        async def system_info() -> Dict[str, Any]:
            """Get system information."""
            return {
                "app": {
                    "title": self.title,
                    "version": self.version,
                    "description": self.description,
                },
                "framework": {
                    "version": __version__,
                    "author": __author__,
                },
                "plugins": {
                    "loaded": len(self.plugin_manager.get_loaded_plugins()),
                    "enabled": len(
                        [
                            p
                            for p in self.plugin_manager.get_loaded_plugins()
                            if self.plugin_manager.get_plugin_status(p) == PluginStatus.ENABLED
                        ]
                    ),
                },
                "services": {
                    "registered": len(self.service_registry.list_services()),
                },
            }

        @self.app.get("/api/plugins")
        async def list_plugins() -> Dict[str, Any]:
            """List all loaded plugins."""
            plugins = []
            for plugin_name in self.plugin_manager.get_loaded_plugins():
                info = self.plugin_manager.get_plugin_info(plugin_name)
                status = self.plugin_manager.get_plugin_status(plugin_name)
                if info:
                    plugins.append(
                        {
                            "name": info.name,
                            "version": info.version,
                            "description": info.description,
                            "author": info.author,
                            "status": status.value if status else "unknown",
                            "dependencies": info.dependencies,
                            "permissions": info.permissions,
                        }
                    )
            return {"plugins": plugins}

        @self.app.post("/api/plugins/{plugin_name}/enable")
        async def enable_plugin(plugin_name: str) -> Dict[str, Any]:
            """Enable a plugin."""
            success = await self.plugin_manager.enable_plugin(plugin_name)
            if success:
                return {"message": f"Plugin {plugin_name} enabled successfully"}
            raise HTTPException(
                status_code=400,
                detail=f"Failed to enable plugin {plugin_name}",
            )

        @self.app.post("/api/plugins/{plugin_name}/disable")
        async def disable_plugin(plugin_name: str) -> Dict[str, Any]:
            """Disable a plugin."""
            success = await self.plugin_manager.disable_plugin(plugin_name)
            if success:
                return {"message": f"Plugin {plugin_name} disabled successfully"}
            raise HTTPException(
                status_code=400,
                detail=f"Failed to disable plugin {plugin_name}",
            )

    def _register_plugin_routes(self) -> None:
        """Register routes from loaded plugins."""
        for plugin_name in self.plugin_manager.get_loaded_plugins():
            plugin = self.plugin_manager._plugins.get(plugin_name)
            if plugin and hasattr(plugin, "get_api_routes"):
                routes = plugin.get_api_routes()
                if routes:
                    for router in routes:
                        # Add plugin prefix to router
                        prefix = f"/api/plugins/{plugin_name}"
                        if hasattr(router, "prefix") and router.prefix:
                            prefix = f"{prefix}{router.prefix}"

                        self.app.include_router(router, prefix=prefix, tags=[plugin_name])
                        logger.info(f"Registered routes for plugin: {plugin_name}")

    def _setup_core_api(self) -> None:
        """Set up comprehensive core API routes."""
        core_api_router = create_core_api_router()
        self.app.include_router(core_api_router)
        logger.info("Registered comprehensive core API routes")

    def _setup_legacy_api(self) -> None:
        """Set up legacy API routes for backward compatibility."""
        legacy_api_router = create_api_router()
        self.app.include_router(legacy_api_router)
        logger.info("Registered legacy API routes")

    def on_startup(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """Register a startup handler."""
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Callable[[], Any]) -> Callable[[], Any]:
        """Register a shutdown handler."""
        self._shutdown_handlers.append(func)
        return func

    async def emit_event(
        self,
        event_type: str,
        data: Optional[Dict[str, Any]] = None,
        priority: EventPriority = EventPriority.NORMAL,
    ) -> None:
        """Emit an event to the event bus."""
        await self.event_bus.publish(event_name=event_type, data=data or {}, priority=priority)

    def register_service(
        self, name: str, service: Any, interface: Optional[Type[Any]] = None
    ) -> None:
        """Register a service in the service registry."""
        self.service_registry.register(name, service, interface)

    def get_service(self, name: str) -> Optional[Any]:
        """Get a service from the registry."""
        return self.service_registry.get(name)

    def get_plugin(self, name: str) -> Optional[BasePlugin]:
        """Get a loaded plugin by name."""
        return self.plugin_manager._plugins.get(name)

    async def load_plugin(self, plugin_path: str) -> bool:
        """Load a plugin dynamically."""
        return await self.plugin_manager.load_plugin(plugin_path)

    async def unload_plugin(self, plugin_name: str) -> bool:
        """Unload a plugin dynamically."""
        return await self.plugin_manager.unload_plugin(plugin_name)

    def run(self, host: str = "0.0.0.0", port: int = 8000, **kwargs: Any) -> None:  # nosec B104
        """Run the application using uvicorn."""
        uvicorn.run(self.app, host=host, port=port, **kwargs)


def create_nexus_app(
    title: str = "Nexus Application",
    version: str = "1.0.0",
    description: str = "A Nexus Framework Application",
    config: Optional[Union[AppConfig, Dict[str, Any], str]] = None,
    **kwargs: Any,
) -> NexusApp:
    """
    Create a Nexus application.

    Args:
        title: Application title
        version: Application version
        description: Application description
        config: Configuration (AppConfig object, dict, or path to config file)
        **kwargs: Additional FastAPI configuration

    Returns:
        Configured NexusApp instance

    Example:
        >>> app = create_nexus_app(
        ...     title="My App",
        ...     version="1.0.0",
        ...     config="config.yaml"
        ... )
        >>> app.run()
    """
    # Handle different config types
    final_config: AppConfig
    if config is None:
        final_config = create_default_config()
        # Set default database configuration
        if not hasattr(final_config, "database") or not final_config.database:
            from .config import DatabaseConfig

            final_config.database = DatabaseConfig()
    elif isinstance(config, str):
        # Load from file
        final_config = load_config(config)
        # Ensure database config exists
        if not hasattr(final_config, "database") or not final_config.database:
            from .config import DatabaseConfig

            final_config.database = DatabaseConfig()
    elif isinstance(config, dict):
        # Create from dictionary
        config_dict = dict(config)  # Create a copy to avoid modifying original
        if "database" not in config_dict:
            from .config import DatabaseConfig

            config_dict["database"] = DatabaseConfig().dict()
        final_config = AppConfig(**config_dict)
    else:
        # config should be AppConfig instance
        if not isinstance(config, AppConfig):
            raise TypeError(
                f"Invalid config type: {type(config)}. Expected AppConfig, str, dict, or None"
            )
        final_config = config

    return NexusApp(
        title=title,
        version=version,
        description=description,
        config=final_config,
        **kwargs,
    )


def create_plugin(
    name: str,
    version: str = "1.0.0",
    description: str = "",
    author: str = "",
    **kwargs: Any,
) -> Type[BasePlugin]:
    """
    Create a plugin class.

    Args:
        name: Plugin name
        version: Plugin version
        description: Plugin description
        author: Plugin author
        **kwargs: Additional plugin attributes

    Returns:
        Plugin class that can be instantiated

    Example:
        >>> MyPlugin = create_plugin(
        ...     name="my_plugin",
        ...     version="1.0.0",
        ...     description="My awesome plugin"
        ... )
        >>> plugin = MyPlugin()
    """

    class DynamicPlugin(BasePlugin):
        def __init__(self) -> None:
            super().__init__()
            self.metadata = PluginMetadata(
                name=name,
                version=version,
                description=description,
                author=author,
                **kwargs,
            )

    DynamicPlugin.__name__ = f"{name.title().replace('_', '')}Plugin"
    return DynamicPlugin


# Version check
if sys.version_info < (3, 11):
    import warnings

    warnings.warn(
        "Nexus Framework requires Python 3.11 or higher. " "Some features may not work correctly.",
        RuntimeWarning,
        stacklevel=2,
    )
