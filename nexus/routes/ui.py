"""
UI Routes for Nexus Framework
Serves user interface templates and component showcases
"""

from typing import Any, Dict

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ..ui.templates import (
    get_debug_interface_template,
    get_notifications_demo_template,
    get_simple_debug_template,
    render_template,
)


def create_ui_router() -> APIRouter:
    """Create UI router with template serving endpoints."""
    router = APIRouter(prefix="/ui", tags=["UI"])

    @router.get("/debug", response_class=HTMLResponse)
    async def debug_interface(request: Request) -> str:
        """Serve the main debug interface."""
        context = {
            "title": "Nexus Debug Interface",
            "api_base_url": str(request.base_url).rstrip("/") + "/api/v1",
        }
        return get_debug_interface_template(context)

    @router.get("/debug/simple", response_class=HTMLResponse)
    async def simple_debug() -> str:
        """Serve the simple debug interface."""
        return get_simple_debug_template()

    @router.get("/notifications", response_class=HTMLResponse)
    async def notifications_demo(request: Request) -> str:
        """Serve the notifications demo page."""
        context = {
            "api_base_url": str(request.base_url).rstrip("/") + "/api/v1",
        }
        return get_notifications_demo_template(context)

    @router.get("/showcase", response_class=HTMLResponse)
    async def component_showcase(request: Request) -> str:
        """Serve the component showcase page."""
        context = {
            "title": "Nexus UI Components Showcase",
            "description": "Explore available UI components for plugin development",
            "api_base_url": str(request.base_url).rstrip("/") + "/api/v1",
        }
        return render_template("component_showcase", context)

    @router.get("/", response_class=HTMLResponse)
    async def ui_index(request: Request) -> str:
        """Serve the main UI index page with navigation."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Nexus Framework UI</title>
    <link rel="stylesheet" href="/static/css/nexus-ui.css">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Nexus Framework UI</h1>
            <p>Choose an interface to explore the framework capabilities</p>
        </div>

        <div class="content">
            <div class="stats-grid">
                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🔍 Debug Interface</h3>
                    </div>
                    <div class="card-body">
                        <p>Real-time event monitoring and system debugging</p>
                        <a href="/ui/debug" class="btn btn-primary">Open Debug Interface</a>
                        <a href="/ui/debug/simple" class="btn btn-secondary">Simple Debug</a>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🔔 Notifications</h3>
                    </div>
                    <div class="card-body">
                        <p>Live notifications and inter-plugin communication demo</p>
                        <a href="/ui/notifications" class="btn btn-primary">View Demo</a>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">🎨 Component Showcase</h3>
                    </div>
                    <div class="card-body">
                        <p>Explore available UI components for plugin development</p>
                        <a href="/ui/showcase" class="btn btn-primary">View Components</a>
                    </div>
                </div>

                <div class="card">
                    <div class="card-header">
                        <h3 class="card-title">📚 Documentation</h3>
                    </div>
                    <div class="card-body">
                        <p>Framework documentation and API reference</p>
                        <a href="/docs" class="btn btn-primary">View Docs</a>
                    </div>
                </div>
            </div>

            <div class="section">
                <h2>🔗 Quick Links</h2>
                <div class="action-buttons">
                    <a href="/api/v1/plugins" class="btn btn-action">📋 Plugin Status</a>
                    <a href="/api/v1/system/info" class="btn btn-action">ℹ️ System Info</a>
                    <a href="/api/v1/system/health" class="btn btn-action">❤️ Health Check</a>
                    <a href="/admin" class="btn btn-action">⚙️ Admin Panel</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
        """

    return router
