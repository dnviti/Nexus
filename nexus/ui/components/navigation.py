"""
Navigation Components for Nexus UI System
Provides navigation elements like menus, breadcrumbs, tabs, and pagination
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseComponent, ComponentProps


class MenuOrientation(Enum):
    """Menu orientation options."""

    HORIZONTAL = "horizontal"
    VERTICAL = "vertical"


class MenuItemType(Enum):
    """Menu item types."""

    LINK = "link"
    BUTTON = "button"
    DIVIDER = "divider"
    HEADER = "header"


@dataclass
class MenuItem:
    """Menu item definition."""

    id: str
    label: str
    type: MenuItemType = MenuItemType.LINK
    url: Optional[str] = None
    onclick: Optional[str] = None
    icon: Optional[str] = None
    badge: Optional[str] = None
    active: bool = False
    disabled: bool = False
    children: List["MenuItem"] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)


@dataclass
class MenuProps(ComponentProps):
    """Properties for menu components."""

    orientation: MenuOrientation = MenuOrientation.HORIZONTAL
    collapsible: bool = False
    collapsed: bool = False


class Menu(BaseComponent):
    """Menu component for navigation."""

    def __init__(
        self,
        items: Optional[List[MenuItem]] = None,
        orientation: MenuOrientation = MenuOrientation.HORIZONTAL,
        collapsible: bool = False,
        props: Optional[MenuProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("nav", props, **kwargs)
        self.items = items or []
        self.orientation = orientation
        self.collapsible = collapsible

        # Add menu classes
        self.add_class("menu")
        self.add_class(f"menu-{orientation.value}")

        if collapsible:
            self.add_class("menu-collapsible")

    def add_item(
        self,
        id: str,
        label: str,
        url: Optional[str] = None,
        icon: Optional[str] = None,
        active: bool = False,
        **kwargs: Any,
    ) -> "Menu":
        """Add a menu item."""
        item = MenuItem(id=id, label=label, url=url, icon=icon, active=active, **kwargs)
        self.items.append(item)
        return self

    def add_divider(self) -> "Menu":
        """Add a divider to the menu."""
        item = MenuItem(id=f"divider-{len(self.items)}", label="", type=MenuItemType.DIVIDER)
        self.items.append(item)
        return self

    def add_header(self, label: str) -> "Menu":
        """Add a header to the menu."""
        item = MenuItem(
            id=f"header-{len(self.items)}",
            label=label,
            type=MenuItemType.HEADER,
        )
        self.items.append(item)
        return self

    def render(self) -> str:
        """Render menu."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        menu_html = self._render_menu_items(self.items)

        if self.orientation == MenuOrientation.HORIZONTAL:
            return f'<nav {attrs}><ul class="menu-list">{menu_html}</ul></nav>'
        else:
            return f'<nav {attrs}><ul class="menu-list">{menu_html}</ul></nav>'

    def _render_menu_items(self, items: List[MenuItem], level: int = 0) -> str:
        """Render menu items recursively."""
        html_parts = []

        for item in items:
            if item.type == MenuItemType.DIVIDER:
                html_parts.append('<li class="menu-divider"></li>')
                continue

            if item.type == MenuItemType.HEADER:
                html_parts.append(f'<li class="menu-header">{item.label}</li>')
                continue

            # Regular menu item
            item_classes = ["menu-item"]
            if item.active:
                item_classes.append("active")
            if item.disabled:
                item_classes.append("disabled")
            if item.children:
                item_classes.append("has-children")

            item_content = ""
            if item.icon:
                item_content += f'<span class="menu-icon">{item.icon}</span>'

            item_content += f'<span class="menu-label">{item.label}</span>'

            if item.badge:
                item_content += f'<span class="menu-badge">{item.badge}</span>'

            # Create link or button
            if item.type == MenuItemType.LINK and item.url:
                link_attrs = f'href="{item.url}"'
                if item.onclick:
                    link_attrs += f' onclick="{item.onclick}"'
                item_html = f'<a class="menu-link" {link_attrs}>{item_content}</a>'
            else:
                btn_attrs = ""
                if item.onclick:
                    btn_attrs += f' onclick="{item.onclick}"'
                if item.disabled:
                    btn_attrs += " disabled"
                item_html = f'<button class="menu-button" {btn_attrs}>{item_content}</button>'

            # Add submenu if has children
            if item.children:
                submenu_html = self._render_menu_items(item.children, level + 1)
                item_html += f'<ul class="submenu">{submenu_html}</ul>'

            html_parts.append(f'<li class="{" ".join(item_classes)}">{item_html}</li>')

        return "".join(html_parts)


