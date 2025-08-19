"""
Nexus Framework Debug Routes
HTTP endpoints for debug interfaces, monitoring dashboards, and WebSocket connections.
"""

import asyncio
import json
import logging
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse

from ..ui.templates import (
    get_debug_interface_template,
    get_notifications_demo_template,
    get_simple_debug_template,
)

logger = logging.getLogger(__name__)


def create_debug_router(app_instance: Any) -> APIRouter:
    """
    Create debug and monitoring routes.

    Args:
        app_instance: The NexusApp instance

    Returns:
        APIRouter: Configured router with debug routes
    """
    router = APIRouter(tags=["debug"])

    @router.get("/debug", response_class=HTMLResponse)
    async def debug_interface() -> HTMLResponse:
        """Main debug interface with real-time event monitoring."""
        return HTMLResponse(content=get_debug_interface_template())

    @router.get("/api/events/debug-ui", response_class=HTMLResponse)
    async def simple_debug_interface() -> HTMLResponse:
        """Simple debug interface for event monitoring."""
        return HTMLResponse(content=get_simple_debug_template())

    @router.get("/demo/notifications", response_class=HTMLResponse)
    async def notifications_demo() -> HTMLResponse:
        """Live notifications demonstration page."""
        return HTMLResponse(content=get_notifications_demo_template())

    @router.websocket("/api/events/stream")
    async def event_stream_websocket(websocket: WebSocket) -> None:
        """WebSocket endpoint for real-time event streaming."""
        await websocket.accept()
        app_instance._event_websockets.append(websocket)

        try:
            await websocket.send_json(
                {
                    "type": "connection",
                    "message": "Connected to event stream",
                    "timestamp": asyncio.get_event_loop().time(),
                }
            )

            # Keep connection alive
            while True:
                try:
                    # Send ping every 30 seconds to keep connection alive
                    await asyncio.sleep(30)
                    await websocket.send_json(
                        {"type": "ping", "timestamp": asyncio.get_event_loop().time()}
                    )
                except WebSocketDisconnect:
                    break

        except WebSocketDisconnect:
            pass
        finally:
            if websocket in app_instance._event_websockets:
                app_instance._event_websockets.remove(websocket)

    return router
