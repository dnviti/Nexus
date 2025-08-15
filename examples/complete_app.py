#!/usr/bin/env python3
"""
Complete Example Application using Nexus Framework

This example demonstrates a full-featured application with:
- Task management system
- User authentication
- Real-time notifications
- Analytics dashboard
- File storage
- Email notifications
- WebSocket support
- Background jobs
"""

import asyncio
import logging
import os
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from pathlib import Path

# Nexus Framework imports
from nexus import (
    NexusApp,
    create_nexus_app,
    BasePlugin,
    PluginMetadata,
    Event,
    EventPriority,
    AppConfig,
    DatabaseConfig,
    create_default_config,
    APIRouter,
    HTTPException,
    Depends,
    status,
    BaseModel,
    Field,
)

# FastAPI imports for additional functionality
from fastapi import WebSocket, WebSocketDisconnect, File, UploadFile, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Custom Plugins
# ============================================================================

class NotificationPlugin(BasePlugin):
    """
    Real-time notification plugin using WebSocket.
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="notifications",
            version="1.0.0",
            description="Real-time notification system",
            author="Example Team",
            category="communication",
            dependencies=["auth_advanced"],
        )
        self.active_connections: Dict[str, WebSocket] = {}

    async def initialize(self, context) -> bool:
        """Initialize the notification plugin."""
        logger.info("Initializing Notification Plugin")

        # Subscribe to events
        event_bus = context.get_service("event_bus")
        if event_bus:
            event_bus.subscribe("task.created", self.handle_task_created)
            event_bus.subscribe("task.assigned", self.handle_task_assigned)
            event_bus.subscribe("user.message", self.handle_user_message)

        return True

    async def handle_task_created(self, event: Event):
        """Handle task creation notifications."""
        data = event.data
        user_id = data.get("assigned_to")
        if user_id and user_id in self.active_connections:
            await self.send_notification(user_id, {
                "type": "task_created",
                "title": "New Task Assigned",
                "message": f"You have been assigned: {data.get('title')}",
                "task_id": data.get("task_id"),
                "priority": data.get("priority")
            })

    async def handle_task_assigned(self, event: Event):
        """Handle task assignment notifications."""
        data = event.data
        user_id = data.get("new_assigned")
        if user_id and user_id in self.active_connections:
            await self.send_notification(user_id, {
                "type": "task_assigned",
                "title": "Task Assigned",
                "message": f"You have been assigned: {data.get('title')}",
                "task_id": data.get("task_id")
            })

    async def handle_user_message(self, event: Event):
        """Handle direct user messages."""
        data = event.data
        recipient_id = data.get("recipient_id")
        if recipient_id and recipient_id in self.active_connections:
            await self.send_notification(recipient_id, {
                "type": "message",
                "from": data.get("sender_name"),
                "message": data.get("message"),
                "timestamp": datetime.utcnow().isoformat()
            })

    async def send_notification(self, user_id: str, notification: Dict[str, Any]):
        """Send notification to a specific user."""
        websocket = self.active_connections.get(user_id)
        if websocket:
            try:
                await websocket.send_json(notification)
            except Exception as e:
                logger.error(f"Failed to send notification to {user_id}: {e}")
                # Remove broken connection
                del self.active_connections[user_id]

    async def broadcast(self, notification: Dict[str, Any]):
        """Broadcast notification to all connected users."""
        disconnected = []
        for user_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(notification)
            except:
                disconnected.append(user_id)

        # Clean up disconnected clients
        for user_id in disconnected:
            del self.active_connections[user_id]

    def get_api_routes(self) -> List[APIRouter]:
        """Define WebSocket routes."""
        router = APIRouter(prefix="/ws", tags=["WebSocket"])

        @router.websocket("/notifications/{user_id}")
        async def websocket_endpoint(websocket: WebSocket, user_id: str):
            """WebSocket endpoint for real-time notifications."""
            await websocket.accept()
            self.active_connections[user_id] = websocket

            # Send welcome message
            await websocket.send_json({
                "type": "connection",
                "message": "Connected to notification service",
                "timestamp": datetime.utcnow().isoformat()
            })

            try:
                while True:
                    # Keep connection alive and handle incoming messages
                    data = await websocket.receive_text()
                    # Echo back or handle commands
                    if data == "ping":
                        await websocket.send_text("pong")
            except WebSocketDisconnect:
                del self.active_connections[user_id]
                logger.info(f"User {user_id} disconnected from notifications")

        return [router]


class AnalyticsPlugin(BasePlugin):
    """
    Analytics and reporting plugin.
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="analytics",
            version="1.0.0",
            description="Analytics and reporting system",
            author="Example Team",
            category="analytics",
            dependencies=["database", "task_manager"],
        )
        self.metrics = {
            "page_views": 0,
            "api_calls": 0,
            "active_users": set(),
            "tasks_created": 0,
            "tasks_completed": 0,
        }

    async def initialize(self, context) -> bool:
        """Initialize the analytics plugin."""
        logger.info("Initializing Analytics Plugin")

        # Subscribe to events for tracking
        event_bus = context.get_service("event_bus")
        if event_bus:
            event_bus.subscribe("task.created", self.track_task_created)
            event_bus.subscribe("task.status_changed", self.track_task_status)
            event_bus.subscribe("user.login", self.track_user_login)
            event_bus.subscribe("api.request", self.track_api_request)

        # Start periodic reporting
        asyncio.create_task(self.periodic_report())

        return True

    async def track_task_created(self, event: Event):
        """Track task creation."""
        self.metrics["tasks_created"] += 1

    async def track_task_status(self, event: Event):
        """Track task status changes."""
        if event.data.get("new_status") == "done":
            self.metrics["tasks_completed"] += 1

    async def track_user_login(self, event: Event):
        """Track user logins."""
        user_id = event.data.get("user_id")
        if user_id:
            self.metrics["active_users"].add(user_id)

    async def track_api_request(self, event: Event):
        """Track API requests."""
        self.metrics["api_calls"] += 1

    async def periodic_report(self):
        """Generate periodic analytics reports."""
        while True:
            await asyncio.sleep(3600)  # Report every hour

            report = {
                "timestamp": datetime.utcnow().isoformat(),
                "metrics": {
                    "page_views": self.metrics["page_views"],
                    "api_calls": self.metrics["api_calls"],
                    "active_users": len(self.metrics["active_users"]),
                    "tasks_created": self.metrics["tasks_created"],
                    "tasks_completed": self.metrics["tasks_completed"],
                    "completion_rate": (
                        self.metrics["tasks_completed"] / self.metrics["tasks_created"] * 100
                        if self.metrics["tasks_created"] > 0 else 0
                    )
                }
            }

            logger.info(f"Analytics Report: {report}")

            # Reset some metrics
            self.metrics["api_calls"] = 0
            self.metrics["active_users"].clear()

    def get_api_routes(self) -> List[APIRouter]:
        """Define API routes for analytics."""
        router = APIRouter(prefix="/api/analytics", tags=["Analytics"])

        @router.get("/dashboard")
        async def get_dashboard():
            """Get analytics dashboard data."""
            return {
                "metrics": {
                    "page_views": self.metrics["page_views"],
                    "api_calls": self.metrics["api_calls"],
                    "active_users": len(self.metrics["active_users"]),
                    "tasks_created": self.metrics["tasks_created"],
                    "tasks_completed": self.metrics["tasks_completed"],
                },
                "charts": {
                    "task_completion_rate": (
                        self.metrics["tasks_completed"] / self.metrics["tasks_created"] * 100
                        if self.metrics["tasks_created"] > 0 else 0
                    ),
                    "user_activity": list(self.metrics["active_users"])[:10],
                },
                "timestamp": datetime.utcnow().isoformat()
            }

        @router.post("/track/event")
        async def track_event(event_name: str, properties: Dict[str, Any] = {}):
            """Track custom analytics event."""
            logger.info(f"Analytics event: {event_name} - {properties}")
            return {"status": "tracked", "event": event_name}

        return [router]


