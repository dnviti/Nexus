"""
my_awesome_plugin Plugin

A my_awesome_plugin plugin for Nexus platform
"""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter
from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)

class MyAwesomePluginPlugin(BasePlugin):
    """A my_awesome_plugin plugin."""

    def __init__(self):
        super().__init__()
        self.name = "my_awesome_plugin"
        self.version = "1.0.0"
        self.category = "business"

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix=f"/plugins/{self.name}", tags=[f"{self.name}"])

        @router.get("/")
        async def get_plugin_info():
            """Get plugin information."""
            return {
                "name": self.name,
                "version": self.version,
                "category": self.category,
                "status": "running"
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_data": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "created_at"}
                    ]
                }
            }
        }
