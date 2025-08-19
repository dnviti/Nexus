"""
Nexus Framework Plugin Routes
HTTP endpoints for plugin discovery, management, and lifecycle control.
"""

import asyncio
import logging
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..core import PluginStatus

logger = logging.getLogger(__name__)


class PluginInfo(BaseModel):
    """Plugin information model for API responses."""

    name: str
    version: str
    description: str
    status: str
    enabled: bool
    author: str = "Unknown"
    category: str = "general"
    route_count: int = 0
    routes: List[Dict[str, Any]] = []


class PluginActionResponse(BaseModel):
    """Response model for plugin actions."""

    message: str
    plugin_name: str
    success: bool
    routes_affected: int = 0


def create_plugins_router(app_instance: Any) -> APIRouter:
    """
    Create plugin management routes.

    Args:
        app_instance: The NexusApp instance

    Returns:
        APIRouter: Configured router with plugin routes
    """
    router = APIRouter(prefix="/api/plugins", tags=["plugins"])

    @router.get("", response_model=Dict[str, List[PluginInfo]])
    async def list_plugins() -> Dict[str, Any]:
        """List all plugins with detailed information including route counts."""
        plugins = []

        # Get all discovered plugins, not just loaded ones
        discovered_plugins = app_instance.plugin_manager._plugin_info

        for plugin_id, info in discovered_plugins.items():
            status = app_instance.plugin_manager.get_plugin_status(plugin_id)

            # Get route information if plugin is active
            route_count = 0
            routes = []
            if (
                app_instance.hot_reload_manager
                and app_instance.hot_reload_manager.is_plugin_active(plugin_id)
            ):
                route_count = app_instance.hot_reload_manager.get_plugin_route_count(plugin_id)
                routes = app_instance.hot_reload_manager.list_plugin_routes(plugin_id)

            plugin_data = PluginInfo(
                name=info.name,
                version=info.version,
                description=info.description,
                status=status.value if status else "unloaded",
                enabled=status == PluginStatus.ENABLED,
                author=info.author,
                category=info.category,
                route_count=route_count,
                routes=routes,
            )
            plugins.append(plugin_data)

        return {"plugins": plugins}

    @router.post("/{plugin_name}/enable", response_model=PluginActionResponse)
    async def enable_plugin(plugin_name: str) -> PluginActionResponse:
        """Enable a plugin and register its routes dynamically."""
        # Check if plugin exists
        plugin_info = app_instance.plugin_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")

        # Check if already enabled
        current_status = app_instance.plugin_manager.get_plugin_status(plugin_name)
        if current_status == PluginStatus.ENABLED:
            route_count = 0
            if app_instance.hot_reload_manager:
                route_count = app_instance.hot_reload_manager.get_plugin_route_count(plugin_name)

            return PluginActionResponse(
                message=f"Plugin {plugin_name} is already enabled",
                plugin_name=plugin_name,
                success=True,
                routes_affected=route_count,
            )

        success = await app_instance.plugin_manager.enable_plugin(plugin_name, enable_routes=True)

        if success:
            # Get route count after enabling
            route_count = 0
            if app_instance.hot_reload_manager:
                route_count = app_instance.hot_reload_manager.get_plugin_route_count(plugin_name)

            return PluginActionResponse(
                message=f"Plugin {plugin_name} enabled successfully. Routes are now available in Swagger UI.",
                plugin_name=plugin_name,
                success=True,
                routes_affected=route_count,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Failed to enable plugin {plugin_name}")

    @router.post("/{plugin_name}/disable", response_model=PluginActionResponse)
    async def disable_plugin(plugin_name: str) -> PluginActionResponse:
        """Disable a plugin and remove its routes dynamically."""
        # Check if plugin exists
        plugin_info = app_instance.plugin_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")

        # Get route count before disabling
        route_count = 0
        if app_instance.hot_reload_manager:
            route_count = app_instance.hot_reload_manager.get_plugin_route_count(plugin_name)

        # Check if already disabled
        current_status = app_instance.plugin_manager.get_plugin_status(plugin_name)
        if current_status != PluginStatus.ENABLED:
            return PluginActionResponse(
                message=f"Plugin {plugin_name} is already disabled",
                plugin_name=plugin_name,
                success=True,
                routes_affected=0,
            )

        success = await app_instance.plugin_manager.disable_plugin(plugin_name, disable_routes=True)

        if success:
            return PluginActionResponse(
                message=f"Plugin {plugin_name} disabled successfully. Routes removed from Swagger UI.",
                plugin_name=plugin_name,
                success=True,
                routes_affected=route_count,
            )
        else:
            raise HTTPException(status_code=400, detail=f"Failed to disable plugin {plugin_name}")

    @router.post("/discover")
    async def discover_plugins() -> Dict[str, Any]:
        """Discover all available plugins and refresh the plugin registry."""
        plugins_path = Path(getattr(app_instance.config.plugins, "directory", "plugins"))

        if not plugins_path.exists():
            return {
                "message": "Plugins directory not found",
                "discovered": 0,
                "plugins": [],
            }

        # Use the plugin manager's discovery method
        try:
            discovered = await app_instance.plugin_manager.discover_plugins(plugins_path)

            # Format the response
            plugin_list = []
            for plugin_info in discovered:
                plugin_id = f"{plugin_info.category}.{plugin_info.name}"
                status = app_instance.plugin_manager.get_plugin_status(plugin_id)

                # Get route information if plugin is active
                route_count = 0
                if (
                    app_instance.hot_reload_manager
                    and app_instance.hot_reload_manager.is_plugin_active(plugin_id)
                ):
                    route_count = app_instance.hot_reload_manager.get_plugin_route_count(plugin_id)

                plugin_data = {
                    "id": plugin_id,
                    "name": plugin_info.name,
                    "category": plugin_info.category,
                    "version": plugin_info.version,
                    "description": plugin_info.description,
                    "author": plugin_info.author,
                    "status": status.value if status else "unloaded",
                    "enabled": status == PluginStatus.ENABLED,
                    "loaded": plugin_id in app_instance.plugin_manager.get_loaded_plugins(),
                    "route_count": route_count,
                    "tags": plugin_info.tags,
                    "permissions": plugin_info.permissions,
                }
                plugin_list.append(plugin_data)

            return {
                "message": f"Discovered {len(discovered)} plugins",
                "discovered": len(discovered),
                "plugins": plugin_list,
            }

        except Exception as e:
            logger.error(f"Error during plugin discovery: {e}")
            raise HTTPException(status_code=500, detail=f"Plugin discovery failed: {str(e)}")

    @router.get("/{plugin_name}/info")
    async def get_plugin_info(plugin_name: str) -> Dict[str, Any]:
        """Get detailed information about a specific plugin."""
        # Get plugin info from memory
        plugin_info = app_instance.plugin_manager.get_plugin_info(plugin_name)
        plugin_status = app_instance.plugin_manager.get_plugin_status(plugin_name)

        if not plugin_info:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")

        # Get route information
        route_count = 0
        routes = []
        is_active = False

        if app_instance.hot_reload_manager:
            is_active = app_instance.hot_reload_manager.is_plugin_active(plugin_name)
            if is_active:
                route_count = app_instance.hot_reload_manager.get_plugin_route_count(plugin_name)
                routes = app_instance.hot_reload_manager.list_plugin_routes(plugin_name)

        # Get persistence status if database is available
        persistence_info = None
        if app_instance.database:
            try:
                enabled_plugins = await app_instance.plugin_manager.get_enabled_plugins_from_db()
                persistence_info = {
                    "persistent": plugin_name in enabled_plugins,
                    "database_available": True,
                }
            except Exception as e:
                persistence_info = {
                    "persistent": False,
                    "database_available": False,
                    "error": True,  # Changed to boolean to match type
                }

        return {
            "plugin_name": plugin_name,
            "info": {
                "name": plugin_info.name,
                "display_name": plugin_info.display_name,
                "category": plugin_info.category,
                "version": plugin_info.version,
                "description": plugin_info.description,
                "author": plugin_info.author,
                "license": plugin_info.license,
                "homepage": plugin_info.homepage,
                "repository": plugin_info.repository,
                "tags": plugin_info.tags,
                "permissions": plugin_info.permissions,
                "dependencies": plugin_info.dependencies,
            },
            "status": {
                "current": plugin_status.value if plugin_status else "unloaded",
                "enabled": plugin_status == PluginStatus.ENABLED,
                "loaded": plugin_name in app_instance.plugin_manager.get_loaded_plugins(),
                "routes_active": is_active,
            },
            "routes": {
                "count": route_count,
                "details": routes,
            },
            "persistence": persistence_info,
        }

    @router.post("/{plugin_name}/reload", response_model=PluginActionResponse)
    async def reload_plugin(plugin_name: str) -> PluginActionResponse:
        """Reload a plugin by disabling and re-enabling it."""
        # Check if plugin exists
        plugin_info = app_instance.plugin_manager.get_plugin_info(plugin_name)
        if not plugin_info:
            raise HTTPException(status_code=404, detail=f"Plugin {plugin_name} not found")

        try:
            # Get initial route count
            initial_route_count = 0
            if app_instance.hot_reload_manager:
                initial_route_count = app_instance.hot_reload_manager.get_plugin_route_count(
                    plugin_name
                )

            # Disable first (if enabled)
            current_status = app_instance.plugin_manager.get_plugin_status(plugin_name)
            was_enabled = current_status == PluginStatus.ENABLED

            if was_enabled:
                await app_instance.plugin_manager.disable_plugin(plugin_name, disable_routes=True)
                logger.info(f"Plugin {plugin_name} disabled for reload")

            # Re-enable
            success = await app_instance.plugin_manager.enable_plugin(
                plugin_name, enable_routes=True
            )

            if success:
                # Get final route count
                final_route_count = 0
                if app_instance.hot_reload_manager:
                    final_route_count = app_instance.hot_reload_manager.get_plugin_route_count(
                        plugin_name
                    )

                return PluginActionResponse(
                    message=f"Plugin {plugin_name} reloaded successfully",
                    plugin_name=plugin_name,
                    success=True,
                    routes_affected=final_route_count,
                )
            else:
                raise HTTPException(
                    status_code=500, detail=f"Failed to re-enable plugin {plugin_name} after reload"
                )

        except Exception as e:
            logger.error(f"Error reloading plugin {plugin_name}: {e}")
            raise HTTPException(status_code=500, detail=f"Plugin reload failed: {str(e)}")

    @router.get("/status/summary")
    async def get_plugins_summary() -> Dict[str, Any]:
        """Get a summary of all plugins and their status."""
        discovered_plugins = app_instance.plugin_manager._plugin_info

        summary: Dict[str, Any] = {
            "total_discovered": len(discovered_plugins),
            "total_loaded": len(app_instance.plugin_manager.get_loaded_plugins()),
            "total_enabled": 0,
            "total_routes": 0,
            "categories": {},
            "status_breakdown": {
                "enabled": 0,
                "disabled": 0,
                "error": 0,
                "unloaded": 0,
            },
        }

        for plugin_id, info in discovered_plugins.items():
            status = app_instance.plugin_manager.get_plugin_status(plugin_id)

            # Count by status
            if status:
                summary["status_breakdown"][status.value] += 1
                if status == PluginStatus.ENABLED:
                    summary["total_enabled"] += 1
            else:
                summary["status_breakdown"]["unloaded"] += 1

            # Count by category
            category = info.category
            if category not in summary["categories"]:
                summary["categories"][category] = {"count": 0, "enabled": 0}
            summary["categories"][category]["count"] += 1

            if status == PluginStatus.ENABLED:
                summary["categories"][category]["enabled"] += 1

                # Count routes for enabled plugins
                if app_instance.hot_reload_manager:
                    summary[
                        "total_routes"
                    ] += app_instance.hot_reload_manager.get_plugin_route_count(plugin_id)

        return summary

    return router
