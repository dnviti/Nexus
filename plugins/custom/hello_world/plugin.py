"""
Hello World Plugin for Nexus Platform
"""

import logging
from typing import Any, Dict, List
from fastapi import APIRouter
from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)

class HelloWorldPlugin(BasePlugin):
    """A simple Hello World plugin."""

    def __init__(self):
        super().__init__()
        self.name = "hello_world"
        self.version = "1.0.0"
        self.category = "custom"

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
        async def get_hello():
            """Get hello message."""
            return {
                "message": "Hello from Nexus Plugin!",
                "plugin": self.name,
                "version": self.version,
                "status": "running"
            }

        @router.get("/greet/{name}")
        async def greet_user(name: str):
            """Greet a specific user."""
            return {
                "message": f"Hello, {name}!",
                "from": "Nexus Hello World Plugin"
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                "greetings": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "name"},
                        {"field": "timestamp"}
                    ]
                }
            }
        }
