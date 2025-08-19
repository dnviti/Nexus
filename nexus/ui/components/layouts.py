"""
Layout Components for Nexus UI System
Provides structural components for organizing UI elements
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

from .base import BaseComponent, ComponentProps, component


class GridSize(Enum):
    """Grid column sizes."""

    XS = "xs"
    SM = "sm"
    MD = "md"
    LG = "lg"
    XL = "xl"


class FlexDirection(Enum):
    """Flexbox direction values."""

    ROW = "row"
    ROW_REVERSE = "row-reverse"
    COLUMN = "column"
    COLUMN_REVERSE = "column-reverse"


class JustifyContent(Enum):
    """Flexbox justify-content values."""

    START = "flex-start"
    END = "flex-end"
    CENTER = "center"
    BETWEEN = "space-between"
    AROUND = "space-around"
    EVENLY = "space-evenly"


class AlignItems(Enum):
    """Flexbox align-items values."""

    START = "flex-start"
    END = "flex-end"
    CENTER = "center"
    STRETCH = "stretch"
    BASELINE = "baseline"


@dataclass
class ContainerProps(ComponentProps):
    """Properties for container components."""

    fluid: bool = False
    max_width: str = ""
    padding: str = ""
    margin: str = ""


class Container(BaseComponent):
    """Container component for responsive layouts."""

    def __init__(
        self,
        fluid: bool = False,
        max_width: str = "",
        props: Optional[ContainerProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.fluid = fluid
        self.max_width = max_width

        # Add container classes
        if fluid:
            self.add_class("container-fluid")
        else:
            self.add_class("container")

        if max_width:
            self.set_style("max-width", max_width)

    def render(self) -> str:
        """Render container."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<div {attrs}>{content}</div>"


@dataclass
class GridProps(ComponentProps):
    """Properties for grid components."""

    columns: int = 12
    gap: str = ""
    align_items: AlignItems = AlignItems.STRETCH
    justify_content: JustifyContent = JustifyContent.START