class FileStoragePlugin(BasePlugin):
    """
    File storage and management plugin.
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="file_storage",
            version="1.0.0",
            description="File storage and management",
            author="Example Team",
            category="storage",
            dependencies=["auth_advanced"],
        )
        self.storage_path = Path("./uploads")

    async def initialize(self, context) -> bool:
        """Initialize the file storage plugin."""
        logger.info("Initializing File Storage Plugin")

        # Create storage directory
        self.storage_path.mkdir(exist_ok=True)

        # Create subdirectories
        (self.storage_path / "images").mkdir(exist_ok=True)
        (self.storage_path / "documents").mkdir(exist_ok=True)
        (self.storage_path / "temp").mkdir(exist_ok=True)

        return True

    def get_api_routes(self) -> List[APIRouter]:
        """Define API routes for file storage."""
        router = APIRouter(prefix="/api/files", tags=["Files"])

        @router.post("/upload")
        async def upload_file(
            file: UploadFile = File(...),
            category: str = "documents"
        ):
            """Upload a file."""
            # Validate file size (max 10MB)
            contents = await file.read()
            if len(contents) > 10 * 1024 * 1024:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File too large. Maximum size is 10MB"
                )

            # Generate unique filename
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{timestamp}_{file.filename}"

            # Determine storage path
            if category not in ["images", "documents", "temp"]:
                category = "documents"

            file_path = self.storage_path / category / filename

            # Save file
            with open(file_path, "wb") as f:
                f.write(contents)

            return {
                "filename": filename,
                "category": category,
                "size": len(contents),
                "path": str(file_path),
                "url": f"/files/{category}/{filename}"
            }

        @router.get("/{category}/{filename}")
        async def download_file(category: str, filename: str):
            """Download a file."""
            file_path = self.storage_path / category / filename

            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            return FileResponse(file_path)

        @router.delete("/{category}/{filename}")
        async def delete_file(category: str, filename: str):
            """Delete a file."""
            file_path = self.storage_path / category / filename

            if not file_path.exists():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="File not found"
                )

            file_path.unlink()
            return {"message": "File deleted successfully"}

        @router.get("/list/{category}")
        async def list_files(category: str):
            """List files in a category."""
            category_path = self.storage_path / category

            if not category_path.exists():
                return {"files": []}

            files = []
            for file_path in category_path.glob("*"):
                if file_path.is_file():
                    files.append({
                        "filename": file_path.name,
                        "size": file_path.stat().st_size,
                        "modified": datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                        "url": f"/files/{category}/{file_path.name}"
                    })

            return {"files": files, "count": len(files)}

        return [router]


# ============================================================================
# Main Application
# ============================================================================

def create_example_app() -> NexusApp:
    """
    Create and configure the example application.
    """

    # Load configuration
    config = AppConfig(
        app={
            "name": "Nexus Example App",
            "version": "1.0.0",
            "description": "Complete example application showcasing Nexus Framework",
            "environment": "development",
            "debug": True,
        },
        server={
            "host": "0.0.0.0",
            "port": 8000,
            "reload": True,
        },
        database={
            "type": "sqlite",
            "connection": {
                "path": "./example.db"
            }
        },
        auth={
            "jwt_secret": "example-secret-key-change-in-production",
            "token_expiry": 3600,
        },
        plugins={
            "directory": "./plugins",
            "auto_load": True,
            "hot_reload": True,
        },
        logging={
            "level": "INFO",
            "file_enabled": True,
            "file_path": "./logs/example.log",
        }
    )

    # Create application
    app = create_nexus_app(
        title="Nexus Example Application",
        version="1.0.0",
        description="""
        ## Complete Example Application

        This example demonstrates:
        - **Task Management**: Create, update, and track tasks
        - **Authentication**: User registration and login with JWT
        - **Real-time Notifications**: WebSocket-based notifications
        - **Analytics**: Track usage and generate reports
        - **File Storage**: Upload and manage files
        - **API Documentation**: Auto-generated OpenAPI docs

        ### Getting Started
        1. Register a new account at `/api/auth/register`
        2. Login at `/api/auth/login`
        3. Explore the API at `/docs`
        4. Connect to WebSocket at `/ws/notifications/{user_id}`
        """,
        config=config
    )

    # Register custom plugins
    app.plugin_manager.plugins["notifications"] = NotificationPlugin()
    app.plugin_manager.plugins["analytics"] = AnalyticsPlugin()
    app.plugin_manager.plugins["file_storage"] = FileStoragePlugin()

    # Add startup handler
    @app.on_startup
    async def startup_handler():
        logger.info("=" * 60)
        logger.info("Nexus Example Application Starting")
        logger.info("=" * 60)
        logger.info(f"Environment: {config.app.environment}")
        logger.info(f"Debug Mode: {config.app.debug}")
        logger.info(f"Database: {config.database.type}")
        logger.info("=" * 60)

        # Initialize custom plugins
        for plugin_name in ["notifications", "analytics", "file_storage"]:
            plugin = app.plugin_manager.plugins.get(plugin_name)
            if plugin:
                context = type('Context', (), {
                    'get_service': app.get_service,
                    'get_config': lambda name, default={}: {},
                    'register_service': app.register_service,
                })()

                success = await plugin.initialize(context)
                if success:
                    logger.info(f"✓ Plugin '{plugin_name}' initialized")
                else:
                    logger.error(f"✗ Failed to initialize plugin '{plugin_name}'")

    # Add shutdown handler
    @app.on_shutdown
    async def shutdown_handler():
        logger.info("Nexus Example Application shutting down...")
        # Cleanup tasks here

    # Add custom routes
    @app.app.get("/", response_class=HTMLResponse)
    async def home():
        """Home page with links to documentation and features."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Nexus Example App</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }
                h1 { color: #333; }
                .links { list-style: none; padding: 0; }
                .links li { margin: 10px 0; }
                .links a { color: #007bff; text-decoration: none; font-size: 18px; }
                .links a:hover { text-decoration: underline; }
                .section { margin: 30px 0; padding: 20px; background: #f5f5f5; border-radius: 5px; }
                code { background: #e9ecef; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🚀 Nexus Example Application</h1>

            <div class="section">
                <h2>📚 Documentation</h2>
                <ul class="links">
                    <li><a href="/docs">📖 Interactive API Documentation (Swagger)</a></li>
                    <li><a href="/redoc">📄 Alternative API Documentation (ReDoc)</a></li>
                </ul>
            </div>

            <div class="section">
                <h2>🔧 Core Features</h2>
                <ul class="links">
                    <li><a href="/health">❤️ Health Check</a></li>
                    <li><a href="/api/system/info">ℹ️ System Information</a></li>
                    <li><a href="/api/plugins">🔌 Loaded Plugins</a></li>
                </ul>
            </div>

            <div class="section">
                <h2>📊 Analytics</h2>
                <ul class="links">
                    <li><a href="/api/analytics/dashboard">📈 Analytics Dashboard</a></li>
                </ul>
            </div>

            <div class="section">
                <h2>🔐 Authentication</h2>
                <p>Use the API documentation to:</p>
                <ul>
                    <li>Register a new account</li>
                    <li>Login and get access token</li>
                    <li>Access protected endpoints</li>
                </ul>
            </div>

            <div class="section">
                <h2>🔄 WebSocket</h2>
                <p>Connect to real-time notifications:</p>
                <code>ws://localhost:8000/ws/notifications/{user_id}</code>
            </div>

            <div class="section">
                <h2>💡 Getting Started</h2>
                <ol>
                    <li>Register an account via <code>POST /api/auth/register</code></li>
                    <li>Login via <code>POST /api/auth/login</code></li>
                    <li>Use the returned token for authenticated requests</li>
                    <li>Create tasks, upload files, and explore features!</li>
                </ol>
            </div>

            <hr>
            <p><small>Powered by Nexus Framework v2.0.0</small></p>
        </body>
        </html>
        """

    # Mount static files (if needed)
    app.app.mount("/static", StaticFiles(directory="static", html=True), name="static")

    # Add middleware for request tracking
    @app.app.middleware("http")
    async def track_requests(request, call_next):
        """Track API requests for analytics."""
        start_time = datetime.utcnow()

        # Track request
        await app.emit_event("api.request", {
            "path": request.url.path,
            "method": request.method,
            "timestamp": start_time.isoformat()
        })

        # Process request
        response = await call_next(request)

        # Log request duration
        duration = (datetime.utcnow() - start_time).total_seconds()
        logger.debug(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")

        return response

    # Background task example
    async def cleanup_temp_files():
        """Background task to clean up temporary files."""
        while True:
            await asyncio.sleep(3600)  # Run every hour

            temp_path = Path("./uploads/temp")
            if temp_path.exists():
                cutoff_time = datetime.utcnow() - timedelta(hours=24)

                for file_path in temp_path.glob("*"):
                    if file_path.is_file():
                        file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if file_time < cutoff_time:
                            file_path.unlink()
                            logger.info(f"Deleted old temp file: {file_path.name}")

    # Start background task
    @app.on_startup
    async def start_background_tasks():
        asyncio.create_task(cleanup_temp_files())

    return app


def main():
    """
    Main entry point for the application.
    """
    # Create application
    app = create_example_app()

    # Run application
    uvicorn.run(
        app.app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )


if __name__ == "__main__":
    main()
