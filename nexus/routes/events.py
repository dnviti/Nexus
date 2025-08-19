"""
Nexus Framework Event Routes
HTTP endpoints for event publishing, subscription management, and real-time streaming.
"""

import asyncio
import json
import logging
from typing import Any, AsyncGenerator, Dict

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from ..core import Event, EventPriority

logger = logging.getLogger(__name__)


def create_events_router(app_instance: Any) -> APIRouter:
    """
    Create event system routes.

    Args:
        app_instance: The NexusApp instance

    Returns:
        APIRouter: Configured router with event routes
    """
    router = APIRouter(prefix="/api/events", tags=["events"])

    @router.post("/publish")
    async def publish_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Publish an event to the event bus."""
        try:
            event_name = event_data.get("name") or event_data.get("event_name")
            if not event_name:
                raise HTTPException(status_code=400, detail="event_name is required")

            data = event_data.get("data", {})
            source = event_data.get("source", "api")
            priority_str = event_data.get("priority", "normal").upper()

            # Convert priority string to enum
            try:
                priority = EventPriority[priority_str]
            except KeyError:
                priority = EventPriority.NORMAL

            # Publish event directly
            await app_instance.event_bus.publish(
                event_name=event_name,
                data=data,
                source=source,
                priority=priority,
            )

            # Create event for broadcasting to debug clients
            event = Event(
                name=event_name,
                data=data,
                source=source,
            )

            # Broadcast to WebSocket/SSE clients for debugging
            await app_instance._broadcast_event_to_clients(event)

            return {
                "message": "Event published successfully",
                "event": {
                    "name": event_name,
                    "source": source,
                    "priority": priority.value,
                },
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error publishing event: {e}")
            raise HTTPException(status_code=500, detail="Failed to publish event")

    @router.get("/subscribers")
    async def list_event_subscribers() -> Dict[str, Any]:
        """List all event subscribers and their events."""
        subscribers = {}

        for event_name, handlers in app_instance.event_bus._subscribers.items():
            subscribers[event_name] = {
                "handler_count": len(handlers),
                "handlers": [
                    {
                        "function_name": getattr(handler, "__name__", str(handler)),
                        "module": getattr(handler, "__module__", "unknown"),
                    }
                    for handler in handlers
                ],
            }

        return {"subscribers": subscribers}

    @router.get("/status")
    async def get_event_bus_status() -> Dict[str, Any]:
        """Get event bus status and statistics."""
        return {
            "status": (
                "running"
                if hasattr(app_instance.event_bus, "_running") and app_instance.event_bus._running
                else "stopped"
            ),
            "queue_size": (
                app_instance.event_bus._queue.qsize()
                if hasattr(app_instance.event_bus._queue, "qsize")
                else 0
            ),
            "subscribers": len(app_instance.event_bus._subscribers),
            "total_events": sum(
                len(handlers) for handlers in app_instance.event_bus._subscribers.values()
            ),
        }

    @router.get("/stream")
    async def event_stream_sse() -> StreamingResponse:
        """Server-Sent Events endpoint for real-time event streaming."""

        async def event_generator() -> AsyncGenerator[str, None]:
            # Send initial connection event
            initial_data = {
                "type": "connection",
                "message": "Connected to SSE event stream",
                "timestamp": asyncio.get_event_loop().time(),
            }
            yield f"data: {json.dumps(initial_data)}\n\n"

            # Create a queue for this client
            client_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()
            app_instance._event_sse_clients.append(client_queue)

            try:
                while True:
                    try:
                        # Wait for events with timeout for heartbeat
                        event_data = await asyncio.wait_for(client_queue.get(), timeout=30.0)
                        yield f"data: {json.dumps(event_data)}\n\n"
                    except asyncio.TimeoutError:
                        # Send heartbeat
                        heartbeat_data = {
                            "type": "heartbeat",
                            "timestamp": asyncio.get_event_loop().time(),
                        }
                        yield f"data: {json.dumps(heartbeat_data)}\n\n"
            except asyncio.CancelledError:
                pass
            finally:
                if client_queue in app_instance._event_sse_clients:
                    app_instance._event_sse_clients.remove(client_queue)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control",
            },
        )

    return router
