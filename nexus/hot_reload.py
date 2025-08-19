"""
Hot Reload Module for Nexus Plugin System

This module provides hot-swappable plugin functionality, allowing plugins
to be enabled/disabled and their routes to be dynamically registered/unregistered
without restarting the application.
"""

import logging
import weakref
from typing import Any, Dict, List, Optional, Set

from fastapi import APIRouter, FastAPI, HTTPException, Request, Response
from fastapi.routing import APIRoute

logger = logging.getLogger(__name__)


class HotReloadManager:
    """Manages hot-reloading of plugin routes and resources."""

    def __init__(self, app: FastAPI):
        self.app = app
        self.plugin_routers: Dict[str, List[APIRouter]] = {}
        self.plugin_routes_registry: Dict[str, List[APIRoute]] = {}
        self.active_plugins: Set[str] = set()

    def enable_plugin_routes(self, plugin_name: str, plugin_instance: Any) -> bool:
        """
        Enable routes for a plugin by dynamically registering them.

        Args:
            plugin_name: Name of the plugin
            plugin_instance: Instance of the plugin with get_api_routes method

        Returns:
            bool: True if routes were successfully enabled
        """
        try:
            logger.info(f"DEBUG: Starting route registration for plugin {plugin_name}")
            logger.info(f"DEBUG: Plugin instance type: {type(plugin_instance)}")

            if not hasattr(plugin_instance, "get_api_routes"):
                logger.warning(f"Plugin {plugin_name} has no get_api_routes method")
                return False

            routes = plugin_instance.get_api_routes()
            logger.info(
                f"DEBUG: Plugin {plugin_name} returned {len(routes) if routes else 0} routes"
            )

            if not routes:
                logger.info(f"Plugin {plugin_name} has no routes to register")
                return True

            # Store the routers for later cleanup
            self.plugin_routers[plugin_name] = routes
            registered_routes = []

            for router in routes:
                # Create a new router with proper prefix
                prefix = f"/api/plugins/{plugin_name}"
                if hasattr(router, "prefix") and router.prefix:
                    # Remove any existing /plugins prefix from plugin to avoid duplication
                    clean_prefix = router.prefix.replace("/plugins", "").strip("/")
                    if clean_prefix:
                        prefix = f"{prefix}/{clean_prefix}"

                # Create new router with corrected prefix and enhanced tags
                plugin_tags = [f"Plugin: {plugin_name}", "plugins"]
                new_router = APIRouter(prefix=prefix, tags=list(plugin_tags))

                # Copy all routes from the plugin router
                logger.info(f"DEBUG: Router has {len(router.routes)} routes")
                for route in router.routes:
                    logger.info(f"DEBUG: Processing route: {route} (type: {type(route)})")
                    if isinstance(route, APIRoute):
                        logger.info(
                            f"DEBUG: Creating APIRoute for path: {route.path}, methods: {route.methods}"
                        )
                        # Get response_class if it exists
                        response_class = None
                        if hasattr(route, "response_class"):
                            response_class = route.response_class

                        # Create a new route with all the same properties
                        route_kwargs = {
                            "path": route.path,
                            "endpoint": route.endpoint,
                            "methods": route.methods,
                            "name": f"{plugin_name}_{route.name}" if route.name else None,
                            "summary": route.summary,
                            "description": route.description,
                            "response_description": route.response_description,
                            "responses": route.responses,
                            "deprecated": route.deprecated,
                            "operation_id": route.operation_id,
                            "response_model": route.response_model,
                            "status_code": route.status_code,
                            "tags": route.tags or [plugin_name],
                            "dependencies": route.dependencies,
                            "include_in_schema": route.include_in_schema,
                        }

                        # Add response_class if it exists
                        if response_class:
                            route_kwargs["response_class"] = response_class
                            logger.info(f"DEBUG: Preserved response_class: {response_class}")

                        new_route = APIRoute(**route_kwargs)
                        new_router.routes.append(new_route)
                        registered_routes.append(new_route)
                        logger.info(f"DEBUG: Added route {route.path} to new_router")
                        logger.info(f"Route will be available at: {prefix}{route.path}")
                    else:
                        logger.info(f"DEBUG: Skipping non-APIRoute: {type(route)}")

                # Include the router in the main app
                logger.info(
                    f"DEBUG: Including router with {len(new_router.routes)} routes at prefix {prefix}"
                )
                self.app.include_router(new_router)
                logger.info(f"Registered router for plugin {plugin_name} at {prefix}")

            # Store registered routes for cleanup
            self.plugin_routes_registry[plugin_name] = registered_routes
            self.active_plugins.add(plugin_name)

            # Refresh OpenAPI schema to include new routes
            self._refresh_openapi_schema()

            logger.info(
                f"Successfully enabled {len(registered_routes)} routes for plugin {plugin_name}"
            )
            logger.info(f"Plugin {plugin_name} routes are now available in Swagger UI")
            return True

        except Exception as e:
            logger.error(f"Failed to enable routes for plugin {plugin_name}: {e}")
            logger.error(f"DEBUG: Exception details: {type(e).__name__}: {str(e)}")
            import traceback

            logger.error(f"DEBUG: Traceback:\n{traceback.format_exc()}")
            # Cleanup any partially registered routes
            self._cleanup_plugin_routes(plugin_name)
            return False

    def disable_plugin_routes(self, plugin_name: str) -> bool:
        """
        Disable routes for a plugin by removing them from the application.

        Args:
            plugin_name: Name of the plugin

        Returns:
            bool: True if routes were successfully disabled
        """
        try:
            if plugin_name not in self.active_plugins:
                logger.warning(f"Plugin {plugin_name} routes are not currently active")
                return True

            self._cleanup_plugin_routes(plugin_name)
            self.active_plugins.discard(plugin_name)

            # Refresh OpenAPI schema to remove old routes
            self._refresh_openapi_schema()

            logger.info(f"Successfully disabled routes for plugin {plugin_name}")
            logger.info(f"Plugin {plugin_name} routes have been removed from Swagger UI")
            return True

        except Exception as e:
            logger.error(f"Failed to disable routes for plugin {plugin_name}: {e}")
            return False

    def _cleanup_plugin_routes(self, plugin_name: str) -> None:
        """Clean up all routes and routers for a plugin."""
        try:
            # Remove routes from the main app
            if plugin_name in self.plugin_routes_registry:
                routes_to_remove = self.plugin_routes_registry[plugin_name]

                # FastAPI doesn't provide direct route removal, so we need to
                # rebuild the routes list without the plugin routes
                new_routes = []
                for route in self.app.routes:
                    if route not in routes_to_remove:
                        new_routes.append(route)

                self.app.routes.clear()
                self.app.routes.extend(new_routes)

                del self.plugin_routes_registry[plugin_name]

            # Clean up router references
            if plugin_name in self.plugin_routers:
                del self.plugin_routers[plugin_name]

        except Exception as e:
            logger.error(f"Error during cleanup for plugin {plugin_name}: {e}")

    def _refresh_openapi_schema(self) -> None:
        """Refresh the OpenAPI schema to reflect current routes."""
        try:
            # Clear the cached OpenAPI schema so it gets regenerated
            if hasattr(self.app, "openapi_schema"):
                self.app.openapi_schema = None

            # Force regeneration of the OpenAPI schema
            try:
                # This will trigger schema regeneration on next access
                _ = self.app.openapi()
                logger.info("OpenAPI schema regenerated with current plugin routes")
            except Exception as schema_error:
                logger.warning(f"Could not immediately regenerate OpenAPI schema: {schema_error}")

            logger.debug("OpenAPI schema refreshed")
        except Exception as e:
            logger.error(f"Failed to refresh OpenAPI schema: {e}")

    def get_active_plugins(self) -> Set[str]:
        """Get the set of currently active plugins."""
        return self.active_plugins.copy()

    def is_plugin_active(self, plugin_name: str) -> bool:
        """Check if a plugin's routes are currently active."""
        return plugin_name in self.active_plugins

    def get_plugin_route_count(self, plugin_name: str) -> int:
        """Get the number of routes registered for a plugin."""
        return len(self.plugin_routes_registry.get(plugin_name, []))

    def list_plugin_routes(self, plugin_name: str) -> List[Dict[str, Any]]:
        """List all route paths and details for a plugin."""
        routes = self.plugin_routes_registry.get(plugin_name, [])
        route_details = []

        for route in routes:
            if hasattr(route, "path"):
                route_info = {
                    "path": route.path,
                    "methods": list(route.methods) if hasattr(route, "methods") else [],
                    "name": route.name if hasattr(route, "name") else None,
                    "summary": route.summary if hasattr(route, "summary") else None,
                }
                route_details.append(route_info)

        return route_details


