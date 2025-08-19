"""
Nexus UI Components
Reusable UI components for plugin web interfaces
"""

from typing import Dict, Optional

from .base import BaseComponent, Component
from .data import Chart, DataGrid, MetricCard, Table
from .feedback import Alert, Modal, ProgressBar, Toast
from .forms import Button, Checkbox, Form, FormField, Input, Select
from .layouts import Card, Container, Grid, Panel, Sidebar
from .navigation import Breadcrumb, Menu, Pagination, Tabs
from .utils import get_theme, register_component, render_component

__all__ = [
    # Base components
    "BaseComponent",
    "Component",
    # Form components
    "Form",
    "FormField",
    "Button",
    "Input",
    "Select",
    "Checkbox",
    # Layout components
    "Container",
    "Grid",
    "Card",
    "Panel",
    "Sidebar",
    # Data components
    "Table",
    "DataGrid",
    "Chart",
    "MetricCard",
    # Navigation components
    "Menu",
    "Breadcrumb",
    "Tabs",
    "Pagination",
    # Feedback components
    "Alert",
    "Modal",
    "Toast",
    "ProgressBar",
    # Utilities
    "render_component",
    "get_theme",
    "register_component",
]

# Component registry for plugins to register custom components
_component_registry: Dict[str, type] = {}


def get_component(name: str) -> Optional[type]:
    """Get a registered component class."""
    return _component_registry.get(name)


def list_components() -> Dict[str, type]:
    """List all registered components."""
    return _component_registry.copy()
