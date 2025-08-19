"""
Nexus Framework UI Package
User interface components, templates, and utilities for the framework.
"""

from .templates import (
    get_debug_interface_template,
    get_notifications_demo_template,
    get_simple_debug_template,
)

__all__ = [
    "get_debug_interface_template",
    "get_simple_debug_template",
    "get_notifications_demo_template",
]
