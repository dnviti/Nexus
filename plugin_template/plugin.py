"""
Plugin Template for Nexus Framework

This is a template plugin that demonstrates the standard structure and best practices
for creating Nexus Framework plugins. Use this as a starting point for your own plugins.

Author: Your Name
License: MIT
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from nexus.plugins import BasePlugin, PluginMetadata, PluginLifecycle
from nexus.core import Event, EventPriority
from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import BaseModel, Field

# Set up logging for this plugin
logger = logging.getLogger(__name__)


# ============================================================================
# Pydantic Models for API
# ============================================================================

class ItemCreate(BaseModel):
    """Schema for creating an item."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    value: float = Field(..., ge=0)
    tags: List[str] = []


class ItemUpdate(BaseModel):
    """Schema for updating an item."""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    value: Optional[float] = Field(None, ge=0)
    tags: Optional[List[str]] = None


class Item(BaseModel):
    """Complete item schema."""
    id: str
    name: str
    description: Optional[str]
    value: float
    tags: List[str]
    created_at: datetime
    updated_at: datetime


# ============================================================================
# Main Plugin Class
# ============================================================================

class TemplatePlugin(BasePlugin):
    """
    Template Plugin for Nexus Framework.

    This plugin demonstrates:
    - Basic plugin structure
    - Configuration management
    - API route registration
    - Event handling
    - Service integration
    - Error handling
    - Logging

    Replace this with your plugin's description.
    """

    def __init__(self):
        """Initialize the plugin."""
        super().__init__()

        # Define plugin metadata
        self.metadata = PluginMetadata(
            name="template_plugin",
            version="1.0.0",
            description="A template plugin demonstrating best practices",
            author="Your Name",
            category="example",
            tags=["template", "example", "starter"],
            dependencies=[],  # Add required plugin dependencies here
            permissions=[
                "database.read",
                "database.write",
                "events.publish",
                "api.register_routes"
            ]
        )

        # Initialize plugin state
        self.initialized = False
        self.config = {}
        self.db = None
        self.event_bus = None
        self.cache = None

        # In-memory storage for demo (replace with real database)
        self.items = {}

    # ------------------------------------------------------------------------
    # Lifecycle Methods
    # ------------------------------------------------------------------------

    async def initialize(self, context) -> bool:
        """
        Initialize the plugin.

        Args:
            context: Plugin context providing access to services and configuration

        Returns:
            bool: True if initialization successful, False otherwise
        """
        try:
            logger.info(f"Initializing {self.metadata.name} v{self.metadata.version}")

            # Get configuration for this plugin
            self.config = context.get_config(self.metadata.name, self._get_default_config())
            logger.debug(f"Loaded configuration: {self.config}")

            # Get core services
            self.db = context.get_service("database")
            self.event_bus = context.get_service("event_bus")
            self.cache = context.get_service("cache")

            # Validate required services
            if not self._validate_services():
                logger.error("Required services not available")
                return False

            # Initialize plugin components
            await self._setup_database()
            self._register_event_handlers()

            # Register this plugin's services
            context.register_service(f"{self.metadata.name}.api", self)

            self.initialized = True
            logger.info(f"{self.metadata.name} initialized successfully")

            # Publish initialization event
            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=f"{self.metadata.name}.initialized",
                    data={"version": self.metadata.version},
                    priority=EventPriority.LOW
                ))

            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.metadata.name}: {e}", exc_info=True)
            return False

    async def cleanup(self):
        """
        Clean up plugin resources.

        This method is called when the plugin is being shut down.
        """
        try:
            logger.info(f"Cleaning up {self.metadata.name}")

            # Publish shutdown event
            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=f"{self.metadata.name}.shutdown",
                    data={"timestamp": datetime.utcnow().isoformat()},
                    priority=EventPriority.LOW
                ))

            # Clean up resources
            # Close database connections, cancel tasks, etc.
            self.items.clear()

            self.initialized = False
            logger.info(f"{self.metadata.name} cleaned up successfully")

        except Exception as e:
            logger.error(f"Error during cleanup of {self.metadata.name}: {e}", exc_info=True)

    # ------------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------------

    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for the plugin.

        Returns:
            Dict containing default configuration values
        """
        return {
            "enabled": True,
            "max_items": 1000,
            "cache_ttl": 300,
            "enable_notifications": True,
            "api_rate_limit": 100,
            "custom_setting": "default_value"
        }

    def _validate_services(self) -> bool:
        """
        Validate that required services are available.

        Returns:
            bool: True if all required services are available
        """
        # Add your service validation logic here
        # For this template, we'll just check if services exist
        # In a real plugin, you might check specific capabilities

        if self.config.get("require_database", False) and not self.db:
            logger.error("Database service required but not available")
            return False

        return True

    # ------------------------------------------------------------------------
    # Database Setup
    # ------------------------------------------------------------------------

    async def _setup_database(self):
        """Set up database tables and indexes."""
        # In a real plugin, you would create tables here
        # For example, using SQLAlchemy:
        # Base.metadata.create_all(bind=self.db.engine)

        logger.debug("Database setup completed (using in-memory storage for demo)")

    # ------------------------------------------------------------------------
    # Event Handling
    # ------------------------------------------------------------------------

    def _register_event_handlers(self):
        """Register event handlers for this plugin."""
        if not self.event_bus:
            return

        # Subscribe to relevant events
        self.event_bus.subscribe("user.created", self._handle_user_created)
        self.event_bus.subscribe("system.maintenance", self._handle_maintenance)

        logger.debug("Event handlers registered")

    async def _handle_user_created(self, event: Event):
        """
        Handle user creation event.

        Args:
            event: Event containing user creation data
        """
        logger.info(f"Handling user.created event: {event.data}")
        # Add your event handling logic here

    async def _handle_maintenance(self, event: Event):
        """
        Handle system maintenance event.

        Args:
            event: Event containing maintenance information
        """
        logger.info(f"System maintenance event received: {event.data}")
        # Perform cleanup or preparation for maintenance

    # ------------------------------------------------------------------------
    # API Routes
    # ------------------------------------------------------------------------

    def get_api_routes(self) -> List[APIRouter]:
        """
        Define and return API routes for this plugin.

        Returns:
            List of FastAPI routers with plugin endpoints
        """
        router = APIRouter(
            prefix=f"/api/{self.metadata.name}",
            tags=[self.metadata.name]
        )

        @router.get("/", summary="Get plugin information")
        async def get_plugin_info():
            """Get information about the plugin."""
            return {
                "name": self.metadata.name,
                "version": self.metadata.version,
                "description": self.metadata.description,
                "status": "active" if self.initialized else "inactive",
                "config": {k: v for k, v in self.config.items() if not k.startswith("_")}
            }

        @router.get("/health", summary="Health check")
        async def health_check():
            """Check plugin health status."""
            return {
                "healthy": self.initialized,
                "checks": {
                    "database": self.db is not None,
                    "event_bus": self.event_bus is not None,
                    "cache": self.cache is not None
                }
            }

        @router.post("/items", response_model=Item, status_code=status.HTTP_201_CREATED)
        async def create_item(item_data: ItemCreate):
            """Create a new item."""
            # Generate ID and timestamps
            item_id = str(len(self.items) + 1)
            now = datetime.utcnow()

            # Create item
            item = {
                "id": item_id,
                "name": item_data.name,
                "description": item_data.description,
                "value": item_data.value,
                "tags": item_data.tags,
                "created_at": now,
                "updated_at": now
            }

            # Store item
            self.items[item_id] = item

            # Publish event
            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=f"{self.metadata.name}.item_created",
                    data={"item_id": item_id, "name": item_data.name},
                    priority=EventPriority.NORMAL
                ))

            return Item(**item)

        @router.get("/items", response_model=List[Item])
        async def list_items(
            skip: int = 0,
            limit: int = 100,
            tag: Optional[str] = None
        ):
            """List all items with optional filtering."""
            items = list(self.items.values())

            # Filter by tag if provided
            if tag:
                items = [item for item in items if tag in item.get("tags", [])]

            # Apply pagination
            items = items[skip:skip + limit]

            return [Item(**item) for item in items]

        @router.get("/items/{item_id}", response_model=Item)
        async def get_item(item_id: str):
            """Get a specific item by ID."""
            if item_id not in self.items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item {item_id} not found"
                )

            return Item(**self.items[item_id])

        @router.put("/items/{item_id}", response_model=Item)
        async def update_item(item_id: str, item_update: ItemUpdate):
            """Update an existing item."""
            if item_id not in self.items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item {item_id} not found"
                )

            # Update item fields
            item = self.items[item_id]
            update_data = item_update.dict(exclude_unset=True)

            for field, value in update_data.items():
                item[field] = value

            item["updated_at"] = datetime.utcnow()

            # Publish event
            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=f"{self.metadata.name}.item_updated",
                    data={"item_id": item_id, "changes": update_data},
                    priority=EventPriority.NORMAL
                ))

            return Item(**item)

        @router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
        async def delete_item(item_id: str):
            """Delete an item."""
            if item_id not in self.items:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Item {item_id} not found"
                )

            # Delete item
            del self.items[item_id]

            # Publish event
            if self.event_bus:
                await self.event_bus.publish(Event(
                    type=f"{self.metadata.name}.item_deleted",
                    data={"item_id": item_id},
                    priority=EventPriority.NORMAL
                ))

            return None

        @router.get("/stats", summary="Get statistics")
        async def get_statistics():
            """Get plugin statistics."""
            total_items = len(self.items)
            total_value = sum(item.get("value", 0) for item in self.items.values())
            all_tags = set()

            for item in self.items.values():
                all_tags.update(item.get("tags", []))

            return {
                "total_items": total_items,
                "total_value": total_value,
                "unique_tags": len(all_tags),
                "tags": list(all_tags),
                "average_value": total_value / total_items if total_items > 0 else 0
            }

        return [router]

    # ------------------------------------------------------------------------
    # Public Methods (can be called by other plugins)
    # ------------------------------------------------------------------------

    async def process_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process data (example public method).

        This method can be called by other plugins through the service registry.

        Args:
            data: Data to process

        Returns:
            Processed data
        """
        logger.debug(f"Processing data: {data}")

        # Add your processing logic here
        result = {
            "processed": True,
            "timestamp": datetime.utcnow().isoformat(),
            "input_keys": list(data.keys()),
            "plugin": self.metadata.name
        }

        return result


# Optional: Export the plugin class with a standard name
Plugin = TemplatePlugin
