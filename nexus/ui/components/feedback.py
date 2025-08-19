"""
Feedback Components for Nexus UI System
Provides user feedback components like alerts, modals, toasts, and progress bars
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseComponent, ComponentProps


class AlertType(Enum):
    """Alert types."""

    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"


class AlertVariant(Enum):
    """Alert style variants."""

    DEFAULT = "default"
    FILLED = "filled"
    OUTLINED = "outlined"


@dataclass
class AlertProps(ComponentProps):
    """Properties for alert components."""

    alert_type: AlertType = AlertType.INFO
    variant: AlertVariant = AlertVariant.DEFAULT
    dismissible: bool = False
    icon: Optional[str] = None
    title: Optional[str] = None


class Alert(BaseComponent):
    """Alert component for displaying messages."""

    def __init__(
        self,
        message: str = "",
        alert_type: AlertType = AlertType.INFO,
        variant: AlertVariant = AlertVariant.DEFAULT,
        dismissible: bool = False,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        props: Optional[AlertProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.message = message
        self.alert_type = alert_type
        self.variant = variant
        self.dismissible = dismissible
        self.title = title
        self.icon = icon

        # Add alert classes
        self.add_class("alert")
        self.add_class(f"alert-{alert_type.value}")
        self.add_class(f"alert-{variant.value}")

        if dismissible:
            self.add_class("alert-dismissible")

    def render(self) -> str:
        """Render alert."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content_parts = []

        # Alert icon
        if self.icon:
            content_parts.append(f'<span class="alert-icon">{self.icon}</span>')
        else:
            # Default icons based on type
            default_icons = {
                AlertType.INFO: "ℹ️",
                AlertType.SUCCESS: "✅",
                AlertType.WARNING: "⚠️",
                AlertType.ERROR: "❌",
            }
            icon = default_icons.get(self.alert_type, "")
            if icon:
                content_parts.append(f'<span class="alert-icon">{icon}</span>')

        # Alert content
        alert_body = []
        if self.title:
            alert_body.append(f'<div class="alert-title">{self.title}</div>')

        if self.message:
            alert_body.append(f'<div class="alert-message">{self.message}</div>')

        # Add child content
        children_content = self._render_children()
        if children_content:
            alert_body.append(children_content)

        if alert_body:
            content_parts.append(f'<div class="alert-body">{"".join(alert_body)}</div>')

        # Dismiss button
        if self.dismissible:
            content_parts.append(
                '<button class="alert-dismiss" onclick="this.parentElement.remove()">&times;</button>'
            )

        return f'<div {attrs}>{"".join(content_parts)}</div>'


class ModalSize(Enum):
    """Modal sizes."""

    SMALL = "sm"
    MEDIUM = "md"
    LARGE = "lg"
    EXTRA_LARGE = "xl"


@dataclass
class ModalProps(ComponentProps):
    """Properties for modal components."""

    size: ModalSize = ModalSize.MEDIUM
    closable: bool = True
    backdrop: bool = True
    keyboard_close: bool = True
    title: Optional[str] = None


