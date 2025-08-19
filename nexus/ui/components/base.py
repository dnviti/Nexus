"""
Base UI Component System for Nexus Framework
Provides foundation classes for building reusable UI components
"""

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Union


@dataclass
class ComponentProps:
    """Base properties for all components."""

    id: Optional[str] = None
    classes: List[str] = field(default_factory=list)
    styles: Dict[str, str] = field(default_factory=dict)
    attributes: Dict[str, Any] = field(default_factory=dict)
    data_attributes: Dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    disabled: bool = False


class BaseComponent(ABC):
    """
    Abstract base class for all UI components.

    Provides the foundation for building reusable, themeable UI components
    that plugins can use to create consistent interfaces.
    """

    def __init__(
        self,
        tag: str = "div",
        props: Optional[ComponentProps] = None,
        children: Optional[List["BaseComponent"]] = None,
        content: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        self.tag = tag
        self.props = props or ComponentProps()
        self.children = children or []
        self.content = content
        self.theme = "default"

        # Apply any additional properties from kwargs
        for key, value in kwargs.items():
            if hasattr(self.props, key):
                setattr(self.props, key, value)

    @abstractmethod
    def render(self) -> str:
        """Render the component to HTML."""
        pass

    def add_child(self, child: "BaseComponent") -> "BaseComponent":
        """Add a child component."""
        self.children.append(child)
        return self

    def add_class(self, class_name: str) -> "BaseComponent":
        """Add a CSS class to the component."""
        if class_name not in self.props.classes:
            self.props.classes.append(class_name)
        return self

    def remove_class(self, class_name: str) -> "BaseComponent":
        """Remove a CSS class from the component."""
        if class_name in self.props.classes:
            self.props.classes.remove(class_name)
        return self

    def set_style(self, property: str, value: str) -> "BaseComponent":
        """Set a CSS style property."""
        self.props.styles[property] = value
        return self

    def set_attribute(self, name: str, value: Any) -> "BaseComponent":
        """Set an HTML attribute."""
        self.props.attributes[name] = value
        return self

    def set_data(self, name: str, value: Any) -> "BaseComponent":
        """Set a data attribute."""
        self.props.data_attributes[name] = value
        return self

    def set_theme(self, theme: str) -> "BaseComponent":
        """Set the component theme."""
        self.theme = theme
        return self

    def show(self) -> "BaseComponent":
        """Show the component."""
        self.props.visible = True
        return self

    def hide(self) -> "BaseComponent":
        """Hide the component."""
        self.props.visible = False
        return self

    def enable(self) -> "BaseComponent":
        """Enable the component."""
        self.props.disabled = False
        return self

    def disable(self) -> "BaseComponent":
        """Disable the component."""
        self.props.disabled = True
        return self

    def _render_attributes(self) -> str:
        """Render HTML attributes."""
        attrs = []

        # ID attribute
        if self.props.id:
            attrs.append(f'id="{self.props.id}"')

        # CSS classes
        if self.props.classes:
            classes = " ".join(self.props.classes)
            attrs.append(f'class="{classes}"')

        # Inline styles
        if self.props.styles:
            styles = "; ".join([f"{k}: {v}" for k, v in self.props.styles.items()])
            attrs.append(f'style="{styles}"')

        # Regular attributes
        for name, value in self.props.attributes.items():
            if isinstance(value, bool):
                if value:
                    attrs.append(name)
            else:
                attrs.append(f'{name}="{value}"')

        # Data attributes
        for name, value in self.props.data_attributes.items():
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            attrs.append(f'data-{name}="{value}"')

        # Visibility and disabled state
        if not self.props.visible:
            attrs.append('style="display: none"')

        if self.props.disabled:
            attrs.append("disabled")

        return " ".join(attrs)

    def _render_children(self) -> str:
        """Render child components."""
        if not self.children:
            return self.content or ""

        children_html = []
        for child in self.children:
            if isinstance(child, BaseComponent):
                children_html.append(child.render())
            else:
                children_html.append(str(child))

        return "".join(children_html)

    def to_dict(self) -> Dict[str, Any]:
        """Convert component to dictionary representation."""
        return {
            "tag": self.tag,
            "props": {
                "id": self.props.id,
                "classes": self.props.classes,
                "styles": self.props.styles,
                "attributes": self.props.attributes,
                "data_attributes": self.props.data_attributes,
                "visible": self.props.visible,
                "disabled": self.props.disabled,
            },
            "content": self.content,
            "children": [
                child.to_dict() if isinstance(child, BaseComponent) else str(child)
                for child in self.children
            ],
            "theme": self.theme,
        }

    def __str__(self) -> str:
        """String representation renders the component."""
        return self.render()


class Component(BaseComponent):
    """
    Generic HTML component implementation.

    Can be used to create any HTML element with proper attributes,
    styling, and child components.
    """

    def __init__(
        self,
        tag: str = "div",
        props: Optional[ComponentProps] = None,
        children: Optional[List[BaseComponent]] = None,
        content: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(tag, props, children, content, **kwargs)

    def render(self) -> str:
        """Render the generic component to HTML."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        children = self._render_children()

        # Self-closing tags
        if self.tag in ["img", "input", "br", "hr", "meta", "link"]:
            return f"<{self.tag} {attrs}>" if attrs else f"<{self.tag}>"

        # Regular tags
        if attrs:
            return f"<{self.tag} {attrs}>{children}</{self.tag}>"
        else:
            return f"<{self.tag}>{children}</{self.tag}>"


class ComponentBuilder:
    """
    Fluent interface for building components.

    Provides a convenient way to create and configure components
    using method chaining.
    """

    def __init__(self, component: BaseComponent):
        self.component = component

    def id(self, id_value: str) -> "ComponentBuilder":
        """Set component ID."""
        self.component.props.id = id_value
        return self

    def css(self, *classes: str) -> "ComponentBuilder":
        """Add CSS classes."""
        for class_name in classes:
            self.component.add_class(class_name)
        return self

    def style(self, **styles: str) -> "ComponentBuilder":
        """Set CSS styles."""
        for prop, value in styles.items():
            prop = prop.replace("_", "-")  # Convert snake_case to kebab-case
            self.component.set_style(prop, value)
        return self

    def attr(self, **attributes: Any) -> "ComponentBuilder":
        """Set HTML attributes."""
        for name, value in attributes.items():
            self.component.set_attribute(name, value)
        return self

    def data(self, **data_attrs: Any) -> "ComponentBuilder":
        """Set data attributes."""
        for name, value in data_attrs.items():
            self.component.set_data(name, value)
        return self

    def content(self, content: str) -> "ComponentBuilder":
        """Set component content."""
        self.component.content = content
        return self

    def child(self, *children: BaseComponent) -> "ComponentBuilder":
        """Add child components."""
        for child in children:
            self.component.add_child(child)
        return self

    def theme(self, theme: str) -> "ComponentBuilder":
        """Set component theme."""
        self.component.set_theme(theme)
        return self

    def build(self) -> BaseComponent:
        """Build and return the component."""
        return self.component


def component(tag: str = "div", **kwargs: Any) -> ComponentBuilder:
    """
    Create a new component with fluent builder interface.

    Args:
        tag: HTML tag name
        **kwargs: Additional component properties

    Returns:
        ComponentBuilder for method chaining

    Examples:
        # Simple div
        div = component("div").content("Hello World").build()

        # Button with classes and events
        button = component("button").css("btn", "btn-primary").content("Click Me").build()

        # Complex nested structure
        card = component("div").css("card").child(
            component("div").css("card-header").content("Title"),
            component("div").css("card-body").content("Content")
        ).build()
    """
    comp = Component(tag, **kwargs)
    return ComponentBuilder(comp)


class ThemeManager:
    """
    Manages component themes and styling.

    Provides functionality to load, register, and apply themes
    to components throughout the application.
    """

    def __init__(self) -> None:
        self.themes: Dict[str, Dict[str, Any]] = {}
        self.active_theme = "default"
        self.theme_path: Optional[Path] = None

    def register_theme(self, name: str, theme_data: Dict[str, Any]) -> None:
        """Register a new theme."""
        self.themes[name] = theme_data

    def get_theme(self, name: str) -> Dict[str, Any]:
        """Get theme data by name."""
        return self.themes.get(name, {})

    def set_active_theme(self, name: str) -> None:
        """Set the active theme."""
        if name in self.themes:
            self.active_theme = name

    def load_theme_from_file(self, theme_file: Path) -> None:
        """Load theme from JSON file."""
        if theme_file.exists():
            with open(theme_file, "r") as f:
                theme_data = json.load(f)
                theme_name = theme_file.stem
                self.register_theme(theme_name, theme_data)

    def get_component_classes(self, component_type: str, variant: str = "default") -> List[str]:
        """Get CSS classes for a component type and variant."""
        theme = self.get_theme(self.active_theme)
        component_config = theme.get("components", {}).get(component_type, {})
        variant_config = component_config.get("variants", {}).get(variant, {})

        classes = []
        classes.extend(component_config.get("base_classes", []))
        classes.extend(variant_config.get("classes", []))

        return classes

    def get_component_styles(self, component_type: str, variant: str = "default") -> Dict[str, str]:
        """Get CSS styles for a component type and variant."""
        theme = self.get_theme(self.active_theme)
        component_config = theme.get("components", {}).get(component_type, {})
        variant_config = component_config.get("variants", {}).get(variant, {})

        styles = {}
        styles.update(component_config.get("base_styles", {}))
        styles.update(variant_config.get("styles", {}))

        return styles


# Global theme manager instance
theme_manager = ThemeManager()

# Register default theme
theme_manager.register_theme(
    "default",
    {
        "name": "Default Nexus Theme",
        "colors": {
            "primary": "#667eea",
            "secondary": "#764ba2",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "info": "#3b82f6",
        },
        "components": {
            "button": {
                "base_classes": ["btn"],
                "variants": {
                    "primary": {"classes": ["btn-primary"]},
                    "secondary": {"classes": ["btn-secondary"]},
                    "success": {"classes": ["btn-success"]},
                    "danger": {"classes": ["btn-danger"]},
                },
            },
            "card": {
                "base_classes": ["card"],
                "variants": {
                    "default": {"classes": ["card-default"]},
                    "elevated": {"classes": ["card-elevated"]},
                },
            },
        },
    },
)
