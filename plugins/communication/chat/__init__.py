"""
Chat Plugin for Nexus Platform

This plugin provides comprehensive real-time chat functionality including:
- Real-time messaging with WebSocket support
- Public and private chat rooms
- Direct messaging between users
- File sharing and attachments
- Message reactions and threading
- Typing indicators and presence status
- Push notifications via event bus
- Message search and history
- Chat moderation and administration
- User presence and activity tracking

Architecture:
- models.py: Data models and validation
- websocket_manager.py: WebSocket connection management
- routes.py: API route handlers
- services.py: Business logic and services
- plugin.py: Main plugin class (legacy compatibility)
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from pathlib import Path

from nexus.database import DatabaseAdapter
from nexus.core import EventBus

from .models import (
    ChatRoom,
    ChatMessage,
    MessageReaction,
    ChatNotification,
    UserPresence,
    FileUpload,
    TypingIndicator,
    RoomMember,
)
from .websocket_manager import ConnectionManager
from .services import ChatService
from .routes import ChatRoutes

logger = logging.getLogger(__name__)


class ChatPlugin:
    """Main Chat Plugin Class"""

    def __init__(self):
        self.name = "chat"
        self.version = "1.0.0"
        self.db: Optional[DatabaseAdapter] = None
        self.event_bus: Optional[EventBus] = None
        self.config: Dict[str, Any] = {}
        self.connection_manager = ConnectionManager()
        self.service: Optional[ChatService] = None
        self.routes: Optional[ChatRoutes] = None
        self.template_dir = None

    async def initialize(self, db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize the chat plugin"""
        logger.info("Starting chat plugin initialization...")
        self.db = db
        self.event_bus = event_bus
        self.config = config

        # Initialize service layer
        logger.info("Initializing chat service...")
        self.service = ChatService(db, event_bus, self.connection_manager)

        # Initialize routes
        logger.info("Initializing chat routes...")
        self.routes = ChatRoutes(self)

        # Setup database tables
        logger.info("Setting up chat database...")
        await self._setup_database()

        # Setup event handlers
        logger.info("Setting up chat event handlers...")
        await self._setup_event_handlers()

        # Setup template directory
        self.template_dir = Path(__file__).parent / "templates"

        logger.info("Chat plugin initialized successfully with routes")

    async def _setup_database(self):
        """Setup database tables for chat functionality"""
        # Create tables if they don't exist
        tables = {
            "chat_rooms": """
                CREATE TABLE IF NOT EXISTS chat_rooms (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    room_type TEXT DEFAULT 'public',
                    max_members INTEGER,
                    is_archived BOOLEAN DEFAULT FALSE,
                    metadata TEXT DEFAULT '{}',
                    created_by TEXT,
                    created_at TEXT,
                    updated_at TEXT,
                    last_activity TEXT,
                    last_message_id TEXT
                )
            """,
            "chat_messages": """
                CREATE TABLE IF NOT EXISTS chat_messages (
                    id TEXT PRIMARY KEY,
                    room_id TEXT NOT NULL,
                    sender_id TEXT NOT NULL,
                    sender_name TEXT,
                    content TEXT NOT NULL,
                    message_type TEXT DEFAULT 'text',
                    thread_id TEXT,
                    reply_to TEXT,
                    metadata TEXT DEFAULT '{}',
                    sent_at TEXT,
                    edited_at TEXT,
                    is_deleted BOOLEAN DEFAULT FALSE,
                    deleted_at TEXT,
                    deleted_by TEXT,
                    reactions TEXT DEFAULT '{}'
                )
            """,
            "chat_room_members": """
                CREATE TABLE IF NOT EXISTS chat_room_members (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    room_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT,
                    permissions TEXT DEFAULT '{}',
                    UNIQUE(room_id, user_id)
                )
            """,
            "chat_notifications": """
                CREATE TABLE IF NOT EXISTS chat_notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    data TEXT DEFAULT '{}',
                    priority TEXT DEFAULT 'normal',
                    created_at TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    read_at TEXT
                )
            """,
            "user_presence": """
                CREATE TABLE IF NOT EXISTS user_presence (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'offline',
                    last_seen TEXT,
                    current_room TEXT
                )
            """,
            "chat_files": """
                CREATE TABLE IF NOT EXISTS chat_files (
                    id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    content_type TEXT,
                    size INTEGER,
                    room_id TEXT NOT NULL,
                    user_id TEXT NOT NULL,
                    file_path TEXT,
                    thumbnail_path TEXT,
                    uploaded_at TEXT
                )
            """,
        }

        for table_name, create_sql in tables.items():
            await self.db.execute(create_sql)

        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_room_id ON chat_messages(room_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_messages_sent_at ON chat_messages(sent_at)",
            "CREATE INDEX IF NOT EXISTS idx_chat_room_members_user_id ON chat_room_members(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_chat_notifications_user_id ON chat_notifications(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_presence_user_id ON user_presence(user_id)",
        ]

        for index_sql in indexes:
            await self.db.execute(index_sql)

    async def _setup_event_handlers(self):
        """Setup event handlers"""
        self.event_bus.subscribe("user.login", self._handle_user_login)
        self.event_bus.subscribe("user.logout", self._handle_user_logout)
        self.event_bus.subscribe("user.profile_updated", self._handle_profile_updated)

    async def _handle_user_login(self, event_data: Dict[str, Any]):
        """Handle user login event"""
        user = event_data.get("user")
        if user:
            await self.service.update_user_presence(user.get("id"), "online")
            logger.info(f"User {user.get('id')} logged in - presence updated")

    async def _handle_user_logout(self, event_data: Dict[str, Any]):
        """Handle user logout event"""
        user = event_data.get("user")
        if user:
            await self.service.update_user_presence(user.get("id"), "offline")
            logger.info(f"User {user.get('id')} logged out - presence updated")

    def _render_template(self, template_name: str, context: Dict[str, Any] = None) -> str:
        """Render a template with context"""
        template_path = self.template_dir / f"{template_name}.html"

        if not template_path.exists():
            return f"""
            <div style="padding: 20px; border: 1px solid #ccc; margin: 10px;">
                <h2>Template Not Found</h2>
                <p>Template '{template_name}' not found at {template_path}</p>
            </div>
            """

        try:
            with open(template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Simple variable substitution
            if context:
                for key, value in context.items():
                    placeholder = f"{{{{{key}}}}}"
                    template_content = template_content.replace(placeholder, str(value))

            return template_content

        except Exception as e:
            return f"""
            <div style="padding: 20px; border: 1px solid red; margin: 10px;">
                <h2>Template Error</h2>
                <p>Error rendering template '{template_name}': {e}</p>
            </div>
            """

    async def _render_chat_interface(self, user) -> str:
        """Render chat interface"""
        # Handle both User objects and None
        if user:
            if hasattr(user, "id"):
                # User object
                user_id = user.id
                username = user.username
            else:
                # Dictionary
                user_id = user.get("id", "anonymous")
                username = user.get("username", "Anonymous")
        else:
            user_id = "anonymous"
            username = "Anonymous"

        context = {
            "title": "Chat Interface",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.now().isoformat(),
        }
        html_content = self._render_template("chat", context)
        logger.info(
            f"Template rendered, content type: {type(html_content)}, length: {len(html_content)}"
        )
        logger.info(f"First 200 chars: {html_content[:200]}")
        return html_content

    async def _render_admin_dashboard(self, user) -> str:
        """Render admin dashboard"""
        # Handle both User objects and None
        if user:
            if hasattr(user, "id"):
                # User object
                user_id = user.id
                username = user.username
            else:
                # Dictionary
                user_id = user.get("id", "anonymous")
                username = user.get("username", "Anonymous")
        else:
            user_id = "anonymous"
            username = "Anonymous"

        context = {
            "title": "Chat Administration",
            "user_id": user_id,
            "username": username,
            "timestamp": datetime.now().isoformat(),
        }
        return self._render_template("admin/dashboard", context)

    async def _handle_profile_updated(self, event_data: Dict[str, Any]):
        """Handle user profile update event"""
        user = event_data.get("user")
        if user:
            # Update sender names in recent messages
            await self.db.execute(
                "UPDATE chat_messages SET sender_name = ? WHERE sender_id = ? AND sent_at > ?",
                [
                    user.get("username"),
                    user.get("id"),
                    (datetime.now() - timedelta(hours=24)).isoformat(),
                ],
            )

    def get_api_routes(self):
        """Get API routes for the plugin"""
        logger.info(f"get_api_routes called, self.routes is: {self.routes}")
        if self.routes:
            logger.info(f"Returning router with prefix: {self.routes.router.prefix}")
            return [self.routes.router]
        logger.warning("No routes available - plugin may not be initialized")
        return []

    async def cleanup(self):
        """Cleanup plugin resources"""
        if self.service:
            await self.service.cleanup_old_data()


# Plugin instance
plugin = ChatPlugin()


# Plugin interface functions
def get_plugin():
    """Get plugin instance"""
    return plugin


async def initialize_plugin(db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
    """Initialize plugin"""
    await plugin.initialize(db, event_bus, config)


def get_routes():
    """Get plugin routes"""
    return plugin.get_api_routes()


def get_name():
    """Get plugin name"""
    return plugin.name


def get_version():
    """Get plugin version"""
    return plugin.version