class Modal(BaseComponent):
    """Modal dialog component."""

    def __init__(
        self,
        title: Optional[str] = None,
        size: ModalSize = ModalSize.MEDIUM,
        closable: bool = True,
        backdrop: bool = True,
        props: Optional[ModalProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.title = title
        self.size = size
        self.closable = closable
        self.backdrop = backdrop

        # Add modal classes
        self.add_class("modal")
        self.add_class(f"modal-{size.value}")

        if not self.props.visible:
            self.add_class("modal-hidden")

    def render(self) -> str:
        """Render modal."""
        attrs = self._render_attributes()

        # Modal backdrop
        backdrop_html = ""
        if self.backdrop:
            backdrop_html = '<div class="modal-backdrop" onclick="this.parentElement.classList.add(\'modal-hidden\')"></div>'

        # Modal dialog
        dialog_html = '<div class="modal-dialog">'

        # Modal content
        content_html = '<div class="modal-content">'

        # Modal header
        if self.title or self.closable:
            header_parts = []
            if self.title:
                header_parts.append(f'<h4 class="modal-title">{self.title}</h4>')
            if self.closable:
                header_parts.append(
                    "<button class=\"modal-close\" onclick=\"this.closest('.modal').classList.add('modal-hidden')\">&times;</button>"
                )
            content_html += f'<div class="modal-header">{"".join(header_parts)}</div>'

        # Modal body
        body_content = self._render_children()
        if body_content:
            content_html += f'<div class="modal-body">{body_content}</div>'

        content_html += "</div>"  # modal-content
        dialog_html += content_html + "</div>"  # modal-dialog

        # Modal script for keyboard handling
        script_html = ""
        if self.closable:
            script_html = """
            <script>
                document.addEventListener('keydown', function(e) {
                    if (e.key === 'Escape') {
                        document.querySelectorAll('.modal:not(.modal-hidden)').forEach(modal => {
                            modal.classList.add('modal-hidden');
                        });
                    }
                });
            </script>
            """

        return f"<div {attrs}>{backdrop_html}{dialog_html}{script_html}</div>"

    def show(self) -> "Modal":
        """Show the modal."""
        self.remove_class("modal-hidden")
        self.props.visible = True
        return self

    def hide(self) -> "Modal":
        """Hide the modal."""
        self.add_class("modal-hidden")
        self.props.visible = False
        return self


class ToastPosition(Enum):
    """Toast positions."""

    TOP_RIGHT = "top-right"
    TOP_LEFT = "top-left"
    BOTTOM_RIGHT = "bottom-right"
    BOTTOM_LEFT = "bottom-left"
    TOP_CENTER = "top-center"
    BOTTOM_CENTER = "bottom-center"


@dataclass
class ToastProps(ComponentProps):
    """Properties for toast components."""

    toast_type: AlertType = AlertType.INFO
    position: ToastPosition = ToastPosition.TOP_RIGHT
    duration: int = 5000
    closable: bool = True
    title: Optional[str] = None


class Toast(BaseComponent):
    """Toast notification component."""

    def __init__(
        self,
        message: str = "",
        toast_type: AlertType = AlertType.INFO,
        position: ToastPosition = ToastPosition.TOP_RIGHT,
        duration: int = 5000,
        closable: bool = True,
        title: Optional[str] = None,
        props: Optional[ToastProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.message = message
        self.toast_type = toast_type
        self.position = position
        self.duration = duration
        self.closable = closable
        self.title = title

        # Add toast classes
        self.add_class("toast")
        self.add_class(f"toast-{toast_type.value}")
        self.add_class(f"toast-{position.value}")

    def render(self) -> str:
        """Render toast."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content_parts = []

        # Toast icon
        default_icons = {
            AlertType.INFO: "ℹ️",
            AlertType.SUCCESS: "✅",
            AlertType.WARNING: "⚠️",
            AlertType.ERROR: "❌",
        }
        icon = default_icons.get(self.toast_type, "")
        if icon:
            content_parts.append(f'<span class="toast-icon">{icon}</span>')

        # Toast content
        toast_body = []
        if self.title:
            toast_body.append(f'<div class="toast-title">{self.title}</div>')

        if self.message:
            toast_body.append(f'<div class="toast-message">{self.message}</div>')

        children_content = self._render_children()
        if children_content:
            toast_body.append(children_content)

        if toast_body:
            content_parts.append(f'<div class="toast-body">{"".join(toast_body)}</div>')

        # Close button
        if self.closable:
            content_parts.append(
                '<button class="toast-close" onclick="this.parentElement.remove()">&times;</button>'
            )

        # Auto-hide script
        script_html = ""
        if self.duration > 0:
            toast_id = self.props.id or f"toast-{id(self)}"
            script_html = f"""
            <script>
                setTimeout(function() {{
                    const toast = document.getElementById('{toast_id}');
                    if (toast) {{
                        toast.classList.add('toast-hiding');
                        setTimeout(() => toast.remove(), 300);
                    }}
                }}, {self.duration});
            </script>
            """

        return f'<div {attrs}>{"".join(content_parts)}{script_html}</div>'


class ProgressBarStyle(Enum):
    """Progress bar styles."""

    DEFAULT = "default"
    STRIPED = "striped"
    ANIMATED = "animated"


@dataclass
class ProgressBarProps(ComponentProps):
    """Properties for progress bar components."""

    value: float = 0
    max_value: float = 100
    show_label: bool = False
    style: ProgressBarStyle = ProgressBarStyle.DEFAULT
    color: str = "primary"


class ProgressBar(BaseComponent):
    """Progress bar component."""

    def __init__(
        self,
        value: float = 0,
        max_value: float = 100,
        show_label: bool = False,
        style: ProgressBarStyle = ProgressBarStyle.DEFAULT,
        color: str = "primary",
        props: Optional[ProgressBarProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.value = max(0, min(value, max_value))
        self.max_value = max_value
        self.show_label = show_label
        self.style = style
        self.color = color

        # Add progress bar classes
        self.add_class("progress")
        self.add_class(f"progress-{color}")

        if style != ProgressBarStyle.DEFAULT:
            self.add_class(f"progress-{style.value}")

    def render(self) -> str:
        """Render progress bar."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        percentage = (self.value / self.max_value) * 100 if self.max_value > 0 else 0

        # Progress bar fill
        bar_attrs = f'class="progress-bar" style="width: {percentage}%"'
        bar_content = ""

        if self.show_label:
            bar_content = f"{percentage:.1f}%"

        return f"<div {attrs}><div {bar_attrs}>{bar_content}</div></div>"

    def set_value(self, value: float) -> "ProgressBar":
        """Set progress value."""
        self.value = max(0, min(value, self.max_value))
        return self


class LoadingSpinner(BaseComponent):
    """Loading spinner component."""

    def __init__(
        self,
        size: str = "medium",
        color: str = "primary",
        message: str = "Loading...",
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.size = size
        self.color = color
        self.message = message

        # Add spinner classes
        self.add_class("spinner")
        self.add_class(f"spinner-{size}")
        self.add_class(f"spinner-{color}")

    def render(self) -> str:
        """Render loading spinner."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()

        spinner_html = '<div class="spinner-element"></div>'
        if self.message:
            spinner_html += f'<div class="spinner-message">{self.message}</div>'

        return f"<div {attrs}>{spinner_html}</div>"


# Convenience functions
def alert(
    message: str,
    alert_type: Union[AlertType, str] = AlertType.INFO,
    dismissible: bool = False,
    **kwargs: Any,
) -> Alert:
    """Create an alert."""
    if isinstance(alert_type, str):
        alert_type = AlertType(alert_type)
    return Alert(message, alert_type, dismissible=dismissible, **kwargs)


def success_alert(message: str, **kwargs: Any) -> Alert:
    """Create a success alert."""
    return Alert(message, AlertType.SUCCESS, **kwargs)


def warning_alert(message: str, **kwargs: Any) -> Alert:
    """Create a warning alert."""
    return Alert(message, AlertType.WARNING, **kwargs)


def error_alert(message: str, **kwargs: Any) -> Alert:
    """Create an error alert."""
    return Alert(message, AlertType.ERROR, **kwargs)


def modal(
    title: Optional[str] = None, size: Union[ModalSize, str] = ModalSize.MEDIUM, **kwargs: Any
) -> Modal:
    """Create a modal."""
    if isinstance(size, str):
        size = ModalSize(size)
    return Modal(title, size, **kwargs)


def toast(
    message: str,
    toast_type: Union[AlertType, str] = AlertType.INFO,
    position: Union[ToastPosition, str] = ToastPosition.TOP_RIGHT,
    duration: int = 5000,
    **kwargs: Any,
) -> Toast:
    """Create a toast notification."""
    if isinstance(toast_type, str):
        toast_type = AlertType(toast_type)
    return Toast(message, toast_type, duration=duration, **kwargs)


def progress_bar(value: float, max_value: float = 100, **kwargs: Any) -> ProgressBar:
    """Create a progress bar."""
    return ProgressBar(value, max_value, **kwargs)


def loading_spinner(message: str = "Loading...", **kwargs: Any) -> LoadingSpinner:
    """Create a loading spinner."""
    return LoadingSpinner(message=message, **kwargs)
