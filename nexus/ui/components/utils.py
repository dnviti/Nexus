"""
Utility Functions for Nexus UI Components
Provides helper functions for component rendering, theming, and registration
"""

import json
import os
from functools import wraps
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, Union

from .base import BaseComponent, theme_manager


def render_component(component: BaseComponent) -> str:
    """
    Render a component to HTML string.

    Args:
        component: Component instance to render

    Returns:
        HTML string representation of the component
    """
    if not isinstance(component, BaseComponent):
        raise TypeError("Expected BaseComponent instance")

    return component.render()


def render_components(components: List[BaseComponent]) -> str:
    """
    Render multiple components to HTML string.

    Args:
        components: List of component instances to render

    Returns:
        HTML string representation of all components
    """
    html_parts = []
    for component in components:
        if isinstance(component, BaseComponent):
            html_parts.append(component.render())
        else:
            html_parts.append(str(component))

    return "".join(html_parts)


def get_theme(theme_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Get theme configuration.

    Args:
        theme_name: Name of the theme to get. If None, returns active theme.

    Returns:
        Theme configuration dictionary
    """
    if theme_name is None:
        theme_name = theme_manager.active_theme

    return theme_manager.get_theme(theme_name)


def set_theme(theme_name: str) -> None:
    """
    Set the active theme.

    Args:
        theme_name: Name of the theme to set as active
    """
    theme_manager.set_active_theme(theme_name)


def register_theme(name: str, theme_data: Dict[str, Any]) -> None:
    """
    Register a new theme.

    Args:
        name: Theme name
        theme_data: Theme configuration data
    """
    theme_manager.register_theme(name, theme_data)


def load_theme_from_file(theme_file: Union[str, Path]) -> None:
    """
    Load theme from a JSON file.

    Args:
        theme_file: Path to theme JSON file
    """
    theme_path = Path(theme_file)
    theme_manager.load_theme_from_file(theme_path)


def get_component_classes(
    component_type: str, variant: str = "default", theme: Optional[str] = None
) -> List[str]:
    """
    Get CSS classes for a component type and variant.

    Args:
        component_type: Type of component (e.g., "button", "card")
        variant: Component variant (e.g., "primary", "secondary")
        theme: Theme name, uses active theme if None

    Returns:
        List of CSS class names
    """
    if theme:
        original_theme = theme_manager.active_theme
        theme_manager.set_active_theme(theme)
        classes = theme_manager.get_component_classes(component_type, variant)
        theme_manager.set_active_theme(original_theme)
        return classes
    else:
        return theme_manager.get_component_classes(component_type, variant)


def get_component_styles(
    component_type: str, variant: str = "default", theme: Optional[str] = None
) -> Dict[str, str]:
    """
    Get CSS styles for a component type and variant.

    Args:
        component_type: Type of component
        variant: Component variant
        theme: Theme name, uses active theme if None

    Returns:
        Dictionary of CSS style properties
    """
    if theme:
        original_theme = theme_manager.active_theme
        theme_manager.set_active_theme(theme)
        styles = theme_manager.get_component_styles(component_type, variant)
        theme_manager.set_active_theme(original_theme)
        return styles
    else:
        return theme_manager.get_component_styles(component_type, variant)


# Component registry for plugin components
_component_registry: Dict[str, Type[BaseComponent]] = {}


def register_component(name: str, component_class: Type[BaseComponent]) -> None:
    """
    Register a custom component class.

    Args:
        name: Component name for registry
        component_class: Component class to register
    """
    if not issubclass(component_class, BaseComponent):
        raise TypeError("Component class must inherit from BaseComponent")

    _component_registry[name] = component_class


def get_registered_component(name: str) -> Optional[Type[BaseComponent]]:
    """
    Get a registered component class by name.

    Args:
        name: Component name

    Returns:
        Component class or None if not found
    """
    return _component_registry.get(name)


def list_registered_components() -> Dict[str, Type[BaseComponent]]:
    """
    List all registered components.

    Returns:
        Dictionary of component name to component class mappings
    """
    return _component_registry.copy()


def unregister_component(name: str) -> bool:
    """
    Unregister a component.

    Args:
        name: Component name to unregister

    Returns:
        True if component was unregistered, False if not found
    """
    if name in _component_registry:
        del _component_registry[name]
        return True
    return False


def component_registry_decorator(name: str) -> Callable[[Type[BaseComponent]], Type[BaseComponent]]:
    """
    Decorator to automatically register a component class.

    Args:
        name: Component name for registry

    Returns:
        Decorated component class

    Example:
        @component_registry_decorator("my_button")
        class MyButton(BaseComponent):
            pass
    """

    def decorator(component_class: Type[BaseComponent]) -> Type[BaseComponent]:
        register_component(name, component_class)
        return component_class

    return decorator


def create_component_factory(component_class: Type[BaseComponent]) -> Callable[..., BaseComponent]:
    """
    Create a factory function for a component class.

    Args:
        component_class: Component class to create factory for

    Returns:
        Factory function that creates component instances

    Example:
        button_factory = create_component_factory(Button)
        my_button = button_factory(content="Click me", variant="primary")
    """

    def factory(*args: Any, **kwargs: Any) -> BaseComponent:
        return component_class(*args, **kwargs)

    factory.__name__ = f"create_{component_class.__name__.lower()}"
    factory.__doc__ = f"Create a {component_class.__name__} instance."

    return factory


def merge_component_props(
    base_props: Dict[str, Any], override_props: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Merge component properties, with override taking precedence.

    Args:
        base_props: Base properties
        override_props: Override properties

    Returns:
        Merged properties dictionary
    """
    merged = base_props.copy()

    for key, value in override_props.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = {**merged[key], **value}
        elif key == "classes" and key in merged:
            # Merge CSS classes
            if isinstance(merged[key], list) and isinstance(value, list):
                merged[key] = list(set(merged[key] + value))
            else:
                merged[key] = value
        else:
            merged[key] = value

    return merged


def sanitize_html_attributes(attrs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize HTML attributes for security.

    Args:
        attrs: Attributes dictionary

    Returns:
        Sanitized attributes dictionary
    """
    sanitized = {}
    dangerous_attrs = ["javascript:", "onclick", "onerror", "onload"]

    for key, value in attrs.items():
        # Convert key to lowercase for checking
        key_lower = key.lower()

        # Skip dangerous attributes
        if any(danger in key_lower for danger in dangerous_attrs):
            continue

        # Skip if value contains dangerous content
        if isinstance(value, str):
            value_lower = value.lower()
            if any(danger in value_lower for danger in dangerous_attrs):
                continue

        sanitized[key] = value

    return sanitized


def escape_html(text: str) -> str:
    """
    Escape HTML special characters.

    Args:
        text: Text to escape

    Returns:
        HTML-escaped text
    """
    if not isinstance(text, str):
        text = str(text)

    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#x27;")
    )


def format_css_value(value: Union[str, int, float]) -> str:
    """
    Format a CSS value with proper units.

    Args:
        value: CSS value

    Returns:
        Formatted CSS value string
    """
    if isinstance(value, (int, float)):
        if value == 0:
            return "0"
        else:
            return f"{value}px"

    return str(value)


def generate_component_id(prefix: str = "component") -> str:
    """
    Generate a unique component ID.

    Args:
        prefix: ID prefix

    Returns:
        Unique component ID
    """
    import uuid

    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def validate_component_props(component: BaseComponent, required_props: List[str]) -> List[str]:
    """
    Validate that a component has required properties.

    Args:
        component: Component to validate
        required_props: List of required property names

    Returns:
        List of missing property names
    """
    missing_props = []

    for prop_name in required_props:
        if not hasattr(component, prop_name) or getattr(component, prop_name) is None:
            missing_props.append(prop_name)

    return missing_props


def create_responsive_classes(breakpoints: Dict[str, str]) -> List[str]:
    """
    Create responsive CSS classes from breakpoint definitions.

    Args:
        breakpoints: Dictionary of breakpoint name to class suffix

    Returns:
        List of responsive CSS classes

    Example:
        create_responsive_classes({"sm": "small", "md": "medium"})
        # Returns: ["responsive-sm-small", "responsive-md-medium"]
    """
    classes = []
    for breakpoint, suffix in breakpoints.items():
        classes.append(f"responsive-{breakpoint}-{suffix}")

    return classes


def apply_component_theme(
    component: BaseComponent, theme_component: str, variant: str = "default"
) -> BaseComponent:
    """
    Apply theme styles to a component.

    Args:
        component: Component to apply theme to
        theme_component: Component type in theme configuration
        variant: Component variant

    Returns:
        Component with theme applied
    """
    # Get theme classes and styles
    theme_classes = get_component_classes(theme_component, variant)
    theme_styles = get_component_styles(theme_component, variant)

    # Apply classes
    for css_class in theme_classes:
        component.add_class(css_class)

    # Apply styles
    for property_name, value in theme_styles.items():
        component.set_style(property_name, value)

    return component


def create_component_from_dict(component_data: Dict[str, Any]) -> BaseComponent:
    """
    Create a component from dictionary configuration.

    Args:
        component_data: Dictionary containing component configuration

    Returns:
        Component instance

    Example:
        component_data = {
            "type": "button",
            "props": {"content": "Click me", "variant": "primary"},
            "children": []
        }
    """
    from .base import Component  # Import here to avoid circular imports

    component_type = component_data.get("type", "div")
    props = component_data.get("props", {})
    content = component_data.get("content", "")
    children_data = component_data.get("children", [])

    # Create base component
    component = Component(tag=component_type, content=content)

    # Apply properties
    for key, value in props.items():
        if hasattr(component, key):
            setattr(component, key, value)
        elif hasattr(component.props, key):
            setattr(component.props, key, value)

    # Add children
    for child_data in children_data:
        if isinstance(child_data, dict):
            child = create_component_from_dict(child_data)
            component.add_child(child)
        else:
            from .base import Component

            text_component = Component(tag="span", content=str(child_data))
            component.add_child(text_component)

    return component


def component_to_dict(component: BaseComponent) -> Dict[str, Any]:
    """
    Convert a component to dictionary representation.

    Args:
        component: Component to convert

    Returns:
        Dictionary representation of component
    """
    return component.to_dict()


def debug_component(component: BaseComponent) -> str:
    """
    Generate debug information for a component.

    Args:
        component: Component to debug

    Returns:
        Debug information string
    """
    debug_info = []
    debug_info.append(f"Component Type: {type(component).__name__}")
    debug_info.append(f"Tag: {component.tag}")
    debug_info.append(f"ID: {component.props.id}")
    debug_info.append(f"Classes: {component.props.classes}")
    debug_info.append(f"Visible: {component.props.visible}")
    debug_info.append(f"Disabled: {component.props.disabled}")
    debug_info.append(f"Children Count: {len(component.children)}")

    if hasattr(component, "theme"):
        debug_info.append(f"Theme: {component.theme}")

    return "\n".join(debug_info)
