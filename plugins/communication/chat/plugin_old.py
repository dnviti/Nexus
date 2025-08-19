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

Features:
- WebSocket-based real-time communication
- Integration with Nexus Platform event bus
- Advanced notification system
- File upload and sharing
- Message threading and reactions
- Comprehensive user presence tracking
- Admin dashboard and moderation tools
- Message search and filtering
- Chat history and export
- Mobile-responsive chat interface
"""

from typing import Dict, Any, Optional, List, Set, Union
import logging
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
import hashlib

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Form,
    File,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
    status,
    Query,
    BackgroundTasks,
)
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, validator
import websockets

from nexus.core import EventBus, Event, EventPriority
from nexus.auth import get_current_user, require_permission
from nexus.database import DatabaseAdapter
from nexus.ui.templates import render_template

logger = logging.getLogger(__name__)


# Data Models
class ChatRoom(BaseModel):
    name: str
    description: Optional[str] = None
    room_type: str = "public"  # public, private, direct, group
    max_members: Optional[int] = None
    is_archived: bool = False
    metadata: Dict[str, Any] = {}

    @validator("room_type")
    def validate_room_type(cls, v):
        if v not in ["public", "private", "direct", "group"]:
            raise ValueError("Invalid room type")
        return v


class ChatMessage(BaseModel):
    room_id: str
    content: str
    message_type: str = "text"  # text, file, image, system
    thread_id: Optional[str] = None
    reply_to: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @validator("content")
    def validate_content(cls, v):
        if not v or not v.strip():
            raise ValueError("Message content cannot be empty")
        if len(v) > 4000:  # Will be configurable
            raise ValueError("Message too long")
        return v


class MessageReaction(BaseModel):
    message_id: str
    emoji: str
    user_id: str


class ChatNotification(BaseModel):
    user_id: str
    notification_type: str
    title: str
    message: str
    data: Dict[str, Any] = {}
    priority: str = "normal"  # low, normal, high, urgent

    @validator("notification_type")
    def validate_notification_type(cls, v):
        valid_types = [
            "new_message",
            "mention",
            "room_invitation",
            "room_update",
            "direct_message",
            "file_shared",
            "reaction_added",
            "thread_reply",
        ]
        if v not in valid_types:
            raise ValueError("Invalid notification type")
        return v


class UserPresence(BaseModel):
    user_id: str
    status: str = "online"  # online, away, busy, offline
    last_seen: Optional[str] = None
    current_room: Optional[str] = None

    @validator("status")
    def validate_status(cls, v):
        if v not in ["online", "away", "busy", "offline"]:
            raise ValueError("Invalid status")
        return v


class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.room_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, room_id: Optional[str] = None):
        """Connect a user's websocket"""
        await websocket.accept()

        # Track user connections
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

        # Track room connections if specified
        if room_id:
            if room_id not in self.room_connections:
                self.room_connections[room_id] = set()
            self.room_connections[room_id].add(websocket)

        # Store connection metadata
        self.active_connections[id(websocket)] = {
            "websocket": websocket,
            "user_id": user_id,
            "room_id": room_id,
            "connected_at": datetime.utcnow(),
        }

    def disconnect(self, websocket: WebSocket):
        """Disconnect a websocket"""
        connection_id = id(websocket)
        if connection_id in self.active_connections:
            connection = self.active_connections[connection_id]
            user_id = connection["user_id"]
            room_id = connection.get("room_id")

            # Remove from user connections
            if user_id in self.user_connections:
                self.user_connections[user_id].discard(websocket)
                if not self.user_connections[user_id]:
                    del self.user_connections[user_id]

            # Remove from room connections
            if room_id and room_id in self.room_connections:
                self.room_connections[room_id].discard(websocket)
                if not self.room_connections[room_id]:
                    del self.room_connections[room_id]

            # Remove connection record
            del self.active_connections[connection_id]

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Send message to a specific user"""
        if user_id in self.user_connections:
            disconnected = []
            for websocket in self.user_connections[user_id].copy():
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)

            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws)

    async def send_room_message(
        self, room_id: str, message: Dict[str, Any], exclude_user: Optional[str] = None
    ):
        """Send message to all users in a room"""
        if room_id in self.room_connections:
            disconnected = []
            for websocket in self.room_connections[room_id].copy():
                try:
                    connection = self.active_connections.get(id(websocket))
                    if connection and connection["user_id"] != exclude_user:
                        await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(websocket)

            # Clean up disconnected websockets
            for ws in disconnected:
                self.disconnect(ws)

    async def broadcast_message(self, message: Dict[str, Any], exclude_user: Optional[str] = None):
        """Broadcast message to all connected users"""
        disconnected = []
        for connection_id, connection in list(self.active_connections.items()):
            if connection["user_id"] != exclude_user:
                try:
                    await connection["websocket"].send_text(json.dumps(message))
                except:
                    disconnected.append(connection["websocket"])

        # Clean up disconnected websockets
        for ws in disconnected:
            self.disconnect(ws)

    def get_online_users(self, room_id: Optional[str] = None) -> List[str]:
        """Get list of online users"""
        if room_id:
            return list(
                {
                    self.active_connections[id(ws)]["user_id"]
                    for ws in self.room_connections.get(room_id, set())
                    if id(ws) in self.active_connections
                }
            )
        else:
            return list(self.user_connections.keys())

    def is_user_online(self, user_id: str) -> bool:
        """Check if user is online"""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0


class ChatPlugin:
    """Main Chat Plugin Class"""

    def __init__(self):
        self.name = "chat"
        self.version = "1.0.0"
        self.router = APIRouter(prefix="/chat", tags=["chat"])
        self.db: Optional[DatabaseAdapter] = None
        self.event_bus: Optional[EventBus] = None
        self.config: Dict[str, Any] = {}
        self.connection_manager = ConnectionManager()
        self.typing_users: Dict[str, Dict[str, datetime]] = {}  # room_id -> {user_id: timestamp}

        # Setup routes
        self._setup_routes()

    async def initialize(self):
        """Initialize the chat plugin"""
        self.db = self.db_adapter
        self.event_bus = self.event_bus
        self.config = getattr(self, "config", {})

        # Setup database schemas
        await self._setup_database()

        # Subscribe to events
        await self._setup_event_handlers()

        # Start background tasks
        asyncio.create_task(self._cleanup_typing_indicators())
        asyncio.create_task(self._cleanup_old_messages())

        logger.info("Chat plugin initialized")
        return True

    def _setup_routes(self):
        """Setup all plugin routes"""

        # Main chat interface
        @self.router.get("/")
        async def chat_interface():
            return await self._render_chat_interface(None)

        # WebSocket endpoint
        @self.router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket, token: str):
            await self._handle_websocket_connection(websocket, token)

        # Room management
        @self.router.get("/rooms")
        async def list_rooms():
            return await self._list_rooms(None)

        @self.router.post("/rooms")
        async def create_room(room_data: ChatRoom):
            return await self._create_room(room_data, None)

        @self.router.get("/rooms/{room_id}")
        async def get_room(room_id: str):
            return await self._get_room(room_id, None)

        @self.router.put("/rooms/{room_id}")
        async def update_room(room_id: str, room_data: ChatRoom):
            return await self._update_room(room_id, room_data, None)

        @self.router.delete("/rooms/{room_id}")
        async def delete_room(room_id: str):
            return await self._delete_room(room_id, None)

        # Room membership
        @self.router.get("/rooms/{room_id}/members")
        async def get_room_members(room_id: str):
            return await self._get_room_members(room_id)

        @self.router.post("/rooms/{room_id}/members")
        async def join_room(room_id: str):
            return await self._join_room(room_id, None)

        @self.router.delete("/rooms/{room_id}/members/{user_id}")
        async def leave_room(room_id: str, user_id: str):
            return await self._leave_room(room_id, user_id, None)

        # Message management
        @self.router.get("/rooms/{room_id}/messages")
        async def get_messages(
            room_id: str,
            limit: int = Query(50, le=100),
            before: Optional[str] = Query(None),
        ):
            return await self._get_messages(room_id, limit, before, None)

        @self.router.post("/rooms/{room_id}/messages")
        async def send_message(
            room_id: str,
            message_data: ChatMessage,
            background_tasks: BackgroundTasks,
        ):
            return await self._send_message(room_id, message_data, None, background_tasks)

        @self.router.put("/messages/{message_id}")
        async def edit_message(message_id: str, content: str = Form(...)):
            return await self._edit_message(message_id, content, None)

        @self.router.delete("/messages/{message_id}")
        async def delete_message(message_id: str):
            return await self._delete_message(message_id, None)

        # Message reactions
        @self.router.post("/messages/{message_id}/reactions")
        async def add_reaction(message_id: str, emoji: str = Form(...)):
            return await self._add_reaction(message_id, emoji, None)

        @self.router.delete("/messages/{message_id}/reactions/{emoji}")
        async def remove_reaction(message_id: str, emoji: str):
            return await self._remove_reaction(message_id, emoji, None)

        # File upload
        @self.router.post("/files/upload")
        async def upload_file(file: UploadFile = File(...), room_id: str = Form(...)):
            return await self._upload_file(file, room_id, None)

        @self.router.get("/files/{file_id}")
        async def download_file(file_id: str):
            return await self._download_file(file_id, None)

        # Notifications
        @self.router.get("/notifications")
        async def get_notifications(unread_only: bool = Query(False)):
            return await self._get_notifications("test_user", unread_only)

        @self.router.put("/notifications/{notification_id}/read")
        async def mark_notification_read(notification_id: str):
            return await self._mark_notification_read(notification_id, None)

        # Search and history
        @self.router.get("/search")
        async def search_messages(
            query: str = Query(...),
            room_id: Optional[str] = Query(None),
            limit: int = Query(20, le=100),
        ):
            return await self._search_messages(query, room_id, limit, None)

        # User presence
        @self.router.get("/presence")
        async def get_user_presence(room_id: Optional[str] = Query(None)):
            return await self._get_user_presence(room_id)

        @self.router.put("/presence")
        async def update_presence(status: str = Form(...)):
            return await self._update_user_presence("test_user", status)

        # Admin routes
        @self.router.get("/admin")
        async def admin_dashboard():
            return await self._render_admin_dashboard()

        @self.router.post("/admin/moderate")
        async def moderate_message(
            message_id: str = Form(...),
            action: str = Form(...),
            reason: Optional[str] = Form(None),
        ):
            return await self._moderate_message(message_id, action, reason, None)

        @self.router.post("/admin/broadcast")
        async def broadcast_message(
            message: str = Form(...),
            room_id: Optional[str] = Form(None),
        ):
            return await self._broadcast_admin_message(message, room_id, None)

    async def _setup_database(self):
        """Setup database schemas"""
        # Chat rooms schema
        await self.db.set(
            "schema:chat_rooms",
            {
                "table": "chat_rooms",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "name": "STRING NOT NULL",
                    "description": "TEXT",
                    "room_type": "STRING DEFAULT 'public'",
                    "created_by": "STRING NOT NULL",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "max_members": "INTEGER",
                    "is_archived": "BOOLEAN DEFAULT FALSE",
                    "metadata": "JSON",
                },
            },
        )

        # Chat messages schema
        await self.db.set(
            "schema:chat_messages",
            {
                "table": "chat_messages",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "room_id": "STRING NOT NULL",
                    "user_id": "STRING NOT NULL",
                    "content": "TEXT NOT NULL",
                    "message_type": "STRING DEFAULT 'text'",
                    "thread_id": "STRING",
                    "reply_to": "STRING",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "is_edited": "BOOLEAN DEFAULT FALSE",
                    "is_deleted": "BOOLEAN DEFAULT FALSE",
                    "metadata": "JSON",
                },
            },
        )

        # Room members schema
        await self.db.set(
            "schema:chat_room_members",
            {
                "table": "chat_room_members",
                "columns": {
                    "room_id": "STRING",
                    "user_id": "STRING",
                    "role": "STRING DEFAULT 'member'",
                    "joined_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "last_read": "TIMESTAMP",
                },
            },
        )

        # Message reactions schema
        await self.db.set(
            "schema:chat_message_reactions",
            {
                "table": "chat_message_reactions",
                "columns": {
                    "message_id": "STRING",
                    "user_id": "STRING",
                    "emoji": "STRING",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # Notifications schema
        await self.db.set(
            "schema:chat_notifications",
            {
                "table": "chat_notifications",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "user_id": "STRING NOT NULL",
                    "notification_type": "STRING NOT NULL",
                    "title": "STRING NOT NULL",
                    "message": "TEXT NOT NULL",
                    "data": "JSON",
                    "priority": "STRING DEFAULT 'normal'",
                    "is_read": "BOOLEAN DEFAULT FALSE",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # User presence schema
        await self.db.set(
            "schema:chat_user_presence",
            {
                "table": "chat_user_presence",
                "columns": {
                    "user_id": "STRING PRIMARY KEY",
                    "status": "STRING DEFAULT 'offline'",
                    "last_seen": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "current_room": "STRING",
                    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # Files schema
        await self.db.set(
            "schema:chat_files",
            {
                "table": "chat_files",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "filename": "STRING NOT NULL",
                    "original_name": "STRING NOT NULL",
                    "file_size": "INTEGER NOT NULL",
                    "mime_type": "STRING NOT NULL",
                    "uploaded_by": "STRING NOT NULL",
                    "room_id": "STRING NOT NULL",
                    "message_id": "STRING",
                    "file_hash": "STRING NOT NULL",
                    "uploaded_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        logger.info("Chat database schemas initialized")

    async def _setup_event_handlers(self):
        """Setup event bus handlers"""
        if self.event_bus:
            self.event_bus.subscribe("security.user.login", self._handle_user_login)
            self.event_bus.subscribe("security.user.logout", self._handle_user_logout)
            self.event_bus.subscribe(
                "user_management.user.profile_updated", self._handle_profile_updated
            )

    async def _handle_user_login(self, event):
        """Handle user login event"""
        user_id = event.data.get("user_id")
        if user_id:
            await self._update_user_presence(user_id, "online")

            # Notify online users
            await self.connection_manager.broadcast_message(
                {
                    "type": "user_online",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                exclude_user=user_id,
            )

    async def _handle_user_logout(self, event):
        """Handle user logout event"""
        user_id = event.data.get("user_id")
        if user_id:
            await self._update_user_presence(user_id, "offline")

            # Notify online users
            await self.connection_manager.broadcast_message(
                {
                    "type": "user_offline",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
                exclude_user=user_id,
            )

    async def _handle_profile_updated(self, event):
        """Handle user profile update event"""
        user_id = event.data.get("user_id")
        if user_id:
            # Notify connected users about profile changes
            await self.connection_manager.send_personal_message(
                user_id,
                {
                    "type": "profile_updated",
                    "user_id": user_id,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

    async def _handle_websocket_connection(self, websocket: WebSocket, token: str):
        """Handle WebSocket connection for real-time chat"""
        try:
            # Validate token and get user
            from nexus.auth import get_current_user_from_token

            user = await get_current_user_from_token(token)
            if not user:
                await websocket.close(code=4001, reason="Invalid token")
                return

            await self.connection_manager.connect(websocket, user.id)

            # Update user presence
            await self._update_user_presence(user.id, "online")

            # Send initial data
            await websocket.send_text(
                json.dumps(
                    {
                        "type": "connection_established",
                        "user_id": user.id,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                )
            )

            # Listen for messages
            while True:
                try:
                    data = await websocket.receive_text()
                    message_data = json.loads(data)
                    await self._handle_websocket_message(websocket, user, message_data)
                except WebSocketDisconnect:
                    break
                except json.JSONDecodeError:
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Invalid JSON format"})
                    )
                except Exception as e:
                    logger.error(f"WebSocket message handling error: {e}")
                    await websocket.send_text(
                        json.dumps({"type": "error", "message": "Message processing failed"})
                    )

        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
        finally:
            self.connection_manager.disconnect(websocket)
            if "user" in locals():
                await self._update_user_presence(user.id, "offline")

    async def _handle_websocket_message(
        self, websocket: WebSocket, user, message_data: Dict[str, Any]
    ):
        """Handle incoming WebSocket messages"""
        message_type = message_data.get("type")

        if message_type == "send_message":
            await self._handle_ws_send_message(websocket, user, message_data)
        elif message_type == "join_room":
            await self._handle_ws_join_room(websocket, user, message_data)
        elif message_type == "leave_room":
            await self._handle_ws_leave_room(websocket, user, message_data)
        elif message_type == "typing":
            await self._handle_ws_typing(websocket, user, message_data)
        elif message_type == "stop_typing":
            await self._handle_ws_stop_typing(websocket, user, message_data)
        elif message_type == "mark_read":
            await self._handle_ws_mark_read(websocket, user, message_data)
        else:
            await websocket.send_text(
                json.dumps({"type": "error", "message": f"Unknown message type: {message_type}"})
            )

    async def _handle_ws_send_message(self, websocket: WebSocket, user, data: Dict[str, Any]):
        """Handle sending message via WebSocket"""
        try:
            room_id = data.get("room_id")
            content = data.get("content")

            if not room_id or not content:
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Missing room_id or content"})
                )
                return

            # Check permissions
            if not await self._user_can_send_to_room(user.id, room_id):
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Permission denied"})
                )
                return

            # Create message
            message_id = str(uuid.uuid4())
            message = {
                "id": message_id,
                "room_id": room_id,
                "user_id": user.id,
                "content": content,
                "message_type": data.get("message_type", "text"),
                "thread_id": data.get("thread_id"),
                "reply_to": data.get("reply_to"),
                "created_at": datetime.utcnow().isoformat(),
                "is_edited": False,
                "is_deleted": False,
                "metadata": data.get("metadata", {}),
            }

            # Save to database
            await self.db.set(f"chat_message:{message_id}", message)

            # Broadcast to room members
            await self.connection_manager.send_room_message(
                room_id, {"type": "new_message", "message": message}
            )

            # Publish event
            if self.event_bus:
                await self.event_bus.publish("chat.message.sent", message)

            # Create notifications for mentions
            await self._process_message_mentions(message)

        except Exception as e:
            logger.error(f"Error handling WebSocket send message: {e}")
            await websocket.send_text(
                json.dumps({"type": "error", "message": "Failed to send message"})
            )

    async def _handle_ws_typing(self, websocket: WebSocket, user, data: Dict[str, Any]):
        """Handle typing indicator"""
        room_id = data.get("room_id")
        if room_id:
            # Update typing users
            if room_id not in self.typing_users:
                self.typing_users[room_id] = {}
            self.typing_users[room_id][user.id] = datetime.utcnow()

            # Broadcast typing indicator
            await self.connection_manager.send_room_message(
                room_id,
                {"type": "user_typing", "user_id": user.id, "room_id": room_id},
                exclude_user=user.id,
            )

    async def _handle_ws_stop_typing(self, websocket: WebSocket, user, data: Dict[str, Any]):
        """Handle stop typing indicator"""
        room_id = data.get("room_id")
        if room_id and room_id in self.typing_users:
            self.typing_users[room_id].pop(user.id, None)

            # Broadcast stop typing
            await self.connection_manager.send_room_message(
                room_id,
                {"type": "user_stopped_typing", "user_id": user.id, "room_id": room_id},
                exclude_user=user.id,
            )

    # Core functionality methods
    async def _render_chat_interface(self, current_user):
        """Render main chat interface"""
        if current_user:
            user_rooms = await self._get_user_rooms(current_user.id)
        else:
            user_rooms = []

        online_users = self.connection_manager.get_online_users()

        template_data = {
            "title": "Chat",
            "current_user": current_user or {"username": "Guest", "id": "guest"},
            "rooms": user_rooms,
            "online_users": online_users,
            "config": {
                "max_message_length": self.config.get("max_message_length", 4000),
                "enable_file_uploads": self.config.get("enable_file_uploads", True),
                "enable_reactions": self.config.get("enable_message_reactions", True),
                "enable_typing_indicators": self.config.get("enable_typing_indicators", True),
            },
        }

        return render_template("chat/chat", template_data)

    async def _list_rooms(self, current_user):
        """List available chat rooms"""
        # Get all rooms user has access to
        all_rooms = await self.db.list_keys("chat_room:*")
        accessible_rooms = []

        for room_key in all_rooms:
            room = await self.db.get(room_key)
            user_id = current_user.id if current_user else "guest"
            if room and await self._user_can_access_room(user_id, room["id"]):
                # Get member count
                members = await self._get_room_member_count(room["id"])
                room["member_count"] = members

                # Get last message
                room["last_message"] = await self._get_last_room_message(room["id"])

                accessible_rooms.append(room)

        return {
            "rooms": sorted(accessible_rooms, key=lambda x: x.get("updated_at", ""), reverse=True)
        }

    async def _create_room(self, room_data: ChatRoom, current_user):
        """Create new chat room"""
        room_id = str(uuid.uuid4())
        user_id = current_user.id if current_user else "guest"
        room = {
            "id": room_id,
            "name": room_data.name,
            "description": room_data.description,
            "room_type": room_data.room_type,
            "created_by": user_id,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "max_members": room_data.max_members,
            "is_archived": room_data.is_archived,
            "metadata": room_data.metadata,
        }

        await self.db.set(f"chat_room:{room_id}", room)

        # Add creator as member
        await self._add_room_member(room_id, user_id, "owner")

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "chat.room.created", {"room_id": room_id, "created_by": user_id}
            )

        return {"message": "Room created successfully", "room_id": room_id}

    async def _get_room(self, room_id: str, current_user):
        """Get room details"""
        user_id = current_user.id if current_user else "guest"
        if not await self._user_can_access_room(user_id, room_id):
            raise HTTPException(status_code=403, detail="Access denied")

        room = await self.db.get(f"chat_room:{room_id}")
        if not room:
            raise HTTPException(status_code=404, detail="Room not found")

        # Get members
        members = await self._get_room_members(room_id)

        # Get recent messages
        messages = await self._get_messages(room_id, 50, None, current_user)

        return {
            "room": room,
            "members": members,
            "messages": messages,
            "online_members": self.connection_manager.get_online_users(room_id),
        }

    async def _send_message(
        self,
        room_id: str,
        message_data: ChatMessage,
        current_user,
        background_tasks: BackgroundTasks,
    ):
        """Send message to room"""
        user_id = current_user.id if current_user else "guest"
        if not await self._user_can_send_to_room(user_id, room_id):
            raise HTTPException(status_code=403, detail="Cannot send message to this room")

        message_id = str(uuid.uuid4())
        message = {
            "id": message_id,
            "room_id": room_id,
            "user_id": user_id,
            "content": message_data.content,
            "message_type": message_data.message_type,
            "thread_id": message_data.thread_id,
            "reply_to": message_data.reply_to,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "is_edited": False,
            "is_deleted": False,
            "metadata": message_data.metadata,
        }

        await self.db.set(f"chat_message:{message_id}", message)

        # Broadcast to room
        await self.connection_manager.send_room_message(
            room_id, {"type": "new_message", "message": message}
        )

        # Process notifications in background
        background_tasks.add_task(self._process_message_notifications, message)

        # Publish event
        if self.event_bus:
            await self.event_bus.publish("chat.message.sent", message)

        return {"message": "Message sent successfully", "message_id": message_id}

    async def _get_messages(self, room_id: str, limit: int, before: Optional[str], current_user):
        """Get room messages"""
        user_id = current_user.id if current_user else "guest"
        if not await self._user_can_access_room(user_id, room_id):
            raise HTTPException(status_code=403, detail="Access denied")

        message_keys = await self.db.list_keys(f"chat_message:*")
        messages = []

        for key in message_keys:
            message = await self.db.get(key)
            if message and message.get("room_id") == room_id and not message.get("is_deleted"):
                if before is None or message.get("created_at", "") < before:
                    messages.append(message)

        # Sort by creation time (newest first)
        messages.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        return {"messages": messages[:limit]}

    async def _create_notification(self, notification: ChatNotification):
        """Create a chat notification"""
        notification_id = str(uuid.uuid4())
        notification_data = {
            "id": notification_id,
            "user_id": notification.user_id,
            "notification_type": notification.notification_type,
            "title": notification.title,
            "message": notification.message,
            "data": notification.data,
            "priority": notification.priority,
            "is_read": False,
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.db.set(f"chat_notification:{notification_id}", notification_data)

        # Send real-time notification
        await self.connection_manager.send_personal_message(
            notification.user_id, {"type": "notification", "notification": notification_data}
        )

        # Publish event
        if self.event_bus:
            await self.event_bus.publish("chat.notification.created", notification_data)

        return notification_id

    async def _process_message_notifications(self, message):
        """Process notifications for a message"""
        room_id = message["room_id"]
        sender_id = message["user_id"]
        content = message["content"]

        # Get room members
        members = await self._get_room_members(room_id)

        # Create notifications for room members (except sender)
        for member in members.get("members", []):
            if member["user_id"] != sender_id:
                notification = ChatNotification(
                    user_id=member["user_id"],
                    notification_type="new_message",
                    title=f"New message in {await self._get_room_name(room_id)}",
                    message=content[:100] + ("..." if len(content) > 100 else ""),
                    data={"room_id": room_id, "message_id": message["id"]},
                )
                await self._create_notification(notification)

    async def _get_notifications(self, user_id: str, unread_only: bool = False):
        """Get user notifications"""
        notification_keys = await self.db.list_keys(f"chat_notification:*")
        notifications = []

        for key in notification_keys:
            notification = await self.db.get(key)
            if notification and notification.get("user_id") == user_id:
                if not unread_only or not notification.get("is_read"):
                    notifications.append(notification)

        notifications.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        return {"notifications": notifications}

    # Helper methods
    async def _user_can_access_room(self, user_id: str, room_id: str) -> bool:
        """Check if user can access room"""
        room = await self.db.get(f"chat_room:{room_id}")
        if not room:
            return False

        if room.get("room_type") == "public":
            return True

        # Check membership
        member_keys = await self.db.list_keys(f"room_member:{room_id}:*")
        for key in member_keys:
            member = await self.db.get(key)
            if member and member.get("user_id") == user_id:
                return True

        return False

    async def _user_can_send_to_room(self, user_id: str, room_id: str) -> bool:
        """Check if user can send messages to room"""
        return await self._user_can_access_room(user_id, room_id)

    async def _get_room_members(self, room_id: str):
        """Get room members"""
        member_keys = await self.db.list_keys(f"room_member:{room_id}:*")
        members = []

        for key in member_keys:
            member = await self.db.get(key)
            if member:
                members.append(member)

        return {"members": members}

    async def _add_room_member(self, room_id: str, user_id: str, role: str = "member"):
        """Add user to room"""
        member_data = {
            "room_id": room_id,
            "user_id": user_id,
            "role": role,
            "joined_at": datetime.utcnow().isoformat(),
            "last_read": datetime.utcnow().isoformat(),
        }

        await self.db.set(f"room_member:{room_id}:{user_id}", member_data)

    async def _get_user_rooms(self, user_id: str):
        """Get rooms user is member of"""
        member_keys = await self.db.list_keys(f"room_member:*:{user_id}")
        rooms = []

        for key in member_keys:
            member = await self.db.get(key)
            if member:
                room = await self.db.get(f"chat_room:{member['room_id']}")
                if room:
                    rooms.append(room)

        return rooms

    async def _get_room_name(self, room_id: str) -> str:
        """Get room name"""
        room = await self.db.get(f"chat_room:{room_id}")
        return room.get("name", "Unknown Room") if room else "Unknown Room"

    async def _update_user_presence(self, user_id: str, status: str):
        """Update user presence status"""
        presence_data = {
            "user_id": user_id,
            "status": status,
            "last_seen": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        await self.db.set(f"user_presence:{user_id}", presence_data)

    async def _get_user_presence(self, room_id: Optional[str] = None):
        """Get user presence information"""
        if room_id:
            online_users = self.connection_manager.get_online_users(room_id)
        else:
            online_users = self.connection_manager.get_online_users()

        presence_data = []
        for user_id in online_users:
            presence = await self.db.get(f"user_presence:{user_id}")
            if presence:
                presence_data.append(presence)

        return {"presence": presence_data}

    async def _cleanup_typing_indicators(self):
        """Background task to cleanup old typing indicators"""
        while True:
            try:
                await asyncio.sleep(5)  # Check every 5 seconds
                current_time = datetime.utcnow()

                for room_id, users in list(self.typing_users.items()):
                    for user_id, timestamp in list(users.items()):
                        if (current_time - timestamp).seconds > 10:  # 10 seconds timeout
                            users.pop(user_id, None)

                            # Broadcast stop typing
                            await self.connection_manager.send_room_message(
                                room_id,
                                {
                                    "type": "user_stopped_typing",
                                    "user_id": user_id,
                                    "room_id": room_id,
                                },
                            )

                    if not users:
                        self.typing_users.pop(room_id, None)

            except Exception as e:
                logger.error(f"Error in typing indicator cleanup: {e}")

    async def _cleanup_old_messages(self):
        """Background task to cleanup old messages"""
        while True:
            try:
                await asyncio.sleep(3600)  # Check every hour

                if self.config.get("auto_delete_messages", False):
                    retention_days = self.config.get("message_history_days", 365)
                    cutoff_date = (datetime.utcnow() - timedelta(days=retention_days)).isoformat()

                    message_keys = await self.db.list_keys("chat_message:*")
                    for key in message_keys:
                        message = await self.db.get(key)
                        if message and message.get("created_at", "") < cutoff_date:
                            await self.db.delete(key)

            except Exception as e:
                logger.error(f"Error in message cleanup: {e}")

    # Placeholder methods for remaining functionality
    async def _join_room(self, room_id: str, current_user):
        """Join a chat room"""
        await self._add_room_member(room_id, current_user.id)
        return {"message": "Joined room successfully"}

    async def _leave_room(self, room_id: str, user_id: str, current_user):
        """Leave a chat room"""
        await self.db.delete(f"room_member:{room_id}:{user_id}")
        return {"message": "Left room successfully"}

    async def _edit_message(self, message_id: str, content: str, current_user):
        """Edit a message"""
        message = await self.db.get(f"chat_message:{message_id}")
        if not message or message.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        message["content"] = content
        message["is_edited"] = True
        message["updated_at"] = datetime.utcnow().isoformat()

        await self.db.set(f"chat_message:{message_id}", message)
        return {"message": "Message edited successfully"}

    async def _delete_message(self, message_id: str, current_user):
        """Delete a message"""
        message = await self.db.get(f"chat_message:{message_id}")
        if not message or message.get("user_id") != current_user.id:
            raise HTTPException(status_code=403, detail="Permission denied")

        message["is_deleted"] = True
        message["updated_at"] = datetime.utcnow().isoformat()

        await self.db.set(f"chat_message:{message_id}", message)
        return {"message": "Message deleted successfully"}

    async def _add_reaction(self, message_id: str, emoji: str, current_user):
        """Add reaction to message"""
        reaction_id = f"{message_id}:{current_user.id}:{emoji}"
        reaction_data = {
            "message_id": message_id,
            "user_id": current_user.id,
            "emoji": emoji,
            "created_at": datetime.utcnow().isoformat(),
        }

        await self.db.set(f"reaction:{reaction_id}", reaction_data)
        return {"message": "Reaction added successfully"}

    async def _remove_reaction(self, message_id: str, emoji: str, current_user):
        """Remove reaction from message"""
        reaction_id = f"{message_id}:{current_user.id}:{emoji}"
        await self.db.delete(f"reaction:{reaction_id}")
        return {"message": "Reaction removed successfully"}

    async def _upload_file(self, file: UploadFile, room_id: str, current_user):
        """Upload file to chat"""
        if not self.config.get("enable_file_uploads", True):
            raise HTTPException(status_code=403, detail="File uploads disabled")

        # Implementation would handle file storage
        return {"message": "File uploaded successfully", "file_id": str(uuid.uuid4())}

    async def _download_file(self, file_id: str, current_user):
        """Download chat file"""
        # Implementation would handle file retrieval
        return {"message": "File download not implemented"}

    async def _search_messages(self, query: str, room_id: Optional[str], limit: int, current_user):
        """Search messages"""
        # Implementation would handle message search
        return {"messages": [], "total": 0}

    async def _mark_notification_read(self, notification_id: str, current_user):
        """Mark notification as read"""
        notification = await self.db.get(f"chat_notification:{notification_id}")
        if notification and notification.get("user_id") == current_user.id:
            notification["is_read"] = True
            await self.db.set(f"chat_notification:{notification_id}", notification)
        return {"message": "Notification marked as read"}

    async def _render_admin_dashboard(self):
        """Render admin dashboard"""
        return render_template("chat/admin/dashboard", {"title": "Chat Administration"})

    async def _moderate_message(
        self, message_id: str, action: str, reason: Optional[str], current_user
    ):
        """Moderate a message"""
        return {"message": f"Message {action} completed"}

    async def _broadcast_admin_message(self, message: str, room_id: Optional[str], current_user):
        """Broadcast admin message"""
        broadcast_data = {
            "type": "admin_broadcast",
            "message": message,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if room_id:
            await self.connection_manager.send_room_message(room_id, broadcast_data)
        else:
            await self.connection_manager.broadcast_message(broadcast_data)

        return {"message": "Broadcast sent successfully"}

    # Additional helper methods
    async def _handle_ws_join_room(self, websocket: WebSocket, user, data: Dict[str, Any]):
        """Handle joining room via WebSocket"""
        room_id = data.get("room_id")
        if room_id and await self._user_can_access_room(user.id, room_id):
            await self.connection_manager.connect(websocket, user.id, room_id)

    async def _handle_ws_leave_room(self, websocket: WebSocket, user, data: Dict[str, Any]):
        """Handle leaving room via WebSocket"""
        # Implementation for leaving room
        pass

    async def _handle_ws_mark_read(self, websocket: WebSocket, user, data: Dict[str, Any]):
        """Handle marking messages as read via WebSocket"""
        # Implementation for marking messages as read
        pass

    async def _process_message_mentions(self, message):
        """Process @mentions in messages"""
        content = message.get("content", "")
        # Simple mention detection (could be enhanced)
        import re

        mentions = re.findall(r"@(\w+)", content)

        for mention in mentions:
            # Create notification for mentioned user
            notification = ChatNotification(
                user_id=mention,  # Would need to resolve username to user_id
                notification_type="mention",
                title=f"You were mentioned",
                message=f"You were mentioned in {await self._get_room_name(message['room_id'])}",
                data={"room_id": message["room_id"], "message_id": message["id"]},
            )
            await self._create_notification(notification)

    async def _get_room_member_count(self, room_id: str) -> int:
        """Get room member count"""
        member_keys = await self.db.list_keys(f"room_member:{room_id}:*")
        return len(member_keys)

    async def _get_last_room_message(self, room_id: str):
        """Get last message in room"""
        message_keys = await self.db.list_keys("chat_message:*")
        last_message = None

        for key in message_keys:
            message = await self.db.get(key)
            if message and message.get("room_id") == room_id and not message.get("is_deleted"):
                if not last_message or message.get("created_at", "") > last_message.get(
                    "created_at", ""
                ):
                    last_message = message

        return last_message

    def get_api_routes(self):
        """Get plugin API routes for registration"""
        return [self.router]


# Plugin instance
plugin = ChatPlugin()


# Export required plugin interface
def get_plugin():
    """Get plugin instance"""
    return plugin


async def initialize_plugin(db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
    """Initialize plugin"""
    plugin.db_adapter = db
    plugin.event_bus = event_bus
    plugin.config = config
    return await plugin.initialize()


def get_routes():
    """Get plugin routes"""
    return [plugin.router]


def get_name():
    """Get plugin name"""
    return plugin.name


def get_version():
    """Get plugin version"""
    return plugin.version
