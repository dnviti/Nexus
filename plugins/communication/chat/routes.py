"""
Chat Plugin API Routes

This module contains all API route handlers for the chat plugin.
"""

import logging
import json
import uuid
from typing import Dict, Any, Optional, List
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
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from nexus.database import DatabaseAdapter
from nexus.core import EventBus
from nexus.auth import get_current_user_dependency

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

logger = logging.getLogger(__name__)


class ChatRoutes:
    """Chat plugin routes handler"""

    def __init__(self, plugin_instance):
        self.plugin = plugin_instance
        self.router = APIRouter(prefix="/chat", tags=["chat"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup all chat routes"""

        @self.router.get("/")
        async def chat_interface(user=Depends(get_current_user_dependency)):
            """Render chat interface"""
            html_content = await self.plugin._render_chat_interface(user)
            return HTMLResponse(content=html_content, media_type="text/html")

        @self.router.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket, user_id: str, room_id: str = "general"):
            """WebSocket endpoint for real-time chat"""
            await self.plugin._handle_websocket_connection(websocket, user_id, room_id)

        @self.router.get("/test")
        async def test_html():
            """Test HTML response"""
            return HTMLResponse(
                content="<h1>Test HTML Response</h1><p>This should render as HTML</p>",
                media_type="text/html",
            )

        # Room management routes
        @self.router.get("/rooms", response_model=List[Dict[str, Any]])
        async def list_rooms(user=Depends(get_current_user_dependency)):
            """List available chat rooms"""
            return await self.plugin._list_rooms(user)

        @self.router.post("/rooms", response_model=Dict[str, Any])
        async def create_room(room: ChatRoom, user=Depends(get_current_user_dependency)):
            """Create a new chat room"""
            return await self.plugin.service.create_room(room.dict(), user)

        @self.router.get("/rooms/{room_id}", response_model=Dict[str, Any])
        async def get_room(room_id: str, user=Depends(get_current_user_dependency)):
            """Get room details"""
            return await self.plugin.service.get_room(room_id, user)

        @self.router.put("/rooms/{room_id}", response_model=Dict[str, Any])
        async def update_room(
            room_id: str, room_data: Dict[str, Any], user=Depends(get_current_user_dependency)
        ):
            """Update room details"""
            return await self.plugin.service.update_room(room_id, room_data, user)

        @self.router.delete("/rooms/{room_id}")
        async def delete_room(room_id: str, user=Depends(get_current_user_dependency)):
            """Delete a room"""
            return await self.plugin.service.delete_room(room_id, user)

        # Room membership routes
        @self.router.get("/rooms/{room_id}/members", response_model=List[Dict[str, Any]])
        async def get_room_members(room_id: str, user=Depends(get_current_user_dependency)):
            """Get room members"""
            return await self.plugin.service.get_room_members(room_id)

        @self.router.post("/rooms/{room_id}/join")
        async def join_room(room_id: str, user=Depends(get_current_user_dependency)):
            """Join a room"""
            return await self.plugin.service.join_room(room_id, user)

        @self.router.post("/rooms/{room_id}/leave")
        async def leave_room(room_id: str, user=Depends(get_current_user_dependency)):
            """Leave a room"""
            return await self.plugin.service.leave_room(room_id, user)

        # Message routes
        @self.router.get("/rooms/{room_id}/messages", response_model=List[Dict[str, Any]])
        async def get_messages(
            room_id: str,
            limit: int = Query(50, le=100),
            offset: int = Query(0, ge=0),
            before: Optional[str] = Query(None),
            after: Optional[str] = Query(None),
            user=Depends(get_current_user_dependency),
        ):
            """Get messages from a room"""
            return await self.plugin._get_messages(room_id, user, limit, offset, before, after)

        @self.router.post("/rooms/{room_id}/messages", response_model=Dict[str, Any])
        async def send_message(
            room_id: str,
            message: ChatMessage,
            background_tasks: BackgroundTasks,
            user=Depends(get_current_user_dependency),
        ):
            """Send a message to a room"""
            return await self.plugin.service.send_message(room_id, message.dict(), user)

        @self.router.put("/messages/{message_id}", response_model=Dict[str, Any])
        async def edit_message(
            message_id: str, content: str = Form(...), user=Depends(get_current_user_dependency)
        ):
            """Edit a message"""
            return await self.plugin.service.edit_message(message_id, {"content": content}, user)

        @self.router.delete("/messages/{message_id}")
        async def delete_message(message_id: str, user=Depends(get_current_user_dependency)):
            """Delete a message"""
            return await self.plugin.service.delete_message(message_id, user)

        # Message reactions
        @self.router.post("/messages/{message_id}/reactions")
        async def add_reaction(
            message_id: str, emoji: str = Form(...), user=Depends(get_current_user_dependency)
        ):
            """Add reaction to message"""
            return await self.plugin.service.add_reaction(message_id, emoji, user)

        @self.router.delete("/messages/{message_id}/reactions/{emoji}")
        async def remove_reaction(
            message_id: str, emoji: str, user=Depends(get_current_user_dependency)
        ):
            """Remove reaction from message"""
            return await self.plugin.service.remove_reaction(message_id, emoji, user)

        # File upload and download
        @self.router.post("/rooms/{room_id}/upload", response_model=Dict[str, Any])
        async def upload_file(
            room_id: str, file: UploadFile = File(...), user=Depends(get_current_user_dependency)
        ):
            """Upload file to room"""
            return await self.plugin.service.upload_file(room_id, file, user)

        @self.router.get("/files/{file_id}")
        async def download_file(file_id: str, user=Depends(get_current_user_dependency)):
            """Download a file"""
            return await self.plugin.service.download_file(file_id, user)

        # Notifications
        @self.router.get("/notifications", response_model=List[Dict[str, Any]])
        async def get_notifications(
            limit: int = Query(20, le=50), user=Depends(get_current_user_dependency)
        ):
            """Get user notifications"""
            return await self.plugin.service.get_notifications(user, limit)

        @self.router.put("/notifications/{notification_id}/read")
        async def mark_notification_read(
            notification_id: str, user=Depends(get_current_user_dependency)
        ):
            """Mark notification as read"""
            return await self.plugin.service.mark_notification_read(notification_id, user)

        # Search and presence
        @self.router.get("/search", response_model=List[Dict[str, Any]])
        async def search_messages(
            q: str = Query(..., min_length=3),
            room_id: Optional[str] = Query(None),
            limit: int = Query(20, le=50),
            offset: int = Query(0, ge=0),
            user=Depends(get_current_user_dependency),
        ):
            """Search messages"""
            return await self.plugin.service.search_messages(q, user, room_id, limit, offset)

        @self.router.get("/presence/{user_id}", response_model=Dict[str, Any])
        async def get_user_presence(user_id: str, user=Depends(get_current_user_dependency)):
            """Get user presence status"""
            return await self.plugin.service.get_user_presence(user_id)

        @self.router.put("/presence", response_model=Dict[str, Any])
        async def update_presence(
            presence: UserPresence, user=Depends(get_current_user_dependency)
        ):
            """Update user presence"""
            return await self.plugin.service.update_user_presence(
                user.get("id"), presence.status, presence.current_room
            )

        # Admin routes
        @self.router.get("/admin/dashboard")
        async def admin_dashboard(user=Depends(get_current_user_dependency)):
            """Admin dashboard"""
            html_content = await self.plugin._render_admin_dashboard(user)
            return HTMLResponse(content=html_content, media_type="text/html")

        @self.router.post("/admin/moderate/{message_id}")
        async def moderate_message(
            message_id: str,
            action: str = Form(...),
            reason: str = Form(None),
            user=Depends(get_current_user_dependency),
        ):
            """Moderate a message"""
            return await self.plugin._moderate_message(message_id, action, reason, user)

        @self.router.post("/admin/broadcast", response_model=Dict[str, Any])
        async def broadcast_message(
            title: str = Form(...),
            message: str = Form(...),
            priority: str = Form("normal"),
            user=Depends(get_current_user_dependency),
        ):
            """Broadcast admin message"""
            return await self.plugin._broadcast_admin_message(title, message, priority, user)

        # Statistics and monitoring
        @self.router.get("/stats", response_model=Dict[str, Any])
        async def get_stats(user=Depends(get_current_user_dependency)):
            """Get chat statistics"""
            return await self.plugin._get_chat_stats(user)

        @self.router.get("/health", response_model=Dict[str, Any])
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "plugin": "chat",
                "version": self.plugin.version,
            }
