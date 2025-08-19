"""
Chat Plugin Services

This module contains business logic and service classes for the chat plugin.
"""

import logging
import json
import uuid
import asyncio
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
from pathlib import Path
import mimetypes
import hashlib

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

logger = logging.getLogger(__name__)


class ChatService:
    """Core chat service with business logic"""

    def __init__(
        self, db: DatabaseAdapter, event_bus: EventBus, connection_manager: ConnectionManager
    ):
        self.db = db
        self.event_bus = event_bus
        self.connection_manager = connection_manager
        self.typing_users: Dict[str, Dict[str, datetime]] = {}

    async def create_room(
        self, room_data: ChatRoom, creator_user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new chat room"""
        room_id = str(uuid.uuid4())
        room_dict = room_data.dict()
        room_dict.update(
            {
                "id": room_id,
                "created_by": creator_user.get("id"),
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
            }
        )

        # Insert room into database
        await self.db.insert("chat_rooms", room_dict)

        # Add creator as room owner
        await self.add_room_member(room_id, creator_user.get("id"), "owner")

        # Emit event
        await self.event_bus.emit(
            "chat.room.created",
            {
                "room_id": room_id,
                "room_data": room_dict,
                "creator": creator_user,
            },
        )

        logger.info(f"Room {room_id} created by user {creator_user.get('id')}")
        return room_dict

    async def get_room(self, room_id: str, user: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Get room details if user has access"""
        if not await self.user_can_access_room(user.get("id"), room_id):
            return None

        room = await self.db.get("chat_rooms", room_id)
        if room:
            # Add member count and last message
            room["member_count"] = await self.get_room_member_count(room_id)
            room["last_message"] = await self.get_last_room_message(room_id)

        return room

    async def list_user_rooms(self, user: Dict[str, Any]) -> List[Dict[str, Any]]:
        """List rooms accessible to user"""
        user_id = user.get("id")

        # Get rooms where user is a member
        member_rooms = await self.db.query(
            "SELECT room_id FROM chat_room_members WHERE user_id = ?", [user_id]
        )
        room_ids = [r["room_id"] for r in member_rooms]

        if not room_ids:
            return []

        # Get room details
        rooms = []
        for room_id in room_ids:
            room = await self.get_room(room_id, user)
            if room:
                rooms.append(room)

        return rooms

    async def send_message(
        self, room_id: str, message_data: ChatMessage, sender: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send a message to a room"""
        if not await self.user_can_send_to_room(sender.get("id"), room_id):
            raise ValueError("User cannot send messages to this room")

        message_id = str(uuid.uuid4())
        message_dict = message_data.dict()
        message_dict.update(
            {
                "id": message_id,
                "sender_id": sender.get("id"),
                "sender_name": sender.get("username", "Unknown"),
                "sent_at": datetime.now().isoformat(),
                "edited_at": None,
                "is_deleted": False,
                "reactions": {},
            }
        )

        # Insert message into database
        await self.db.insert("chat_messages", message_dict)

        # Update room's last activity
        await self.db.update(
            "chat_rooms",
            room_id,
            {
                "last_activity": datetime.now().isoformat(),
                "last_message_id": message_id,
            },
        )

        # Send via WebSocket
        await self.connection_manager.send_room_message(
            room_id,
            {
                "type": "new_message",
                "message": message_dict,
            },
        )

        # Process mentions and create notifications
        await self.process_message_mentions(message_dict)

        # Emit event
        await self.event_bus.emit(
            "chat.message.sent",
            {
                "message": message_dict,
                "room_id": room_id,
                "sender": sender,
            },
        )

        logger.info(f"Message {message_id} sent to room {room_id} by user {sender.get('id')}")
        return message_dict

    async def get_messages(
        self,
        room_id: str,
        user: Dict[str, Any],
        limit: int = 50,
        offset: int = 0,
        before: Optional[str] = None,
        after: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Get messages from a room"""
        if not await self.user_can_access_room(user.get("id"), room_id):
            return []

        query = "SELECT * FROM chat_messages WHERE room_id = ? AND is_deleted = 0"
        params = [room_id]

        if before:
            query += " AND sent_at < ?"
            params.append(before)

        if after:
            query += " AND sent_at > ?"
            params.append(after)

        query += " ORDER BY sent_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        messages = await self.db.query(query, params)
        return list(reversed(messages))  # Return in chronological order

    async def edit_message(
        self, message_id: str, new_content: str, user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Edit a message"""
        message = await self.db.get("chat_messages", message_id)
        if not message:
            raise ValueError("Message not found")

        if message["sender_id"] != user.get("id"):
            raise ValueError("Can only edit your own messages")

        # Update message
        updated_data = {
            "content": new_content,
            "edited_at": datetime.now().isoformat(),
        }
        await self.db.update("chat_messages", message_id, updated_data)

        message.update(updated_data)

        # Notify room via WebSocket
        await self.connection_manager.send_room_message(
            message["room_id"],
            {
                "type": "message_edited",
                "message": message,
            },
        )

        return message

    async def delete_message(self, message_id: str, user: Dict[str, Any]) -> bool:
        """Delete a message"""
        message = await self.db.get("chat_messages", message_id)
        if not message:
            return False

        # Check permissions
        is_sender = message["sender_id"] == user.get("id")
        is_admin = user.get("role") in ["admin", "moderator"]

        if not (is_sender or is_admin):
            raise ValueError("Cannot delete this message")

        # Soft delete
        await self.db.update(
            "chat_messages",
            message_id,
            {
                "is_deleted": True,
                "deleted_at": datetime.now().isoformat(),
                "deleted_by": user.get("id"),
            },
        )

        # Notify room
        await self.connection_manager.send_room_message(
            message["room_id"],
            {
                "type": "message_deleted",
                "message_id": message_id,
            },
        )

        return True

    async def add_reaction(
        self, message_id: str, emoji: str, user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add reaction to a message"""
        message = await self.db.get("chat_messages", message_id)
        if not message:
            raise ValueError("Message not found")

        user_id = user.get("id")
        reactions = json.loads(message.get("reactions", "{}"))

        if emoji not in reactions:
            reactions[emoji] = []

        if user_id not in reactions[emoji]:
            reactions[emoji].append(user_id)

        await self.db.update("chat_messages", message_id, {"reactions": json.dumps(reactions)})

        # Notify room
        await self.connection_manager.send_room_message(
            message["room_id"],
            {
                "type": "reaction_added",
                "message_id": message_id,
                "emoji": emoji,
                "user_id": user_id,
            },
        )

        return {"emoji": emoji, "users": reactions[emoji]}

    async def remove_reaction(self, message_id: str, emoji: str, user: Dict[str, Any]) -> bool:
        """Remove reaction from a message"""
        message = await self.db.get("chat_messages", message_id)
        if not message:
            return False

        user_id = user.get("id")
        reactions = json.loads(message.get("reactions", "{}"))

        if emoji in reactions and user_id in reactions[emoji]:
            reactions[emoji].remove(user_id)
            if not reactions[emoji]:
                del reactions[emoji]

            await self.db.update("chat_messages", message_id, {"reactions": json.dumps(reactions)})

            # Notify room
            await self.connection_manager.send_room_message(
                message["room_id"],
                {
                    "type": "reaction_removed",
                    "message_id": message_id,
                    "emoji": emoji,
                    "user_id": user_id,
                },
            )

            return True

        return False

    async def join_room(self, room_id: str, user: Dict[str, Any]) -> bool:
        """Join a room"""
        room = await self.db.get("chat_rooms", room_id)
        if not room:
            return False

        # Check if room is public or user has permission
        if room.get("room_type") != "public":
            # Check if user is invited or has permission
            pass  # Add invitation logic here

        user_id = user.get("id")
        await self.add_room_member(room_id, user_id, "member")
        await self.connection_manager.join_room(user_id, room_id)

        # Notify room
        await self.connection_manager.send_room_message(
            room_id,
            {
                "type": "user_joined",
                "room_id": room_id,
                "user": user,
            },
        )

        return True

    async def leave_room(self, room_id: str, user: Dict[str, Any]) -> bool:
        """Leave a room"""
        user_id = user.get("id")

        # Remove from database
        await self.db.delete(
            "chat_room_members",
            {
                "room_id": room_id,
                "user_id": user_id,
            },
        )

        await self.connection_manager.leave_room(user_id, room_id)

        # Notify room
        await self.connection_manager.send_room_message(
            room_id,
            {
                "type": "user_left",
                "room_id": room_id,
                "user": user,
            },
        )

        return True

    async def update_user_presence(self, user_id: str, status: str, room_id: Optional[str] = None):
        """Update user presence status"""
        presence_data = {
            "user_id": user_id,
            "status": status,
            "last_seen": datetime.now().isoformat(),
            "current_room": room_id,
        }

        # Upsert presence
        await self.db.upsert("user_presence", presence_data, ["user_id"])

        # Send presence update
        await self.connection_manager.send_presence_update(user_id, status)

    async def get_user_presence(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user presence status"""
        presence = await self.db.get_by_field("user_presence", "user_id", user_id)
        if presence:
            # Check if user is actually online
            is_online = self.connection_manager.is_user_online(user_id)
            if not is_online and presence["status"] != "offline":
                await self.update_user_presence(user_id, "offline")
                presence["status"] = "offline"

        return presence

    async def create_notification(self, notification: ChatNotification):
        """Create a notification for a user"""
        notification_id = str(uuid.uuid4())
        notification_dict = notification.dict()
        notification_dict.update(
            {
                "id": notification_id,
                "created_at": datetime.now().isoformat(),
                "is_read": False,
            }
        )

        await self.db.insert("chat_notifications", notification_dict)

        # Send real-time notification
        await self.connection_manager.send_personal_message(
            notification.user_id,
            {
                "type": "notification",
                "notification": notification_dict,
            },
        )

        return notification_dict

    async def get_notifications(
        self, user: Dict[str, Any], limit: int = 20
    ) -> List[Dict[str, Any]]:
        """Get user notifications"""
        notifications = await self.db.query(
            "SELECT * FROM chat_notifications WHERE user_id = ? ORDER BY created_at DESC LIMIT ?",
            [user.get("id"), limit],
        )
        return notifications

    async def mark_notification_read(self, notification_id: str, user: Dict[str, Any]) -> bool:
        """Mark notification as read"""
        notification = await self.db.get("chat_notifications", notification_id)
        if not notification or notification["user_id"] != user.get("id"):
            return False

        await self.db.update(
            "chat_notifications",
            notification_id,
            {
                "is_read": True,
                "read_at": datetime.now().isoformat(),
            },
        )

        return True

    # Helper methods
    async def user_can_access_room(self, user_id: str, room_id: str) -> bool:
        """Check if user can access a room"""
        # Check if user is a member
        member = await self.db.get_by_fields(
            "chat_room_members",
            {
                "user_id": user_id,
                "room_id": room_id,
            },
        )
        return member is not None

    async def user_can_send_to_room(self, user_id: str, room_id: str) -> bool:
        """Check if user can send messages to a room"""
        return await self.user_can_access_room(user_id, room_id)

    async def add_room_member(self, room_id: str, user_id: str, role: str = "member"):
        """Add a user to a room"""
        member_data = {
            "room_id": room_id,
            "user_id": user_id,
            "role": role,
            "joined_at": datetime.now().isoformat(),
        }
        await self.db.upsert("chat_room_members", member_data, ["room_id", "user_id"])

    async def get_room_members(self, room_id: str) -> List[Dict[str, Any]]:
        """Get room members"""
        members = await self.db.query(
            "SELECT * FROM chat_room_members WHERE room_id = ?", [room_id]
        )
        return members

    async def get_room_member_count(self, room_id: str) -> int:
        """Get room member count"""
        result = await self.db.query(
            "SELECT COUNT(*) as count FROM chat_room_members WHERE room_id = ?", [room_id]
        )
        return result[0]["count"] if result else 0

    async def get_last_room_message(self, room_id: str) -> Optional[Dict[str, Any]]:
        """Get the last message in a room"""
        messages = await self.db.query(
            "SELECT * FROM chat_messages WHERE room_id = ? AND is_deleted = 0 ORDER BY sent_at DESC LIMIT 1",
            [room_id],
        )
        return messages[0] if messages else None

    async def process_message_mentions(self, message: Dict[str, Any]):
        """Process @mentions in messages and create notifications"""
        content = message.get("content", "")
        room_id = message.get("room_id")
        sender_id = message.get("sender_id")

        # Simple mention detection - @username
        import re

        mentions = re.findall(r"@(\w+)", content)

        for username in mentions:
            # Get user by username
            mentioned_user = await self.db.get_by_field("users", "username", username)
            if mentioned_user and mentioned_user["id"] != sender_id:
                # Check if mentioned user has access to the room
                if await self.user_can_access_room(mentioned_user["id"], room_id):
                    await self.create_notification(
                        ChatNotification(
                            user_id=mentioned_user["id"],
                            notification_type="mention",
                            title=f"You were mentioned by {message.get('sender_name')}",
                            message=f"In room: {content[:100]}...",
                            data={
                                "message_id": message["id"],
                                "room_id": room_id,
                                "sender_id": sender_id,
                            },
                        )
                    )

    async def search_messages(
        self,
        query: str,
        user: Dict[str, Any],
        room_id: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Search messages"""
        user_id = user.get("id")

        # Base query
        sql = """
            SELECT cm.* FROM chat_messages cm
            JOIN chat_room_members crm ON cm.room_id = crm.room_id
            WHERE crm.user_id = ? AND cm.is_deleted = 0
            AND (cm.content LIKE ? OR cm.sender_name LIKE ?)
        """
        params = [user_id, f"%{query}%", f"%{query}%"]

        if room_id:
            sql += " AND cm.room_id = ?"
            params.append(room_id)

        sql += " ORDER BY cm.sent_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        messages = await self.db.query(sql, params)
        return messages

    async def cleanup_old_data(self):
        """Cleanup old messages, notifications, etc."""
        # Clean up old typing indicators
        now = datetime.now()
        for room_id, typing_users in self.typing_users.items():
            expired_users = []
            for user_id, timestamp in typing_users.items():
                if (now - timestamp).seconds > 30:  # 30 second timeout
                    expired_users.append(user_id)

            for user_id in expired_users:
                del typing_users[user_id]
                await self.connection_manager.send_typing_indicator(room_id, user_id, False)

        # Clean up old notifications (older than 30 days)
        cutoff_date = (now - timedelta(days=30)).isoformat()
        await self.db.execute(
            "DELETE FROM chat_notifications WHERE created_at < ? AND is_read = 1", [cutoff_date]
        )

        logger.info("Cleaned up old chat data")

    async def update_room(
        self, room_id: str, room_data: Dict[str, Any], user: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update room details"""
        room = await self.db.get("chat_rooms", room_id)
        if not room:
            raise ValueError("Room not found")

        # Check if user can update room (room owner/admin)
        if room.get("created_by") != user.get("id"):
            raise PermissionError("Only room creator can update room")

        # Update room data
        room.update(room_data)
        room["updated_at"] = datetime.now().isoformat()

        await self.db.upsert("chat_rooms", room, ["id"])
        return room

    async def delete_room(self, room_id: str, user: Dict[str, Any]) -> bool:
        """Delete a room"""
        room = await self.db.get("chat_rooms", room_id)
        if not room:
            return False

        # Check if user can delete room (room owner/admin)
        if room.get("created_by") != user.get("id"):
            raise PermissionError("Only room creator can delete room")

        # Delete room and related data
        await self.db.execute("DELETE FROM chat_rooms WHERE id = ?", [room_id])
        await self.db.execute("DELETE FROM chat_messages WHERE room_id = ?", [room_id])
        await self.db.execute("DELETE FROM chat_room_members WHERE room_id = ?", [room_id])

        return True

    async def upload_file(self, room_id: str, file, user: Dict[str, Any]) -> Dict[str, Any]:
        """Upload file to room"""
        # Check if user can access room
        if not await self.user_can_access_room(user.get("id"), room_id):
            raise PermissionError("Cannot upload file to this room")

        # For now, return a placeholder response
        file_id = str(uuid.uuid4())
        file_data = {
            "id": file_id,
            "filename": file.filename,
            "content_type": file.content_type,
            "size": 0,  # Would be actual file size
            "room_id": room_id,
            "uploaded_by": user.get("id"),
            "uploaded_at": datetime.now().isoformat(),
        }

        await self.db.insert("file_uploads", file_data)
        return {"message": "File uploaded successfully", "file_id": file_id}

    async def download_file(self, file_id: str, user: Dict[str, Any]):
        """Download a file"""
        file_data = await self.db.get("file_uploads", file_id)
        if not file_data:
            raise ValueError("File not found")

        # Check if user can access the room where file was uploaded
        if not await self.user_can_access_room(user.get("id"), file_data.get("room_id")):
            raise PermissionError("Cannot access this file")

        # For now, return file metadata
        return file_data
