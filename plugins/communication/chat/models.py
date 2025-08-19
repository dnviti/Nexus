"""
Chat Plugin Models

This module contains all data models and validation classes for the chat plugin.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, validator


class ChatRoom(BaseModel):
    """Model for chat rooms"""

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
    """Model for chat messages"""

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
    """Model for message reactions"""

    message_id: str
    emoji: str
    user_id: str


class ChatNotification(BaseModel):
    """Model for chat notifications"""

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
            raise ValueError(f"Invalid notification type. Must be one of: {valid_types}")
        return v


class UserPresence(BaseModel):
    """Model for user presence status"""

    user_id: str
    status: str = "online"  # online, away, busy, offline
    last_seen: Optional[str] = None
    current_room: Optional[str] = None

    @validator("status")
    def validate_status(cls, v):
        if v not in ["online", "away", "busy", "offline"]:
            raise ValueError("Invalid status")
        return v


class FileUpload(BaseModel):
    """Model for file uploads"""

    filename: str
    content_type: str
    size: int
    room_id: str
    user_id: str
    file_path: Optional[str] = None
    thumbnail_path: Optional[str] = None


class TypingIndicator(BaseModel):
    """Model for typing indicators"""

    user_id: str
    room_id: str
    is_typing: bool = True


class RoomMember(BaseModel):
    """Model for room membership"""

    user_id: str
    room_id: str
    role: str = "member"  # owner, admin, moderator, member
    joined_at: Optional[str] = None
    permissions: Dict[str, bool] = {}

    @validator("role")
    def validate_role(cls, v):
        if v not in ["owner", "admin", "moderator", "member"]:
            raise ValueError("Invalid role")
        return v
