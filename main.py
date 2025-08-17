"""
Nexus - Main Application Entry Point
A powerful, plugin-based application platform for building modular, scalable applications.
"""

import asyncio
import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import uvicorn
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from nexus.core import (
    AppConfig,
    DatabaseAdapter,
    EventBus,
    PluginManager,
    ServiceRegistry,
    create_default_config,
)
from nexus.auth import AuthenticationManager, create_default_admin
from nexus.api import create_api_router
from nexus.middleware import (
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
)
from nexus.monitoring import HealthCheck, MetricsCollector
from nexus.utils import setup_logging

# Version information
__version__ = "1.0.0"
__author__ = "Nexus Framework Team"

# Setup logging
setup_logging("INFO")
logger = logging.getLogger("nexus.main")


class NexusApplication:
    """
    Main Nexus Framework Application.

    This class orchestrates all core components and manages the plugin ecosystem.
    """

    def __init__(self, config: Optional[AppConfig] = None):
        """
        Initialize the Nexus application.

        Args:
            config: Application configuration. If None, uses default config.
        """
        self.config = config or create_default_config()
        self.app: Optional[FastAPI] = None

        # Core components
        self.db_adapter: Optional[DatabaseAdapter] = None
        self.event_bus = EventBus()
        self.service_registry = ServiceRegistry()
        self.plugin_manager = PluginManager(
            event_bus=self.event_bus, service_registry=self.service_registry
        )
        self.auth_manager = AuthenticationManager()
        # Remove this line - health checks are managed by metrics collector
        self.metrics = MetricsCollector()

        # Runtime state
        self._initialized = False
        self._startup_complete = False

    async def initialize(self) -> None:
        """Initialize all application components."""
        if self._initialized:
            return

        logger.info(f"Initializing Nexus Framework v{__version__}")

        try:
            # Initialize database
            await self._initialize_database()

            # Initialize authentication
            await self._initialize_auth()

            # Initialize plugin system
            await self._initialize_plugins()

            # Initialize service registry with core services
            await self._register_core_services()

            self._initialized = True
            logger.info("Nexus Framework initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize application: {e}")
            raise

    async def _initialize_database(self) -> None:
        """Initialize database connection."""
        logger.info(f"Connecting to database: {self.config.database.type}")

        from nexus.db import create_database_adapter

        self.db_adapter = create_database_adapter(self.config.database)
        await self.db_adapter.connect()

        # Run migrations if needed
        if self.config.database.auto_migrate:
            await self.db_adapter.migrate()

    async def _initialize_auth(self) -> None:
        """Initialize authentication system."""
        logger.info("Initializing authentication system")

        self.auth_manager.initialize(self.db_adapter)

        # Create default admin user if it doesn't exist
        if self.config.auth.create_default_admin:
            await create_default_admin(self.auth_manager)

    async def _initialize_plugins(self) -> None:
        """Discover and load plugins."""
        logger.info("Initializing plugin system")

        # Set plugin database adapter
        self.plugin_manager.set_database(self.db_adapter)

        # Discover available plugins
        plugin_paths = [
            Path("plugins"),  # Local plugins directory
            Path("/usr/share/nexus/plugins"),  # System plugins
            Path.home() / ".nexus" / "plugins",  # User plugins
        ]

        for path in plugin_paths:
            if path.exists():
                logger.info(f"Scanning for plugins in: {path}")
                await self.plugin_manager.discover_plugins(path)

        # Load enabled plugins
        enabled_plugins = await self.db_adapter.get("core.plugins.enabled", [])
        for plugin_id in enabled_plugins:
            try:
                await self.plugin_manager.load_plugin(plugin_id)
                logger.info(f"Loaded plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to load plugin {plugin_id}: {e}")

    async def _register_core_services(self) -> None:
        """Register core services in the service registry."""
        self.service_registry.register("database", self.db_adapter)
        self.service_registry.register("auth", self.auth_manager)
        self.service_registry.register("events", self.event_bus)
        self.service_registry.register("plugins", self.plugin_manager)
        self.service_registry.register("health", self.metrics)
        self.service_registry.register("metrics", self.metrics)

    def create_app(self) -> FastAPI:
        """
        Create and configure the FastAPI application.

        Returns:
            Configured FastAPI application instance.
        """
        if self.app:
            return self.app

        # Create FastAPI app with lifespan management
        self.app = FastAPI(
            title=self.config.app.name,
            description=self.config.app.description,
            version=__version__,
            docs_url="/api/docs",
            redoc_url="/api/redoc",
            openapi_url="/api/openapi.json",
            lifespan=self._lifespan_manager,
        )

        # Configure middleware
        self._configure_middleware()

        # Configure routes
        self._configure_routes()

        # Configure static files
        self._configure_static_files()

        # Configure exception handlers
        self._configure_exception_handlers()

        return self.app

    @asynccontextmanager
    async def _lifespan_manager(self, app: FastAPI):
        """Manage application lifecycle."""
        # Startup
        await self.startup()
        yield
        # Shutdown
        await self.shutdown()

    async def startup(self) -> None:
        """Handle application startup."""
        if self._startup_complete:
            return

        logger.info("Starting Nexus Framework application")

        # Initialize if not already done
        if not self._initialized:
            await self.initialize()

        # Start background tasks
        await self._start_background_tasks()

        # Initialize plugin routes
        self._register_plugin_routes()

        # Perform health checks
        health_results = await self.metrics.run_health_checks()
        overall_health = self.metrics.get_overall_health()
        if overall_health != "healthy":
            logger.warning(f"Application started with health issues: {overall_health}")

        self._startup_complete = True
        logger.info(
            f"Nexus Framework started successfully on {self.config.app.host}:{self.config.app.port}"
        )

    async def shutdown(self) -> None:
        """Handle application shutdown."""
        logger.info("Shutting down Nexus Framework application")

        # Stop background tasks
        await self._stop_background_tasks()

        # Shutdown plugins
        await self.plugin_manager.shutdown_all()

        # Close database connection
        if self.db_adapter:
            await self.db_adapter.disconnect()

        # Cleanup resources
        await self.event_bus.shutdown()

        logger.info("Nexus Framework shutdown complete")

    async def _start_background_tasks(self) -> None:
        """Start background tasks."""
        # Start event bus processing
        asyncio.create_task(self.event_bus.process_events())

        # Start metrics collection
        if self.config.monitoring.metrics_enabled:
            asyncio.create_task(self.metrics.collect_metrics())

        # Start plugin health monitoring
        if self.config.monitoring.health_check_interval:
            asyncio.create_task(self._monitor_plugin_health())

    async def _stop_background_tasks(self) -> None:
        """Stop all background tasks."""
        # Cancel all tasks
        tasks = [t for t in asyncio.all_tasks() if t != asyncio.current_task()]
        for task in tasks:
            task.cancel()

        # Wait for all tasks to complete
        await asyncio.gather(*tasks, return_exceptions=True)

    async def _monitor_plugin_health(self) -> None:
        """Monitor plugin health periodically."""
        while True:
            try:
                await asyncio.sleep(self.config.monitoring.health_check_interval)

                for plugin_id, plugin in self.plugin_manager.get_loaded_plugins().items():
                    try:
                        health = await plugin.health_check()
                        if not health.healthy:
                            logger.warning(
                                f"Plugin {plugin_id} health check failed: {health.message}"
                            )
                    except Exception as e:
                        logger.error(f"Error checking health of plugin {plugin_id}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health monitoring: {e}")

    def _configure_middleware(self) -> None:
        """Configure application middleware."""
        # CORS middleware
        if self.config.security.cors_enabled:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.security.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )

        # Trusted host middleware
        if self.config.security.trusted_hosts:
            self.app.add_middleware(
                TrustedHostMiddleware, allowed_hosts=self.config.security.trusted_hosts
            )

        # Compression middleware
        if self.config.performance.compression_enabled:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000)

        # Custom middleware
        self.app.add_middleware(RequestIDMiddleware)
        self.app.add_middleware(LoggingMiddleware)

        if self.config.security.rate_limiting_enabled:
            self.app.add_middleware(
                RateLimitMiddleware,
                requests=self.config.security.rate_limit_requests,
                period=self.config.security.rate_limit_period,
            )

        self.app.add_middleware(ErrorHandlerMiddleware)

    def _configure_routes(self) -> None:
        """Configure application routes."""

        # Root redirect
        @self.app.get("/", include_in_schema=False)
        async def root():
            return RedirectResponse(url="/api/docs")

        # Health check endpoint
        @self.app.get("/health", tags=["System"])
        async def health_check():
            """System health check endpoint."""
            health_results = await self.metrics.run_health_checks()
            overall_health = self.metrics.get_overall_health()
            return {
                "status": overall_health,
                "version": __version__,
                "checks": {name: status.dict() for name, status in health_results.items()},
                "timestamp": datetime.utcnow().isoformat(),
            }

        # Metrics endpoint
        if self.config.monitoring.metrics_enabled:

            @self.app.get("/metrics", tags=["System"])
            async def metrics():
                """System metrics endpoint."""
                return await self.metrics.get_metrics()

        # Core API routes
        api_router = create_api_router()

        self.app.include_router(api_router, prefix="/api")

    def _register_plugin_routes(self) -> None:
        """Register all plugin routes."""
        for plugin_id, plugin in self.plugin_manager.get_loaded_plugins().items():
            try:
                routes = plugin.get_api_routes()
                for router in routes:
                    prefix = f"/api/plugins/{plugin.category}/{plugin.name}"
                    self.app.include_router(router, prefix=prefix, tags=[plugin.name])
                    logger.debug(f"Registered routes for plugin: {plugin_id}")
            except Exception as e:
                logger.error(f"Failed to register routes for plugin {plugin_id}: {e}")

    def _configure_static_files(self) -> None:
        """Configure static file serving."""
        static_dir = Path("static")
        if static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=static_dir), name="static")

        # Mount plugin static files
        for plugin_id, plugin in self.plugin_manager.get_loaded_plugins().items():
            plugin_static = Path(f"plugins/{plugin.category}/{plugin.name}/static")
            if plugin_static.exists():
                mount_path = f"/static/plugins/{plugin.category}/{plugin.name}"
                self.app.mount(
                    mount_path, StaticFiles(directory=plugin_static), name=f"static-{plugin_id}"
                )

    def _configure_exception_handlers(self) -> None:
        """Configure global exception handlers."""

        @self.app.exception_handler(HTTPException)
        async def http_exception_handler(request: Request, exc: HTTPException):
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "status_code": exc.status_code,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )

        @self.app.exception_handler(Exception)
        async def general_exception_handler(request: Request, exc: Exception):
            logger.exception(f"Unhandled exception: {exc}")
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Internal server error",
                    "status_code": 500,
                    "request_id": getattr(request.state, "request_id", None),
                },
            )


