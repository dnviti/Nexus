"""
Nexus Framework Application Class
Main application orchestrator for the plugin-based framework.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

# API imports
from .api import create_api_router, create_core_api_router
from .config import AppConfig, create_default_config
from .core import DatabaseAdapter, Event, EventBus, PluginManager, PluginStatus, ServiceRegistry
from .database import DatabaseConfig as DatabaseConfigImpl
from .database import create_database_adapter, create_default_database_config
from .hot_reload import HotReloadManager, create_hot_reload_manager
from .plugins import BasePlugin
from .routes import (
    create_core_router,
    create_debug_router,
    create_events_router,
    create_plugins_router,
)

logger = logging.getLogger(__name__)


def _convert_config_to_database_config(config: Any) -> DatabaseConfigImpl:
    """Convert app database config to database module config."""
    if hasattr(config, "type"):
        # Handle nested config object
        return DatabaseConfigImpl(
            type=getattr(config, "type", "sqlite"),
            host=getattr(config, "host", "localhost"),
            port=getattr(config, "port", 5432),
            username=getattr(config, "username", ""),
            password=getattr(config, "password", ""),
            database=getattr(config, "database", "nexus.db"),
            pool_size=getattr(config, "pool_size", 5),
            max_overflow=getattr(config, "max_overflow", 10),
            pool_timeout=getattr(config, "pool_timeout", 30),
        )
    else:
        # Handle dict-like config
        return DatabaseConfigImpl(
            type=config.get("type", "sqlite"),
            host=config.get("host", "localhost"),
            port=config.get("port", 5432),
            username=config.get("username", ""),
            password=config.get("password", ""),
            database=config.get("database", "nexus.db"),
            pool_size=config.get("pool_size", 5),
            max_overflow=config.get("max_overflow", 10),
            pool_timeout=config.get("pool_timeout", 30),
        )


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
        self._setup_database()

        # Initialize hot reload manager later during startup
        self.hot_reload_manager: Optional[HotReloadManager] = None

        # Initialize FastAPI app
        self.app = FastAPI(
            title=self.title,
            version=self.version,
            description=self.description,
            lifespan=self._lifespan,
            **kwargs,
        )

        # Store WebSocket and SSE clients for event broadcasting
        self._event_websockets: List[WebSocket] = []
        self._event_sse_clients: List[Any] = []

        # Store startup and shutdown handlers
        self._startup_handlers: List[Any] = []
        self._shutdown_handlers: List[Any] = []

        # Setup application components
        self._setup_middleware()
        self._setup_routes()
        self._setup_comprehensive_api()
        self._register_services()

        logger.info(f"Initialized Nexus application: {self.title} v{self.version}")

    def _setup_database(self) -> None:
        """Set up database connection."""
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

    def _setup_middleware(self) -> None:
        """Set up application middleware."""
        # CORS middleware
        cors_config = getattr(self.config, "cors", None)
        if cors_config:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=getattr(cors_config, "allow_origins", ["*"]),
                allow_credentials=getattr(cors_config, "allow_credentials", True),
                allow_methods=getattr(cors_config, "allow_methods", ["*"]),
                allow_headers=getattr(cors_config, "allow_headers", ["*"]),
            )
        else:
            # Default CORS configuration for development
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Request logging middleware
        @self.app.middleware("http")
        async def log_requests(request: Request, call_next: Any) -> Any:
            """Log all HTTP requests."""
            start_time = asyncio.get_event_loop().time()
            response = await call_next(request)
            process_time = asyncio.get_event_loop().time() - start_time

            logger.debug(
                f"{request.method} {request.url.path} - "
                f"{response.status_code} - {process_time:.4f}s"
            )
            return response

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

    def _setup_routes(self) -> None:
        """Set up all application routes using modular routers."""
        # Core system routes
        core_router = create_core_router(self)
        self.app.include_router(core_router)

        # Plugin management routes
        plugins_router = create_plugins_router(self)
        self.app.include_router(plugins_router)

        # Event system routes
        events_router = create_events_router(self)
        self.app.include_router(events_router)

        # Debug and monitoring routes
        debug_router = create_debug_router(self)
        self.app.include_router(debug_router)

        logger.info("Modular routes registered successfully")

    def _register_services(self) -> None:
        """Register core services in the service registry."""
        self.service_registry.register("app", self)
        self.service_registry.register("event_bus", self.event_bus)
        self.service_registry.register("plugin_manager", self.plugin_manager)
        if self.database:
            self.service_registry.register("database", self.database)

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

        # Connect to database if configured
        if self.database:
            try:
                await self.database.connect()
                logger.info("Database connected successfully")
            except Exception as e:
                logger.error(f"Failed to connect to database: {e}")

        # Set global app instance for authentication
        from .auth import set_app_instance

        set_app_instance(self)

        # Set up event broadcasting for debugging
        self.event_bus.set_broadcast_callback(self._broadcast_event_to_clients)

        # Start event bus processing
        asyncio.create_task(self.event_bus.process_events())
        logger.info("Event bus started")

        # Initialize hot reload manager
        self.hot_reload_manager = create_hot_reload_manager(self.app)
        logger.info("Hot reload manager initialized")

        # Connect hot reload manager to plugin manager
        self.plugin_manager.set_hot_reload_manager(self.hot_reload_manager)
        logger.info("Plugin manager connected to hot reload manager")

        # Discover and load plugins
        await self._discover_and_load_plugins()

        # Register plugin routes
        await self._register_plugin_routes()

        # Run custom startup handlers
        await self._run_handlers(self._startup_handlers)

        # Fire startup event
        await self.event_bus.publish(
            event_name="app.startup",
            data={"app": self.title, "version": self.version},
            source="nexus.app",
        )

        logger.info(f"{self.title} started successfully")

    async def _shutdown(self) -> None:
        """Handle application shutdown."""
        logger.info(f"Shutting down {self.title}...")

        # Fire shutdown event
        await self.event_bus.publish(
            event_name="app.shutdown",
            data={"app": self.title},
            source="nexus.app",
        )

        # Run custom shutdown handlers
        await self._run_handlers(self._shutdown_handlers)

        # Shutdown plugins
        await self.plugin_manager.shutdown_all()
        logger.info("Plugins shut down")

        # Shutdown event bus
        await self.event_bus.shutdown()
        logger.info("Event bus shut down")

        # Shutdown database connections
        if self.database:
            try:
                await self.database.disconnect()
                logger.info("Database connections closed")
            except Exception as e:
                logger.warning(f"Error closing database: {e}")

        logger.info(f"{self.title} shutdown complete")

    async def _discover_and_load_plugins(self) -> None:
        """Discover and load plugins from the plugins directory."""
        plugins_path = Path(getattr(self.config.plugins, "directory", "plugins"))
        if plugins_path.exists():
            discovered = await self.plugin_manager.discover_plugins(plugins_path)
            logger.info(f"Discovered {len(discovered)} plugins")

            # Load previously enabled plugins from database
            await self._load_enabled_plugins()
            loaded_count = len(self.plugin_manager.get_loaded_plugins())
            logger.info(f"Loaded {loaded_count} plugins")
        else:
            logger.info("No plugins directory found, skipping plugin discovery")

    def _setup_comprehensive_api(self) -> None:
        """Set up comprehensive API routes."""
        # Create and include core API router
        core_api_router = create_core_api_router()
        self.app.include_router(core_api_router)

        # Create and include legacy API router for backward compatibility
        legacy_api_router = create_api_router()
        self.app.include_router(legacy_api_router)

        logger.info("Comprehensive API routes registered")

    async def _register_plugin_routes(self) -> None:
        """Register routes from all loaded plugins."""
        if not self.hot_reload_manager:
            logger.warning("Hot reload manager not available for plugin route registration")
            return

        loaded_plugins = self.plugin_manager.get_loaded_plugins()
        enabled_count = 0
        for plugin_name in loaded_plugins:
            plugin = self.plugin_manager._plugins.get(plugin_name)
            if plugin:
                # Only register routes for enabled plugins
                plugin_status = self.plugin_manager.get_plugin_status(plugin_name)
                if plugin_status == PluginStatus.ENABLED:
                    success = self.hot_reload_manager.enable_plugin_routes(plugin_name, plugin)
                    if success:
                        enabled_count += 1
                        logger.info(f"Registered routes for enabled plugin: {plugin_name}")
                    else:
                        logger.error(f"Failed to register routes for plugin {plugin_name}")

        logger.info(
            f"Plugin routes registered for {enabled_count}/{len(loaded_plugins)} enabled plugins"
        )

    async def _load_enabled_plugins(self) -> None:
        """Load previously enabled plugins from database."""
        if not self.database:
            logger.warning("No database available for loading enabled plugins")
            return

        try:
            # Clean up enabled plugins list first
            cleaned_count = await self.plugin_manager.cleanup_enabled_plugins_list()
            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} stale plugin entries from database")

            # Get enabled plugins from database
            enabled_plugins = await self.plugin_manager.get_enabled_plugins_from_db()
            logger.info(f"Found {len(enabled_plugins)} previously enabled plugins in database")

            if not enabled_plugins:
                logger.info("No previously enabled plugins to restore")
                return

            # Enable each plugin
            enabled_count = 0
            failed_count = 0

            for plugin_id in enabled_plugins:
                try:
                    success = await self.plugin_manager.enable_plugin(plugin_id)
                    if success:
                        enabled_count += 1
                        logger.info(f"✅ Restored plugin {plugin_id}")
                    else:
                        logger.error(f"❌ Failed to restore plugin {plugin_id}")
                        failed_count += 1
                except Exception as e:
                    logger.error(f"💥 Error restoring plugin {plugin_id}: {e}")
                    failed_count += 1

            # Log summary
            if enabled_count > 0:
                logger.info(f"🎉 Successfully restored {enabled_count} plugins")
            if failed_count > 0:
                logger.warning(f"⚠️ Failed to restore {failed_count} plugins")

        except Exception as e:
            logger.error(f"💥 Failed to load enabled plugins from database: {e}")

    async def _run_handlers(self, handlers: List[Any]) -> None:
        """Run a list of async/sync handlers."""
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler()
                else:
                    handler()
            except Exception as e:
                logger.error(f"Error running handler {handler}: {e}")

    async def _broadcast_event_to_clients(self, event: Event) -> None:
        """Broadcast events to WebSocket and SSE clients for debugging."""
        event_data = {
            "type": "event",
            "name": event.name,
            "data": event.data,
            "source": event.source,
            "timestamp": asyncio.get_event_loop().time(),
        }

        # Broadcast to WebSocket clients
        disconnected_ws = []
        for websocket in self._event_websockets:
            try:
                await websocket.send_json(event_data)
            except Exception:
                disconnected_ws.append(websocket)

        # Remove disconnected WebSocket clients
        for ws in disconnected_ws:
            self._event_websockets.remove(ws)

        # Broadcast to SSE clients
        disconnected_sse = []
        for client_queue in self._event_sse_clients:
            try:
                client_queue.put_nowait(event_data)
            except Exception:
                disconnected_sse.append(client_queue)

        # Remove disconnected SSE clients
        for client in disconnected_sse:
            self._event_sse_clients.remove(client)

    # Public API methods for application control

    def on_startup(self, func: Any) -> Any:
        """Register a startup handler."""
        self._startup_handlers.append(func)
        return func

    def on_shutdown(self, func: Any) -> Any:
        """Register a shutdown handler."""
        self._shutdown_handlers.append(func)
        return func

    async def emit_event(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit an event to the event bus."""
        await self.event_bus.publish(event_name=event_type, data=data or {})

    def register_service(self, name: str, service: Any, interface: Optional[type] = None) -> None:
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
        import uvicorn

        uvicorn.run(self.app, host=host, port=port, **kwargs)
