"""
Nexus Framework Routes Package
HTTP route handlers organized by functional area.
"""

from .core import create_core_router
from .debug import create_debug_router
from .events import create_events_router
from .plugins import create_plugins_router
from .ui import create_ui_router

__all__ = [
    "create_core_router",
    "create_events_router",
    "create_plugins_router",
    "create_debug_router",
    "create_ui_router",
]
