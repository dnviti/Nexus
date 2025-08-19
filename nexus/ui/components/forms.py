"""
Form Components for Nexus UI System
Provides form elements and validation for user input
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseComponent, ComponentProps, component


class InputType(Enum):
    """Input field types."""

    TEXT = "text"
    EMAIL = "email"
    PASSWORD = "password"
    NUMBER = "number"
    DATE = "date"
    TIME = "time"
    DATETIME = "datetime-local"
    URL = "url"
    TEL = "tel"
    SEARCH = "search"
    HIDDEN = "hidden"


class ValidationRule:
    """Base validation rule."""

    def __init__(self, message: str = "Invalid value"):
        self.message = message

    def validate(self, value: Any) -> bool:
        """Validate a value. Override in subclasses."""
        return True


class RequiredRule(ValidationRule):
    """Required field validation."""

    def __init__(self, message: str = "This field is required"):
        super().__init__(message)

    def validate(self, value: Any) -> bool:
        if value is None:
            return False
        if isinstance(value, str):
            return bool(value.strip())
        return bool(value)


class LengthRule(ValidationRule):
    """String length validation."""

    def __init__(
        self, min_length: int = 0, max_length: Optional[int] = None, message: Optional[str] = None
    ):
        self.min_length = min_length
        self.max_length = max_length
        if message is None:
            if max_length:
                message = f"Length must be between {min_length} and {max_length} characters"
            else:
                message = f"Length must be at least {min_length} characters"
        super().__init__(message)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        length = len(value)
        if length < self.min_length:
            return False
        if self.max_length and length > self.max_length:
            return False
        return True


class EmailRule(ValidationRule):
    """Email validation."""

    def __init__(self, message: str = "Please enter a valid email address"):
        super().__init__(message)

    def validate(self, value: Any) -> bool:
        if not isinstance(value, str):
            return False
        import re

        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, value))


class NumericRule(ValidationRule):
    """Numeric range validation."""

    def __init__(
        self,
        min_value: Optional[float] = None,
        max_value: Optional[float] = None,
        message: Optional[str] = None,
    ):
        self.min_value = min_value
        self.max_value = max_value
        if message is None:
            if min_value is not None and max_value is not None:
                message = f"Value must be between {min_value} and {max_value}"
            elif min_value is not None:
                message = f"Value must be at least {min_value}"
            elif max_value is not None:
                message = f"Value must be at most {max_value}"
            else:
                message = "Invalid numeric value"
        super().__init__(message)

    def validate(self, value: Any) -> bool:
        try:
            num_value = float(value)
            if self.min_value is not None and num_value < self.min_value:
                return False
            if self.max_value is not None and num_value > self.max_value:
                return False
            return True
        except (ValueError, TypeError):
            return False


@dataclass
class FormFieldProps(ComponentProps):
    """Properties for form fields."""

    name: str = ""
    value: Any = ""
    placeholder: str = ""
    required: bool = False
    readonly: bool = False
    validation_rules: List[ValidationRule] = field(default_factory=list)
    error_message: str = ""
    help_text: str = ""
    label: str = ""


class FormField(BaseComponent):
    """Base form field component."""

    def __init__(self, props: Optional[FormFieldProps] = None, **kwargs: Any) -> None:
        self.field_props = props or FormFieldProps()

        # Apply kwargs to field props
        for key, value in kwargs.items():
            if hasattr(self.field_props, key):
                setattr(self.field_props, key, value)

        super().__init__(props=self.field_props)

        # Add base form field classes
        self.add_class("form-field")
        if self.field_props.required:
            self.add_class("required")
        if self.field_props.error_message:
            self.add_class("has-error")

    def validate(self, value: Any = None) -> tuple[bool, str]:
        """Validate field value."""
        if value is None:
            value = self.field_props.value

        for rule in self.field_props.validation_rules:
            if not rule.validate(value):
                return False, rule.message

        return True, ""

    def set_error(self, message: str) -> "FormField":
        """Set error message and styling."""
        self.field_props.error_message = message
        self.add_class("has-error")
        return self

    def clear_error(self) -> "FormField":
        """Clear error message and styling."""
        self.field_props.error_message = ""
        self.remove_class("has-error")
        return self

    def render(self) -> str:
        """Render form field with label, input, and error."""
        field_html = self._render_field()

        wrapper_classes = ["form-group"]
        if self.field_props.error_message:
            wrapper_classes.append("has-error")

        html_parts = []

        # Label
        if self.field_props.label:
            label_classes = ["form-label"]
            if self.field_props.required:
                label_classes.append("required")

            label_html = f'<label class="{" ".join(label_classes)}" for="{self.field_props.name}">'
            label_html += self.field_props.label
            if self.field_props.required:
                label_html += ' <span class="required-indicator">*</span>'
            label_html += "</label>"
            html_parts.append(label_html)

        # Field input
        html_parts.append(field_html)

        # Help text
        if self.field_props.help_text:
            html_parts.append(f'<div class="form-help">{self.field_props.help_text}</div>')

        # Error message
        if self.field_props.error_message:
            html_parts.append(f'<div class="form-error">{self.field_props.error_message}</div>')

        return f'<div class="{" ".join(wrapper_classes)}">{"".join(html_parts)}</div>'

    def _render_field(self) -> str:
        """Render the actual input field. Override in subclasses."""
        return ""


class Input(FormField):
    """Text input component."""

    def __init__(
        self,
        input_type: Union[InputType, str] = InputType.TEXT,
        props: Optional[FormFieldProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(props, **kwargs)
        self.input_type = input_type if isinstance(input_type, InputType) else InputType(input_type)
        self.add_class("form-input")

    def _render_field(self) -> str:
        """Render input field."""
        attrs = []

        attrs.append(f'type="{self.input_type.value}"')
        attrs.append(f'name="{self.field_props.name}"')

        if self.field_props.id:
            attrs.append(f'id="{self.field_props.id}"')
        elif self.field_props.name:
            attrs.append(f'id="{self.field_props.name}"')

        if self.field_props.value:
            attrs.append(f'value="{self.field_props.value}"')

        if self.field_props.placeholder:
            attrs.append(f'placeholder="{self.field_props.placeholder}"')

        if self.field_props.required:
            attrs.append("required")

        if self.field_props.readonly:
            attrs.append("readonly")

        if self.field_props.disabled:
            attrs.append("disabled")

        # CSS classes
        classes = ["form-control"] + self.props.classes
        attrs.append(f'class="{" ".join(classes)}"')

        return f'<input {" ".join(attrs)}>'


class Textarea(FormField):
    """Textarea component."""

    def __init__(
        self,
        rows: int = 3,
        cols: Optional[int] = None,
        props: Optional[FormFieldProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(props, **kwargs)
        self.rows = rows
        self.cols = cols
        self.add_class("form-textarea")

    def _render_field(self) -> str:
        """Render textarea field."""
        attrs = []

        attrs.append(f'name="{self.field_props.name}"')
        attrs.append(f'rows="{self.rows}"')

        if self.cols:
            attrs.append(f'cols="{self.cols}"')

        if self.field_props.id:
            attrs.append(f'id="{self.field_props.id}"')
        elif self.field_props.name:
            attrs.append(f'id="{self.field_props.name}"')

        if self.field_props.placeholder:
            attrs.append(f'placeholder="{self.field_props.placeholder}"')

        if self.field_props.required:
            attrs.append("required")

        if self.field_props.readonly:
            attrs.append("readonly")

        if self.field_props.disabled:
            attrs.append("disabled")

        # CSS classes
        classes = ["form-control"] + self.props.classes
        attrs.append(f'class="{" ".join(classes)}"')

        value = self.field_props.value or ""

        return f'<textarea {" ".join(attrs)}>{value}</textarea>'


class Select(FormField):
    """Select dropdown component."""

    def __init__(
        self,
        options: Optional[List[Dict[str, Any]]] = None,
        multiple: bool = False,
        props: Optional[FormFieldProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(props, **kwargs)
        self.options = options or []
        self.multiple = multiple
        self.add_class("form-select")

    def add_option(
        self, value: str, label: str, selected: bool = False, disabled: bool = False, **attrs: Any
    ) -> "Select":
        """Add an option to the select."""
        self.options.append(
            {"value": value, "label": label, "selected": selected, "disabled": disabled, **attrs}
        )
        return self

    def _render_field(self) -> str:
        """Render select field."""
        attrs = []

        attrs.append(f'name="{self.field_props.name}"')

        if self.field_props.id:
            attrs.append(f'id="{self.field_props.id}"')
        elif self.field_props.name:
            attrs.append(f'id="{self.field_props.name}"')

        if self.multiple:
            attrs.append("multiple")

        if self.field_props.required:
            attrs.append("required")

        if self.field_props.disabled:
            attrs.append("disabled")

        # CSS classes
        classes = ["form-control"] + self.props.classes
        attrs.append(f'class="{" ".join(classes)}"')

        # Render options
        options_html = []
        for option in self.options:
            option_attrs = [f'value="{option["value"]}"']

            if option.get("selected") or option["value"] == self.field_props.value:
                option_attrs.append("selected")

            if option.get("disabled"):
                option_attrs.append("disabled")

            # Add any additional attributes
            for attr_name, attr_value in option.items():
                if attr_name not in ["value", "label", "selected", "disabled"]:
                    option_attrs.append(f'{attr_name}="{attr_value}"')

            options_html.append(f'<option {" ".join(option_attrs)}>{option["label"]}</option>')

        return f'<select {" ".join(attrs)}>{"".join(options_html)}</select>'


class Checkbox(FormField):
    """Checkbox component."""

    def __init__(
        self,
        checked: bool = False,
        value: str = "1",
        props: Optional[FormFieldProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(props, **kwargs)
        self.checked = checked
        self.checkbox_value = value
        self.add_class("form-checkbox")

    def _render_field(self) -> str:
        """Render checkbox field."""
        attrs = []

        attrs.append('type="checkbox"')
        attrs.append(f'name="{self.field_props.name}"')
        attrs.append(f'value="{self.checkbox_value}"')

        if self.field_props.id:
            attrs.append(f'id="{self.field_props.id}"')
        elif self.field_props.name:
            attrs.append(f'id="{self.field_props.name}"')

        if self.checked or self.field_props.value:
            attrs.append("checked")

        if self.field_props.required:
            attrs.append("required")

        if self.field_props.disabled:
            attrs.append("disabled")

        # CSS classes
        classes = ["form-check-input"] + self.props.classes
        attrs.append(f'class="{" ".join(classes)}"')

        checkbox_html = f'<input {" ".join(attrs)}>'

        # Wrap in checkbox container with label
        wrapper_html = '<div class="form-check">'
        wrapper_html += checkbox_html
        if self.field_props.label:
            label_for = self.field_props.id or self.field_props.name
            wrapper_html += f'<label class="form-check-label" for="{label_for}">'
            wrapper_html += self.field_props.label
            wrapper_html += "</label>"
        wrapper_html += "</div>"

        return wrapper_html


class Radio(FormField):
    """Radio button component."""

    def __init__(
        self,
        value: str = "",
        group_name: Optional[str] = None,
        checked: bool = False,
        props: Optional[FormFieldProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(props, **kwargs)
        self.radio_value = value
        self.group_name = group_name or self.field_props.name
        self.checked = checked
        self.add_class("form-radio")

    def _render_field(self) -> str:
        """Render radio field."""
        attrs = []

        attrs.append('type="radio"')
        attrs.append(f'name="{self.group_name}"')
        attrs.append(f'value="{self.radio_value}"')

        if self.field_props.id:
            attrs.append(f'id="{self.field_props.id}"')

        if self.checked or self.field_props.value == self.radio_value:
            attrs.append("checked")

        if self.field_props.required:
            attrs.append("required")

        if self.field_props.disabled:
            attrs.append("disabled")

        # CSS classes
        classes = ["form-check-input"] + self.props.classes
        attrs.append(f'class="{" ".join(classes)}"')

        radio_html = f'<input {" ".join(attrs)}>'

        # Wrap in radio container with label
        wrapper_html = '<div class="form-check">'
        wrapper_html += radio_html
        if self.field_props.label:
            label_for = self.field_props.id or f"{self.group_name}_{self.radio_value}"
            wrapper_html += f'<label class="form-check-label" for="{label_for}">'
            wrapper_html += self.field_props.label
            wrapper_html += "</label>"
        wrapper_html += "</div>"

        return wrapper_html


class Button(BaseComponent):
    """Button component."""

    def __init__(
        self,
        button_type: str = "button",
        variant: str = "primary",
        size: str = "medium",
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("button", props, **kwargs)
        self.button_type = button_type
        self.variant = variant
        self.size = size

        # Add button classes
        self.add_class("btn")
        self.add_class(f"btn-{variant}")
        if size != "medium":
            self.add_class(f"btn-{size}")

    def render(self) -> str:
        """Render button."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        attrs += f' type="{self.button_type}"'

        content = self._render_children()

        return f"<button {attrs}>{content}</button>"


