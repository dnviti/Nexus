"""
Nexus Framework Core Routes
Core system endpoints for health, system information, and basic status.
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter

logger = logging.getLogger(__name__)


def create_core_router(app_instance: Any) -> APIRouter:
    """
    Create core system routes.

    Args:
        app_instance: The NexusApp instance

    Returns:
        APIRouter: Configured router with core routes
    """
    router = APIRouter(tags=["core"])

    @router.get("/health")
    async def health_check() -> Dict[str, Any]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "app": app_instance.title,
            "version": app_instance.version,
            "plugins": len(app_instance.plugin_manager.get_loaded_plugins()),
        }

    @router.get("/api/system/info")
    async def system_info() -> Dict[str, Any]:
        """Get system information."""
        from .. import __author__, __version__

        return {
            "app": {
                "title": app_instance.title,
                "version": app_instance.version,
                "description": app_instance.description,
            },
            "framework": {
                "version": __version__,
                "author": __author__,
            },
            "plugins": {
                "loaded": len(app_instance.plugin_manager.get_loaded_plugins()),
                "enabled": len(
                    [
                        p
                        for p in app_instance.plugin_manager.get_loaded_plugins()
                        if app_instance.plugin_manager.get_plugin_status(p).name == "ENABLED"
                    ]
                ),
            },
            "services": {
                "registered": len(app_instance.service_registry.list_services()),
            },
        }

    return router