@dataclass
class BreadcrumbItem:
    """Breadcrumb item definition."""

    label: str
    url: Optional[str] = None
    active: bool = False


class Breadcrumb(BaseComponent):
    """Breadcrumb navigation component."""

    def __init__(
        self,
        items: Optional[List[BreadcrumbItem]] = None,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("nav", props, **kwargs)
        self.items = items or []
        self.add_class("breadcrumb")

    def add_item(self, label: str, url: Optional[str] = None, active: bool = False) -> "Breadcrumb":
        """Add a breadcrumb item."""
        item = BreadcrumbItem(label=label, url=url, active=active)
        self.items.append(item)
        return self

    def render(self) -> str:
        """Render breadcrumb."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        items_html = []

        for i, item in enumerate(self.items):
            item_classes = ["breadcrumb-item"]
            if item.active or i == len(self.items) - 1:
                item_classes.append("active")

            if item.url and not item.active and i != len(self.items) - 1:
                item_html = f'<a href="{item.url}">{item.label}</a>'
            else:
                item_html = item.label

            items_html.append(f'<li class="{" ".join(item_classes)}">{item_html}</li>')

        return f'<nav {attrs}><ol class="breadcrumb-list">{"".join(items_html)}</ol></nav>'


@dataclass
class TabItem:
    """Tab item definition."""

    id: str
    label: str
    content: str = ""
    active: bool = False
    disabled: bool = False
    icon: Optional[str] = None


class Tabs(BaseComponent):
    """Tabs component for organizing content."""

    def __init__(
        self,
        items: Optional[List[TabItem]] = None,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.items = items or []
        self.add_class("tabs")

    def add_tab(
        self,
        id: str,
        label: str,
        content: str = "",
        active: bool = False,
        icon: Optional[str] = None,
    ) -> "Tabs":
        """Add a tab."""
        tab = TabItem(id=id, label=label, content=content, active=active, icon=icon)
        self.items.append(tab)
        return self

    def render(self) -> str:
        """Render tabs."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()

        # Tab navigation
        nav_html = '<ul class="tab-nav">'
        for tab in self.items:
            nav_classes = ["tab-nav-item"]
            if tab.active:
                nav_classes.append("active")
            if tab.disabled:
                nav_classes.append("disabled")

            tab_content = ""
            if tab.icon:
                tab_content += f'<span class="tab-icon">{tab.icon}</span>'
            tab_content += f'<span class="tab-label">{tab.label}</span>'

            nav_html += f"""
            <li class="{" ".join(nav_classes)}">
                <button class="tab-button" data-tab="{tab.id}" {'disabled' if tab.disabled else ''}>
                    {tab_content}
                </button>
            </li>
            """

        nav_html += "</ul>"

        # Tab content
        content_html = '<div class="tab-content">'
        for tab in self.items:
            content_classes = ["tab-pane"]
            if tab.active:
                content_classes.append("active")

            content_html += f"""
            <div class="{" ".join(content_classes)}" id="tab-{tab.id}">
                {tab.content}
            </div>
            """

        content_html += "</div>"

        # Tab switching script
        script_html = """
        <script>
            document.querySelectorAll('.tab-button').forEach(button => {
                button.addEventListener('click', function() {
                    const tabId = this.getAttribute('data-tab');
                    const tabsContainer = this.closest('.tabs');

                    // Remove active from all tabs and panes
                    tabsContainer.querySelectorAll('.tab-nav-item').forEach(item => {
                        item.classList.remove('active');
                    });
                    tabsContainer.querySelectorAll('.tab-pane').forEach(pane => {
                        pane.classList.remove('active');
                    });

                    // Add active to clicked tab and corresponding pane
                    this.parentElement.classList.add('active');
                    const targetPane = tabsContainer.querySelector('#tab-' + tabId);
                    if (targetPane) {
                        targetPane.classList.add('active');
                    }
                });
            });
        </script>
        """

        return f"<div {attrs}>{nav_html}{content_html}{script_html}</div>"


class Pagination(BaseComponent):
    """Pagination component."""

    def __init__(
        self,
        current_page: int = 1,
        total_pages: int = 1,
        page_size: int = 10,
        total_items: int = 0,
        show_info: bool = True,
        show_size_selector: bool = False,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("nav", props, **kwargs)
        self.current_page = current_page
        self.total_pages = total_pages
        self.page_size = page_size
        self.total_items = total_items
        self.show_info = show_info
        self.show_size_selector = show_size_selector

        self.add_class("pagination")

    def render(self) -> str:
        """Render pagination."""
        if not self.props.visible or self.total_pages <= 1:
            return ""

        attrs = self._render_attributes()
        parts = []

        # Pagination info
        if self.show_info:
            start_item = (self.current_page - 1) * self.page_size + 1
            end_item = min(self.current_page * self.page_size, self.total_items)
            info_html = f"""
            <div class="pagination-info">
                Showing {start_item}-{end_item} of {self.total_items} items
            </div>
            """
            parts.append(info_html)

        # Page size selector
        if self.show_size_selector:
            size_html = """
            <div class="pagination-size">
                <label>Items per page:</label>
                <select class="pagination-size-select">
                    <option value="10">10</option>
                    <option value="25">25</option>
                    <option value="50">50</option>
                    <option value="100">100</option>
                </select>
            </div>
            """
            parts.append(size_html)

        # Pagination controls
        controls_html = '<ul class="pagination-list">'

        # Previous button
        prev_classes = ["pagination-item"]
        if self.current_page <= 1:
            prev_classes.append("disabled")

        controls_html += f"""
        <li class="{" ".join(prev_classes)}">
            <button class="pagination-button" data-page="{self.current_page - 1}" {'disabled' if self.current_page <= 1 else ''}>
                Previous
            </button>
        </li>
        """

        # Page numbers
        start_page = max(1, self.current_page - 2)
        end_page = min(self.total_pages, self.current_page + 2)

        # First page
        if start_page > 1:
            controls_html += """
            <li class="pagination-item">
                <button class="pagination-button" data-page="1">1</button>
            </li>
            """
            if start_page > 2:
                controls_html += '<li class="pagination-item disabled"><span class="pagination-ellipsis">...</span></li>'

        # Page range
        for page in range(start_page, end_page + 1):
            page_classes = ["pagination-item"]
            if page == self.current_page:
                page_classes.append("active")

            controls_html += f"""
            <li class="{" ".join(page_classes)}">
                <button class="pagination-button" data-page="{page}">{page}</button>
            </li>
            """

        # Last page
        if end_page < self.total_pages:
            if end_page < self.total_pages - 1:
                controls_html += '<li class="pagination-item disabled"><span class="pagination-ellipsis">...</span></li>'
            controls_html += f"""
            <li class="pagination-item">
                <button class="pagination-button" data-page="{self.total_pages}">{self.total_pages}</button>
            </li>
            """

        # Next button
        next_classes = ["pagination-item"]
        if self.current_page >= self.total_pages:
            next_classes.append("disabled")

        controls_html += f"""
        <li class="{" ".join(next_classes)}">
            <button class="pagination-button" data-page="{self.current_page + 1}" {'disabled' if self.current_page >= self.total_pages else ''}>
                Next
            </button>
        </li>
        """

        controls_html += "</ul>"
        parts.append(controls_html)

        return f'<nav {attrs}>{"".join(parts)}</nav>'


# Convenience functions
def menu(
    orientation: Union[MenuOrientation, str] = MenuOrientation.HORIZONTAL, **kwargs: Any
) -> Menu:
    """Create a menu."""
    if isinstance(orientation, str):
        orientation = MenuOrientation(orientation)
    return Menu(orientation=orientation, **kwargs)


def breadcrumb(*items: str) -> Breadcrumb:
    """Create a breadcrumb from a list of labels."""
    bc = Breadcrumb()
    for i, item in enumerate(items):
        bc.add_item(item, active=(i == len(items) - 1))
    return bc


def tabs(*tab_items: Any) -> Tabs:
    """Create tabs from a list of (id, label, content) tuples."""
    tab_component = Tabs()
    for i, item in enumerate(tab_items):
        if len(item) >= 3:
            tab_component.add_tab(item[0], item[1], item[2], active=(i == 0))
        elif len(item) >= 2:
            tab_component.add_tab(item[0], item[1], active=(i == 0))
    return tab_component


def pagination(current: int, total: int, **kwargs: Any) -> Pagination:
    """Create pagination."""
    return Pagination(current_page=current, total_pages=total, **kwargs)
