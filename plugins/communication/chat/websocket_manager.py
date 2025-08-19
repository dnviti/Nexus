"""
WebSocket Connection Manager for Chat Plugin

This module manages WebSocket connections for real-time chat functionality.
"""

import logging
import json
import asyncio
from typing import Dict, Any, Set, List, Optional
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time chat"""

    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.user_connections: Dict[str, Set[WebSocket]] = {}
        self.room_connections: Dict[str, Set[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str, room_id: Optional[str] = None):
        """Connect a user's websocket"""
        await websocket.accept()

        connection_id = str(id(websocket))

        # Store connection
        if connection_id not in self.active_connections:
            self.active_connections[connection_id] = set()

        # Store user connection
        if user_id not in self.user_connections:
            self.user_connections[user_id] = set()
        self.user_connections[user_id].add(websocket)

        # Store room connection if provided
        if room_id:
            if room_id not in self.room_connections:
                self.room_connections[room_id] = set()
            self.room_connections[room_id].add(websocket)

        logger.info(f"User {user_id} connected via WebSocket")

        # Send connection confirmation
        await self.send_personal_message(
            user_id,
            {
                "type": "connection_confirmed",
                "user_id": user_id,
                "room_id": room_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def disconnect(self, websocket: WebSocket):
        """Disconnect a user's websocket"""
        connection_id = str(id(websocket))

        # Remove from active connections
        self.active_connections.pop(connection_id, None)

        # Remove from user connections
        user_to_remove = None
        for user_id, connections in self.user_connections.items():
            if websocket in connections:
                connections.discard(websocket)
                if not connections:  # No more connections for this user
                    user_to_remove = user_id
                break

        if user_to_remove:
            self.user_connections.pop(user_to_remove, None)
            logger.info(f"User {user_to_remove} disconnected from WebSocket")

        # Remove from room connections
        rooms_to_clean = []
        for room_id, connections in self.room_connections.items():
            connections.discard(websocket)
            if not connections:
                rooms_to_clean.append(room_id)

        for room_id in rooms_to_clean:
            self.room_connections.pop(room_id, None)

    async def send_personal_message(self, user_id: str, message: Dict[str, Any]):
        """Send message to specific user"""
        if user_id in self.user_connections:
            message_json = json.dumps(message)
            disconnected_websockets = []

            for websocket in self.user_connections[user_id]:
                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending personal message to {user_id}: {e}")
                    disconnected_websockets.append(websocket)

            # Clean up disconnected websockets
            for ws in disconnected_websockets:
                self.disconnect(ws)

    async def send_room_message(
        self, room_id: str, message: Dict[str, Any], exclude_user: Optional[str] = None
    ):
        """Send message to all users in a room"""
        if room_id in self.room_connections:
            message_json = json.dumps(message)
            disconnected_websockets = []

            for websocket in self.room_connections[room_id]:
                # Skip if this websocket belongs to excluded user
                if exclude_user:
                    websocket_user = self._get_websocket_user(websocket)
                    if websocket_user == exclude_user:
                        continue

                try:
                    await websocket.send_text(message_json)
                except Exception as e:
                    logger.error(f"Error sending room message to room {room_id}: {e}")
                    disconnected_websockets.append(websocket)

            # Clean up disconnected websockets
            for ws in disconnected_websockets:
                self.disconnect(ws)

    async def broadcast_message(self, message: Dict[str, Any]):
        """Broadcast message to all connected users"""
        message_json = json.dumps(message)
        disconnected_websockets = []

        all_websockets = set()
        for connections in self.user_connections.values():
            all_websockets.update(connections)

        for websocket in all_websockets:
            try:
                await websocket.send_text(message_json)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected_websockets.append(websocket)

        # Clean up disconnected websockets
        for ws in disconnected_websockets:
            self.disconnect(ws)

    def get_online_users(self, room_id: Optional[str] = None) -> List[str]:
        """Get list of online users"""
        if room_id:
            # Get users in specific room
            online_users = []
            if room_id in self.room_connections:
                for websocket in self.room_connections[room_id]:
                    user_id = self._get_websocket_user(websocket)
                    if user_id and user_id not in online_users:
                        online_users.append(user_id)
            return online_users
        else:
            # Get all online users
            return list(self.user_connections.keys())

    def is_user_online(self, user_id: str) -> bool:
        """Check if user is online"""
        return user_id in self.user_connections and len(self.user_connections[user_id]) > 0

    def get_room_user_count(self, room_id: str) -> int:
        """Get number of users in a room"""
        if room_id not in self.room_connections:
            return 0
        return len(self.room_connections[room_id])

    def _get_websocket_user(self, websocket: WebSocket) -> Optional[str]:
        """Get user ID for a given websocket"""
        for user_id, connections in self.user_connections.items():
            if websocket in connections:
                return user_id
        return None

    async def join_room(self, user_id: str, room_id: str):
        """Add user to a room's websocket connections"""
        if user_id in self.user_connections:
            if room_id not in self.room_connections:
                self.room_connections[room_id] = set()

            for websocket in self.user_connections[user_id]:
                self.room_connections[room_id].add(websocket)

            logger.info(f"User {user_id} joined room {room_id}")

    async def leave_room(self, user_id: str, room_id: str):
        """Remove user from a room's websocket connections"""
        if user_id in self.user_connections and room_id in self.room_connections:
            for websocket in self.user_connections[user_id]:
                self.room_connections[room_id].discard(websocket)

            # Clean up empty room
            if not self.room_connections[room_id]:
                self.room_connections.pop(room_id, None)

            logger.info(f"User {user_id} left room {room_id}")

    async def send_typing_indicator(self, room_id: str, user_id: str, is_typing: bool):
        """Send typing indicator to room"""
        message = {
            "type": "typing_indicator",
            "room_id": room_id,
            "user_id": user_id,
            "is_typing": is_typing,
            "timestamp": datetime.now().isoformat(),
        }
        await self.send_room_message(room_id, message, exclude_user=user_id)

    async def send_presence_update(self, user_id: str, status: str):
        """Send presence update to all relevant users"""
        message = {
            "type": "presence_update",
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.now().isoformat(),
        }
        # Send to all users who share rooms with this user
        await self.broadcast_message(message)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "online_users": len(self.user_connections),
            "active_rooms": len(self.room_connections),
            "connections_per_user": {
                user_id: len(connections) for user_id, connections in self.user_connections.items()
            },
        }