def create_nexus_app(
    config: Optional[AppConfig] = None,
    title: Optional[str] = None,
    description: Optional[str] = None,
    version: Optional[str] = None,
) -> FastAPI:
    """
    Factory function to create a Nexus Framework application.

    Args:
        config: Application configuration
        title: Application title
        description: Application description
        version: Application version

    Returns:
        Configured FastAPI application instance
    """
    # Override config values if provided
    if config is None:
        config = create_default_config()

    if title:
        config.app.name = title
    if description:
        config.app.description = description
    if version:
        config.app.version = version

    # Create and return application
    nexus = NexusApplication(config)
    return nexus.create_app()


def main():
    """Main entry point for running the application."""
    # Load configuration from environment or file
    config = create_default_config()

    # Override from environment variables
    config.app.host = os.getenv("NEXUS_HOST", config.app.host)
    config.app.port = int(os.getenv("NEXUS_PORT", config.app.port))
    config.app.reload = os.getenv("NEXUS_RELOAD", "false").lower() == "true"

    # Create application
    nexus = NexusApplication(config)
    app = nexus.create_app()

    # Run with uvicorn
    uvicorn.run(
        app,
        host=config.app.host,
        port=config.app.port,
        reload=config.app.reload,
        log_level=config.logging.level.lower(),
        access_log=config.logging.access_log,
    )


if __name__ == "__main__":
    main()