class Form(BaseComponent):
    """Form container component."""

    def __init__(
        self,
        action: str = "",
        method: str = "post",
        enctype: Optional[str] = None,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("form", props, **kwargs)
        self.method = method
        self.action = action
        self.enctype = enctype
        self.fields: List[FormField] = []

        self.add_class("form")

    def add_field(self, field: FormField) -> "Form":
        """Add a field to the form."""
        self.fields.append(field)
        self.add_child(field)
        return self

    def get_field(self, name: str) -> Optional[FormField]:
        """Get a field by name."""
        for form_field in self.fields:
            if hasattr(form_field, "field_props") and form_field.field_props.name == name:
                return form_field
        return None

    def validate(self) -> tuple[bool, Dict[str, str]]:
        """Validate all form fields."""
        is_valid = True
        errors = {}

        for form_field in self.fields:
            if hasattr(form_field, "validate"):
                field_valid, error_msg = form_field.validate()
                if not field_valid:
                    is_valid = False
                    errors[form_field.field_props.name] = error_msg

        return is_valid, errors

    def get_data(self) -> Dict[str, Any]:
        """Get form data as dictionary."""
        data = {}
        for form_field in self.fields:
            if hasattr(form_field, "field_props"):
                data[form_field.field_props.name] = form_field.field_props.value
        return data

    def set_form_data(self, data: Dict[str, Any]) -> "Form":
        """Set form data from dictionary."""
        for form_field in self.fields:
            if hasattr(form_field, "field_props") and form_field.field_props.name in data:
                form_field.field_props.value = data[form_field.field_props.name]
        return self

    def render(self) -> str:
        """Render form."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        attrs += f' method="{self.method}"'

        if self.action:
            attrs += f' action="{self.action}"'

        if self.enctype:
            attrs += f' enctype="{self.enctype}"'

        content = self._render_children()

        return f"<form {attrs}>{content}</form>"


# Convenience functions for creating form components
def input_field(
    name: str, input_type: Union[InputType, str] = InputType.TEXT, label: str = "", **kwargs: Any
) -> Input:
    """Create an input field."""
    props = FormFieldProps(name=name, label=label)
    return Input(input_type, props, **kwargs)


def textarea_field(name: str, label: str = "", rows: int = 3, **kwargs: Any) -> Textarea:
    """Create a textarea field."""
    props = FormFieldProps(name=name, label=label)
    return Textarea(rows, props=props, **kwargs)


def select_field(
    name: str, options: List[Dict[str, Any]], label: str = "", **kwargs: Any
) -> Select:
    """Create a select field."""
    props = FormFieldProps(name=name, label=label)
    return Select(options, props=props, **kwargs)


def checkbox_field(name: str, label: str = "", checked: bool = False, **kwargs: Any) -> Checkbox:
    """Create a checkbox field."""
    props = FormFieldProps(name=name, label=label)
    return Checkbox(checked, props=props, **kwargs)


def submit_button(text: str = "Submit", **kwargs: Any) -> Button:
    """Create a submit button."""
    return Button("submit", content=text, **kwargs)


def form_builder() -> "FormBuilder":
    """Create a form builder for fluent form construction."""
    return FormBuilder()


class FormBuilder:
    """Fluent builder for forms."""

    def __init__(self) -> None:
        self.form = Form()

    def method(self, method: str) -> "FormBuilder":
        """Set form method."""
        self.form.method = method
        return self

    def action(self, action: str) -> "FormBuilder":
        """Set form action."""
        self.form.action = action
        return self

    def text(self, name: str, label: str = "", **kwargs: Any) -> "FormBuilder":
        """Add text input."""
        field = input_field(name, InputType.TEXT, label, **kwargs)
        self.form.add_field(field)
        return self

    def email(self, name: str, label: str = "", **kwargs: Any) -> "FormBuilder":
        """Add email input."""
        field = input_field(name, InputType.EMAIL, label, **kwargs)
        field.field_props.validation_rules.append(EmailRule())
        self.form.add_field(field)
        return self

    def password(self, name: str, label: str = "", **kwargs: Any) -> "FormBuilder":
        """Add password input."""
        field = input_field(name, InputType.PASSWORD, label, **kwargs)
        self.form.add_field(field)
        return self

    def textarea(self, name: str, label: str = "", rows: int = 3, **kwargs: Any) -> "FormBuilder":
        """Add textarea."""
        field = textarea_field(name, label, rows, **kwargs)
        self.form.add_field(field)
        return self

    def select(
        self, name: str, options: List[Dict[str, Any]], label: str = "", **kwargs: Any
    ) -> "FormBuilder":
        """Add select field."""
        field = select_field(name, options, label, **kwargs)
        self.form.add_field(field)
        return self

    def checkbox(self, name: str, label: str = "", **kwargs: Any) -> "FormBuilder":
        """Add checkbox."""
        field = checkbox_field(name, label, **kwargs)
        self.form.add_field(field)
        return self

    def submit(self, text: str = "Submit", **kwargs: Any) -> "FormBuilder":
        """Add submit button."""
        button = submit_button(text, **kwargs)
        self.form.add_child(button)
        return self

    def build(self) -> Form:
        """Build the form."""
        return self.form
