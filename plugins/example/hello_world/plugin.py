"""
Hello World Plugin for Nexus Framework
A simple example plugin demonstrating the basics of plugin development.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from nexus.plugins import BasePlugin, HealthStatus


# Request/Response Models
class GreetingRequest(BaseModel):
    """Request model for greeting endpoint."""

    name: str = Field(..., min_length=1, max_length=100, description="Name to greet")
    language: str = Field(default="en", description="Language for greeting")


class GreetingResponse(BaseModel):
    """Response model for greeting endpoint."""

    message: str
    timestamp: datetime
    language: str
    plugin_version: str


class MessageCreate(BaseModel):
    """Model for creating a message."""

    content: str = Field(..., min_length=1, max_length=500)
    author: str = Field(..., min_length=1, max_length=100)
    tags: List[str] = Field(default_factory=list)


class Message(BaseModel):
    """Message model."""

    id: str
    content: str
    author: str
    tags: List[str]
    created_at: datetime
    likes: int = 0


class HelloWorldPlugin(BasePlugin):
    """
    A simple Hello World plugin demonstrating Nexus Framework capabilities.

    Features:
    - Greeting endpoints in multiple languages
    - Message board functionality
    - Event publishing and subscribing
    - Configuration management
    - Health checks
    """

    def __init__(self):
        """Initialize the Hello World plugin."""
        super().__init__()

        # Plugin metadata
        self.name = "hello_world"
        self.category = "example"
        self.version = "1.0.0"
        self.description = "A simple Hello World plugin for Nexus Framework"
        self.author = "Nexus Team"
        self.license = "MIT"

        # Plugin state
        self.greetings = {
            "en": "Hello",
            "es": "Hola",
            "fr": "Bonjour",
            "de": "Hallo",
            "it": "Ciao",
            "pt": "Olá",
            "ja": "こんにちは",
            "zh": "你好",
            "ru": "Привет",
            "ar": "مرحبا",
        }

        self.message_counter = 0
        self.greeting_counter = 0

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        try:
            self.logger.info(f"Initializing {self.name} plugin v{self.version}")

            # Load configuration
            await self._load_configuration()

            # Subscribe to events
            await self._setup_event_handlers()

            # Initialize data
            await self._initialize_data()

            # Mark startup time
            self._startup_time = datetime.utcnow()
            self.initialized = True

            self.logger.info(f"{self.name} plugin initialized successfully")

            # Publish initialization event
            await self.publish_event(
                "hello_world.initialized",
                {"version": self.version, "timestamp": datetime.utcnow().isoformat()},
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to initialize {self.name} plugin: {e}")
            return False

    async def shutdown(self) -> None:
        """Cleanup plugin resources."""
        self.logger.info(f"Shutting down {self.name} plugin")

        # Save current state
        await self._save_state()

        # Unsubscribe from events
        for event_name in list(self._event_subscriptions.keys()):
            await self.unsubscribe_from_event(event_name)

        # Mark shutdown time
        self._shutdown_time = datetime.utcnow()

        # Publish shutdown event
        await self.publish_event(
            "hello_world.shutdown",
            {"version": self.version, "timestamp": datetime.utcnow().isoformat()},
        )

        self.logger.info(f"{self.name} plugin shut down successfully")

    def get_api_routes(self) -> List[APIRouter]:
        """Return API routes for this plugin."""
        router = APIRouter(tags=["Hello World"])

        @router.get("/", response_model=Dict[str, Any])
        async def plugin_info():
            """Get plugin information."""
            return self.get_info()

        @router.get("/greet", response_model=GreetingResponse)
        async def greet(
            name: str = Query(..., description="Name to greet"),
            language: str = Query("en", description="Language code"),
        ):
            """Greet someone in their preferred language."""
            self.greeting_counter += 1

            greeting_word = self.greetings.get(language, self.greetings["en"])
            message = f"{greeting_word}, {name}!"

            # Publish greeting event
            await self.publish_event(
                "hello_world.greeting",
                {
                    "name": name,
                    "language": language,
                    "message": message,
                    "count": self.greeting_counter,
                },
            )

            return GreetingResponse(
                message=message,
                timestamp=datetime.utcnow(),
                language=language,
                plugin_version=self.version,
            )

        @router.post("/greet", response_model=GreetingResponse)
        async def greet_post(request: GreetingRequest):
            """Greet someone using POST method."""
            self.greeting_counter += 1

            greeting_word = self.greetings.get(request.language, self.greetings["en"])
            message = f"{greeting_word}, {request.name}!"

            return GreetingResponse(
                message=message,
                timestamp=datetime.utcnow(),
                language=request.language,
                plugin_version=self.version,
            )

        @router.get("/languages", response_model=Dict[str, str])
        async def list_languages():
            """List available greeting languages."""
            return self.greetings

        @router.post("/languages/{code}")
        async def add_language(code: str, greeting: str):
            """Add a new language greeting."""
            self.greetings[code] = greeting
            await self.set_config("greetings", self.greetings)

            return {"message": f"Added greeting for language: {code}"}

        @router.get("/messages", response_model=List[Message])
        async def list_messages(limit: int = Query(10, ge=1, le=100), offset: int = Query(0, ge=0)):
            """List all messages."""
            messages = await self.get_data("messages", [])
            return messages[offset : offset + limit]

        @router.post("/messages", response_model=Message, status_code=status.HTTP_201_CREATED)
        async def create_message(message_data: MessageCreate):
            """Create a new message."""
            self.message_counter += 1

            message = Message(
                id=f"msg_{self.message_counter}",
                content=message_data.content,
                author=message_data.author,
                tags=message_data.tags,
                created_at=datetime.utcnow(),
                likes=0,
            )

            # Store message
            messages = await self.get_data("messages", [])
            messages.append(message.dict())
            await self.set_data("messages", messages)

            # Publish message created event
            await self.publish_event("hello_world.message_created", message.dict())

            return message

        @router.post("/messages/{message_id}/like")
        async def like_message(message_id: str):
            """Like a message."""
            messages = await self.get_data("messages", [])

            for msg in messages:
                if msg["id"] == message_id:
                    msg["likes"] = msg.get("likes", 0) + 1
                    await self.set_data("messages", messages)

                    # Publish like event
                    await self.publish_event(
                        "hello_world.message_liked",
                        {"message_id": message_id, "likes": msg["likes"]},
                    )

                    return {"message": "Message liked", "likes": msg["likes"]}

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Message {message_id} not found"
            )

        @router.get("/stats")
        async def get_statistics():
            """Get plugin statistics."""
            messages = await self.get_data("messages", [])

            return {
                "greeting_count": self.greeting_counter,
                "message_count": len(messages),
                "total_likes": sum(msg.get("likes", 0) for msg in messages),
                "languages_supported": len(self.greetings),
                "uptime_seconds": self.get_metrics()["uptime_seconds"],
            }

        @router.get("/health")
        async def health_check():
            """Check plugin health."""
            status = await self.health_check()
            return status.dict()

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Return database schema for this plugin."""
        return {
            "collections": {
                "messages": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "author"},
                        {"field": "created_at"},
                    ]
                }
            },
            "initial_data": {
                "messages": [
                    {
                        "id": "msg_welcome",
                        "content": "Welcome to Hello World Plugin!",
                        "author": "System",
                        "tags": ["welcome", "system"],
                        "created_at": datetime.utcnow().isoformat(),
                        "likes": 0,
                    }
                ],
                "config": {"max_message_length": 500, "enable_notifications": True},
            },
        }

    async def health_check(self) -> HealthStatus:
        """Check plugin health status."""
        health = await super().health_check()

        # Add custom health checks
        try:
            messages = await self.get_data("messages", [])
            health.components["messages"] = {"status": "healthy", "count": len(messages)}
        except Exception as e:
            health.components["messages"] = {"status": "unhealthy", "error": str(e)}
            health.healthy = False

        health.metrics.update(
            {
                "greeting_count": self.greeting_counter,
                "message_count": self.message_counter,
                "languages": len(self.greetings),
            }
        )

        return health

    def get_metrics(self) -> Dict[str, float]:
        """Get plugin metrics."""
        metrics = super().get_metrics()

        metrics.update(
            {
                "greetings_total": float(self.greeting_counter),
                "messages_total": float(self.message_counter),
                "languages_supported": float(len(self.greetings)),
            }
        )

        return metrics

    # Private methods
    async def _load_configuration(self) -> None:
        """Load plugin configuration."""
        # Load saved greetings if available
        saved_greetings = await self.get_config("greetings")
        if saved_greetings:
            self.greetings.update(saved_greetings)

        # Load counters
        self.greeting_counter = await self.get_config("greeting_counter", 0)
        self.message_counter = await self.get_config("message_counter", 0)

        self.logger.debug(f"Loaded configuration: {len(self.greetings)} languages")

    async def _setup_event_handlers(self) -> None:
        """Set up event subscriptions."""
        # Subscribe to user events
        await self.subscribe_to_event("user.created", self._handle_user_created)
        await self.subscribe_to_event("system.shutdown", self._handle_system_shutdown)

    async def _initialize_data(self) -> None:
        """Initialize plugin data."""
        # Check if messages exist
        messages = await self.get_data("messages")
        if messages is None:
            # Create initial welcome message
            welcome_message = {
                "id": "msg_welcome",
                "content": "Welcome to Hello World Plugin!",
                "author": "System",
                "tags": ["welcome", "system"],
                "created_at": datetime.utcnow().isoformat(),
                "likes": 0,
            }
            await self.set_data("messages", [welcome_message])
            self.logger.info("Created initial welcome message")

    async def _save_state(self) -> None:
        """Save plugin state."""
        await self.set_config("greeting_counter", self.greeting_counter)
        await self.set_config("message_counter", self.message_counter)
        await self.set_config("greetings", self.greetings)

        self.logger.debug("Plugin state saved")

    async def _handle_user_created(self, event: Any) -> None:
        """Handle user created event."""
        self.logger.info(f"New user created: {event.data.get('username', 'Unknown')}")

        # Create a welcome message for the new user
        welcome_message = {
            "id": f"msg_welcome_{event.data.get('user_id', 'unknown')}",
            "content": f"Welcome to the platform, {event.data.get('username', 'friend')}!",
            "author": "System",
            "tags": ["welcome", "auto-generated"],
            "created_at": datetime.utcnow().isoformat(),
            "likes": 0,
        }

        messages = await self.get_data("messages", [])
        messages.append(welcome_message)
        await self.set_data("messages", messages)

    async def _handle_system_shutdown(self, event: Any) -> None:
        """Handle system shutdown event."""
        self.logger.info("System shutdown event received")
        await self._save_state()