class HotReloadablePlugin:
    """Base class for plugins that support hot reloading."""

    def __init__(self) -> None:
        self.hot_reload_manager: Optional[HotReloadManager] = None

    def set_hot_reload_manager(self, manager: HotReloadManager) -> None:
        """Set the hot reload manager for this plugin."""
        self.hot_reload_manager = manager

    def on_hot_enable(self) -> bool:
        """Called when the plugin is hot-enabled. Override for custom logic."""
        return True

    def on_hot_disable(self) -> bool:
        """Called when the plugin is hot-disabled. Override for custom logic."""
        return True

    def get_route_info(self) -> Dict[str, Any]:
        """Get information about this plugin's routes."""
        if not self.hot_reload_manager or not hasattr(self, "name"):
            return {}

        plugin_name = getattr(self, "name", "unknown")
        return {
            "active": self.hot_reload_manager.is_plugin_active(plugin_name),
            "route_count": self.hot_reload_manager.get_plugin_route_count(plugin_name),
            "routes": self.hot_reload_manager.list_plugin_routes(plugin_name),
        }


def create_hot_reload_manager(app: FastAPI) -> HotReloadManager:
    """Create and configure a hot reload manager for the given FastAPI app."""
    manager = HotReloadManager(app)

    # Add a health check endpoint for hot reload status
    @app.get("/api/hot-reload/status")
    async def hot_reload_status() -> Dict[str, Any]:
        """Get hot reload system status."""
        return {
            "active_plugins": list(manager.get_active_plugins()),
            "total_active": len(manager.get_active_plugins()),
            "status": "operational",
        }

    @app.get("/api/hot-reload/plugins/{plugin_name}/info")
    async def plugin_hot_reload_info(plugin_name: str) -> Dict[str, Any]:
        """Get hot reload information for a specific plugin."""
        if not manager.is_plugin_active(plugin_name):
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} is not active")

        return {
            "plugin_name": plugin_name,
            "active": True,
            "route_count": manager.get_plugin_route_count(plugin_name),
            "routes": manager.list_plugin_routes(plugin_name),
        }

    return manager