class Grid(BaseComponent):
    """CSS Grid container component."""

    def __init__(
        self, columns: int = 12, gap: str = "1rem", props: Optional[GridProps] = None, **kwargs: Any
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.columns = columns
        self.gap = gap

        # Add grid classes and styles
        self.add_class("grid")
        self.set_style("display", "grid")
        self.set_style("grid-template-columns", f"repeat({columns}, 1fr)")

        if gap:
            self.set_style("gap", gap)

    def render(self) -> str:
        """Render grid container."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<div {attrs}>{content}</div>"


@dataclass
class GridItemProps(ComponentProps):
    """Properties for grid item components."""

    col_span: int = 1
    row_span: int = 1
    col_start: Optional[int] = None
    row_start: Optional[int] = None


class GridItem(BaseComponent):
    """Grid item component."""

    def __init__(
        self,
        col_span: int = 1,
        row_span: int = 1,
        col_start: Optional[int] = None,
        row_start: Optional[int] = None,
        props: Optional[GridItemProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.col_span = col_span
        self.row_span = row_span
        self.col_start = col_start
        self.row_start = row_start

        # Add grid item classes and styles
        self.add_class("grid-item")

        if col_span > 1:
            self.set_style("grid-column", f"span {col_span}")

        if row_span > 1:
            self.set_style("grid-row", f"span {row_span}")

        if col_start:
            self.set_style("grid-column-start", str(col_start))

        if row_start:
            self.set_style("grid-row-start", str(row_start))

    def render(self) -> str:
        """Render grid item."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<div {attrs}>{content}</div>"


@dataclass
class FlexProps(ComponentProps):
    """Properties for flex components."""

    direction: FlexDirection = FlexDirection.ROW
    wrap: bool = False
    justify_content: JustifyContent = JustifyContent.START
    align_items: AlignItems = AlignItems.STRETCH
    gap: str = ""


class Flex(BaseComponent):
    """Flexbox container component."""

    def __init__(
        self,
        direction: FlexDirection = FlexDirection.ROW,
        wrap: bool = False,
        justify_content: JustifyContent = JustifyContent.START,
        align_items: AlignItems = AlignItems.STRETCH,
        gap: str = "0",
        props: Optional[FlexProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.direction = direction
        self.wrap = wrap
        self.justify_content = justify_content
        self.align_items = align_items
        self.gap = gap

        # Add flex classes and styles
        self.add_class("flex")
        self.set_style("display", "flex")
        self.set_style("flex-direction", direction.value)
        self.set_style("justify-content", justify_content.value)
        self.set_style("align-items", align_items.value)

        if wrap:
            self.set_style("flex-wrap", "wrap")

        if gap:
            self.set_style("gap", gap)

    def render(self) -> str:
        """Render flex container."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<div {attrs}>{content}</div>"


@dataclass
class FlexItemProps(ComponentProps):
    """Properties for flex item components."""

    flex_grow: int = 0
    flex_shrink: int = 1
    flex_basis: str = "auto"
    align_self: Optional[AlignItems] = None


class FlexItem(BaseComponent):
    """Flex item component."""

    def __init__(
        self,
        flex_grow: int = 0,
        flex_shrink: int = 1,
        flex_basis: str = "auto",
        align_self: Optional[AlignItems] = None,
        props: Optional[FlexItemProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.flex_grow = flex_grow
        self.flex_shrink = flex_shrink
        self.flex_basis = flex_basis
        self.align_self = align_self

        # Add flex item styles
        self.add_class("flex-item")
        self.set_style("flex", f"{flex_grow} {flex_shrink} {flex_basis}")

        if align_self:
            self.set_style("align-self", align_self.value)

    def render(self) -> str:
        """Render flex item."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<div {attrs}>{content}</div>"


@dataclass
class CardProps(ComponentProps):
    """Properties for card components."""

    variant: str = "default"
    elevated: bool = False
    padding: str = ""
    title: str = ""
    subtitle: str = ""


class Card(BaseComponent):
    """Card component for content grouping."""

    def __init__(
        self,
        variant: str = "default",
        elevated: bool = False,
        title: str = "",
        subtitle: str = "",
        props: Optional[CardProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.variant = variant
        self.elevated = elevated
        self.title = title
        self.subtitle = subtitle

        # Add card classes
        self.add_class("card")
        self.add_class(f"card-{variant}")

        if elevated:
            self.add_class("card-elevated")

    def render(self) -> str:
        """Render card with optional header."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content_parts = []

        # Card header
        if self.title or self.subtitle:
            header_content = []
            if self.title:
                header_content.append(f'<h3 class="card-title">{self.title}</h3>')
            if self.subtitle:
                header_content.append(f'<p class="card-subtitle">{self.subtitle}</p>')

            content_parts.append(f'<div class="card-header">{"".join(header_content)}</div>')

        # Card body
        body_content = self._render_children()
        if body_content:
            content_parts.append(f'<div class="card-body">{body_content}</div>')

        return f'<div {attrs}>{"".join(content_parts)}</div>'


@dataclass
class PanelProps(ComponentProps):
    """Properties for panel components."""

    collapsible: bool = False
    collapsed: bool = False
    title: str = ""


class Panel(BaseComponent):
    """Panel component for grouping content."""

    def __init__(
        self,
        title: str = "",
        collapsible: bool = False,
        collapsed: bool = False,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.title = title
        self.collapsible = collapsible
        self.collapsed = collapsed

        # Add panel classes
        self.add_class("panel")

        if collapsible:
            self.add_class("panel-collapsible")

        if collapsed:
            self.add_class("panel-collapsed")

    def render(self) -> str:
        """Render panel with optional collapsible behavior."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content_parts = []

        # Panel header
        if self.title:
            header_classes = ["panel-header"]
            if self.collapsible:
                header_classes.append("panel-header-clickable")

            header_content = f'<span class="panel-title">{self.title}</span>'
            if self.collapsible:
                icon = "▼" if not self.collapsed else "▶"
                header_content += f'<span class="panel-toggle">{icon}</span>'

            content_parts.append(f'<div class="{" ".join(header_classes)}">{header_content}</div>')

        # Panel body
        body_classes = ["panel-body"]
        if self.collapsed:
            body_classes.append("panel-body-collapsed")

        body_content = self._render_children()
        content_parts.append(f'<div class="{" ".join(body_classes)}">{body_content}</div>')

        return f'<div {attrs}>{"".join(content_parts)}</div>'


@dataclass
class SidebarProps(ComponentProps):
    """Properties for sidebar components."""

    position: str = "left"
    width: str = "250px"
    collapsible: bool = True
    collapsed: bool = False


class Sidebar(BaseComponent):
    """Sidebar navigation component."""

    def __init__(
        self,
        position: str = "left",
        width: str = "250px",
        collapsible: bool = True,
        collapsed: bool = False,
        props: Optional[SidebarProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("aside", props, **kwargs)
        self.position = position
        self.width = width
        self.collapsible = collapsible
        self.collapsed = collapsed

        # Add sidebar classes and styles
        self.add_class("sidebar")
        self.add_class(f"sidebar-{position}")

        if collapsible:
            self.add_class("sidebar-collapsible")

        if collapsed:
            self.add_class("sidebar-collapsed")

        # Set width
        if not collapsed:
            self.set_style("width", width)

    def render(self) -> str:
        """Render sidebar."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<aside {attrs}>{content}</aside>"


class Section(BaseComponent):
    """Semantic section component."""

    def __init__(
        self, title: str = "", props: Optional[ComponentProps] = None, **kwargs: Any
    ) -> None:
        super().__init__("section", props, **kwargs)
        self.title = title
        self.add_class("section")

    def render(self) -> str:
        """Render section with optional title."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content_parts = []

        if self.title:
            content_parts.append(f'<h2 class="section-title">{self.title}</h2>')

        content_parts.append(self._render_children())

        return f'<section {attrs}>{"".join(content_parts)}</section>'


class Header(BaseComponent):
    """Header component."""

    def __init__(
        self, level: int = 1, props: Optional[ComponentProps] = None, **kwargs: Any
    ) -> None:
        tag = f"h{min(max(level, 1), 6)}"  # Ensure level is between 1-6
        super().__init__(tag, props, **kwargs)
        self.level = level
        self.add_class(f"heading-{level}")

    def render(self) -> str:
        """Render header."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content = self._render_children()

        return f"<{self.tag} {attrs}>{content}</{self.tag}>"


class Divider(BaseComponent):
    """Horizontal divider component."""

    def __init__(
        self, text: str = "", props: Optional[ComponentProps] = None, **kwargs: Any
    ) -> None:
        super().__init__("hr", props, **kwargs)
        self.text = text
        self.add_class("divider")

    def render(self) -> str:
        """Render divider."""
        if not self.props.visible:
            return ""

        if self.text:
            attrs = self._render_attributes()
            return f'<div {attrs}><span class="divider-text">{self.text}</span></div>'
        else:
            attrs = self._render_attributes()
            return f"<hr {attrs}>"


class Spacer(BaseComponent):
    """Spacer component for adding space."""

    def __init__(
        self,
        size: str = "1rem",
        horizontal: bool = False,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.size = size
        self.horizontal = horizontal

        self.add_class("spacer")

        if horizontal:
            self.set_style("width", size)
            self.set_style("height", "1px")
        else:
            self.set_style("height", size)
            self.set_style("width", "1px")

    def render(self) -> str:
        """Render spacer."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        return f"<div {attrs}></div>"


# Convenience functions for creating layout components
def container(fluid: bool = False, **kwargs: Any) -> Container:
    """Create a container."""
    return Container(fluid, **kwargs)


def grid(columns: int = 12, gap: str = "1rem", **kwargs: Any) -> Grid:
    """Create a grid container."""
    return Grid(columns, gap, **kwargs)


def flex(
    direction: FlexDirection = FlexDirection.ROW,
    justify: JustifyContent = JustifyContent.START,
    align: AlignItems = AlignItems.STRETCH,
    **kwargs: Any,
) -> Flex:
    """Create a flex container."""
    return Flex(direction, justify_content=justify, align_items=align, **kwargs)


def card(title: str = "", elevated: bool = False, **kwargs: Any) -> Card:
    """Create a card."""
    return Card(title=title, elevated=elevated, **kwargs)


def panel(title: str = "", collapsible: bool = False, **kwargs: Any) -> Panel:
    """Create a panel."""
    return Panel(title, collapsible, **kwargs)


def sidebar(position: str = "left", width: str = "250px", **kwargs: Any) -> Sidebar:
    """Create a sidebar."""
    return Sidebar(position, width, **kwargs)


def section(title: str = "", **kwargs: Any) -> Section:
    """Create a section."""
    return Section(title, **kwargs)


def header(level: int = 1, text: str = "", **kwargs: Any) -> Header:
    """Create a header."""
    h = Header(level, **kwargs)
    if text:
        h.content = text
    return h


def divider(text: str = "", **kwargs: Any) -> Divider:
    """Create a divider."""
    return Divider(text, **kwargs)


def spacer(size: str = "1rem", horizontal: bool = False, **kwargs: Any) -> Spacer:
    """Create a spacer."""
    return Spacer(size, horizontal, **kwargs)
