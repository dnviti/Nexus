"""
Common Validation Utilities

This module provides shared validation functions that can be used
across all plugins to ensure consistent data validation and security.
"""

import re
import html
import logging
from typing import Any, Dict, List, Optional, Union
from email_validator import validate_email as _validate_email, EmailNotValidError
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Common regex patterns
USERNAME_PATTERN = re.compile(r"^[a-zA-Z0-9_.-]{3,30}$")
PHONE_PATTERN = re.compile(r"^\+?1?-?\.?\s?\(?(\d{3})\)?[\s.-]?(\d{3})[\s.-]?(\d{4})$")
PASSWORD_PATTERN = re.compile(
    r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
)
SLUG_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
HEX_COLOR_PATTERN = re.compile(r"^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$")
IP_ADDRESS_PATTERN = re.compile(
    r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$"
)

# Security blacklists
DANGEROUS_PATTERNS = [
    r"<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>",  # Script tags
    r"javascript:",  # JavaScript URLs
    r"vbscript:",  # VBScript URLs
    r"on\w+\s*=",  # Event handlers
    r"data:text\/html",  # Data URLs with HTML
    r"<iframe\b[^>]*>",  # Iframe tags
    r"<object\b[^>]*>",  # Object tags
    r"<embed\b[^>]*>",  # Embed tags
]

SQL_INJECTION_PATTERNS = [
    r"(\s*(\'|\")\s*(or|and)\s*(\d+|\'|\")\s*=\s*(\d+|\'|\"))",
    r"(\s*(\'|\")\s*(or|and)\s*(\'|\")\s*(\d+|\'|\")\s*=\s*(\d+|\'|\"))",
    r"(\s*union\s+(all\s+)?select)",
    r"(\s*drop\s+table)",
    r"(\s*insert\s+into)",
    r"(\s*delete\s+from)",
    r"(\s*update\s+\w+\s+set)",
]


class ValidationError(Exception):
    """Custom validation error."""

    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(message)


def validate_email(email: str, check_deliverability: bool = False) -> str:
    """
    Validate email address format.

    Args:
        email: Email address to validate
        check_deliverability: Whether to check if email domain exists

    Returns:
        Normalized email address

    Raises:
        ValidationError: If email is invalid
    """
    if not email or not isinstance(email, str):
        raise ValidationError("Email address is required", "email")

    try:
        # Use email-validator library for robust validation
        validation = _validate_email(email, check_deliverability=check_deliverability)
        return validation.email
    except EmailNotValidError as e:
        raise ValidationError(f"Invalid email address: {str(e)}", "email")


def validate_username(username: str, min_length: int = 3, max_length: int = 30) -> str:
    """
    Validate username format and length.

    Args:
        username: Username to validate
        min_length: Minimum username length
        max_length: Maximum username length

    Returns:
        Validated username

    Raises:
        ValidationError: If username is invalid
    """
    if not username or not isinstance(username, str):
        raise ValidationError("Username is required", "username")

    username = username.strip()

    if len(username) < min_length:
        raise ValidationError(f"Username must be at least {min_length} characters", "username")

    if len(username) > max_length:
        raise ValidationError(f"Username must be no more than {max_length} characters", "username")

    if not USERNAME_PATTERN.match(username):
        raise ValidationError(
            "Username can only contain letters, numbers, dots, hyphens, and underscores", "username"
        )

    # Check for reserved usernames
    reserved = ["admin", "root", "system", "api", "www", "mail", "support", "info"]
    if username.lower() in reserved:
        raise ValidationError(f"Username '{username}' is reserved", "username")

    return username


def validate_password(password: str, min_length: int = 8) -> str:
    """
    Validate password strength.

    Args:
        password: Password to validate
        min_length: Minimum password length

    Returns:
        Validated password

    Raises:
        ValidationError: If password is weak
    """
    if not password or not isinstance(password, str):
        raise ValidationError("Password is required", "password")

    if len(password) < min_length:
        raise ValidationError(f"Password must be at least {min_length} characters", "password")

    # Check password strength
    if not re.search(r"[a-z]", password):
        raise ValidationError("Password must contain at least one lowercase letter", "password")

    if not re.search(r"[A-Z]", password):
        raise ValidationError("Password must contain at least one uppercase letter", "password")

    if not re.search(r"\d", password):
        raise ValidationError("Password must contain at least one digit", "password")

    if not re.search(r"[@$!%*?&]", password):
        raise ValidationError(
            "Password must contain at least one special character (@$!%*?&)", "password"
        )

    # Check for common weak patterns
    if password.lower() in ["password", "123456", "qwerty", "admin"]:
        raise ValidationError("Password is too common", "password")

    return password


def validate_phone(phone: str) -> str:
    """
    Validate phone number format.

    Args:
        phone: Phone number to validate

    Returns:
        Normalized phone number

    Raises:
        ValidationError: If phone number is invalid
    """
    if not phone or not isinstance(phone, str):
        raise ValidationError("Phone number is required", "phone")

    # Remove all non-digit characters except +
    clean_phone = re.sub(r"[^\d+]", "", phone)

    if not PHONE_PATTERN.match(phone):
        raise ValidationError("Invalid phone number format", "phone")

    return clean_phone


def validate_url(url: str, allowed_schemes: Optional[List[str]] = None) -> str:
    """
    Validate URL format and scheme.

    Args:
        url: URL to validate
        allowed_schemes: List of allowed URL schemes (default: http, https)

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL is invalid
    """
    if not url or not isinstance(url, str):
        raise ValidationError("URL is required", "url")

    if allowed_schemes is None:
        allowed_schemes = ["http", "https"]

    try:
        parsed = urlparse(url)

        if not parsed.scheme:
            raise ValidationError("URL must include a scheme (http/https)", "url")

        if parsed.scheme not in allowed_schemes:
            raise ValidationError(f"URL scheme must be one of: {', '.join(allowed_schemes)}", "url")

        if not parsed.netloc:
            raise ValidationError("URL must include a domain", "url")

        return url

    except Exception as e:
        raise ValidationError(f"Invalid URL format: {str(e)}", "url")


def sanitize_input(
    value: str, max_length: Optional[int] = None, strip_html: bool = True, strip_sql: bool = True
) -> str:
    """
    Sanitize user input to prevent XSS and injection attacks.

    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length
        strip_html: Whether to remove HTML tags
        strip_sql: Whether to check for SQL injection patterns

    Returns:
        Sanitized input

    Raises:
        ValidationError: If input contains dangerous patterns
    """
    if not isinstance(value, str):
        return str(value)

    original_value = value

    # Check for dangerous patterns first
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(f"Dangerous pattern detected in input: {pattern}")
            raise ValidationError("Input contains potentially dangerous content", "input")

    # Check for SQL injection patterns
    if strip_sql:
        for pattern in SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.warning(f"SQL injection pattern detected: {pattern}")
                raise ValidationError("Input contains potentially dangerous SQL patterns", "input")

    # Strip HTML if requested
    if strip_html:
        value = html.escape(value)

    # Trim whitespace
    value = value.strip()

    # Check length
    if max_length and len(value) > max_length:
        raise ValidationError(f"Input exceeds maximum length of {max_length} characters", "input")

    return value


def validate_slug(slug: str) -> str:
    """
    Validate URL slug format.

    Args:
        slug: Slug to validate

    Returns:
        Validated slug

    Raises:
        ValidationError: If slug is invalid
    """
    if not slug or not isinstance(slug, str):
        raise ValidationError("Slug is required", "slug")

    slug = slug.strip().lower()

    if not SLUG_PATTERN.match(slug):
        raise ValidationError(
            "Slug can only contain lowercase letters, numbers, and hyphens", "slug"
        )

    if slug.startswith("-") or slug.endswith("-"):
        raise ValidationError("Slug cannot start or end with a hyphen", "slug")

    return slug


def validate_hex_color(color: str) -> str:
    """
    Validate hex color format.

    Args:
        color: Hex color to validate

    Returns:
        Validated hex color

    Raises:
        ValidationError: If color is invalid
    """
    if not color or not isinstance(color, str):
        raise ValidationError("Color is required", "color")

    color = color.strip()

    if not HEX_COLOR_PATTERN.match(color):
        raise ValidationError("Invalid hex color format (e.g., #FF0000 or #F00)", "color")

    return color.upper()


def validate_ip_address(ip: str) -> str:
    """
    Validate IP address format.

    Args:
        ip: IP address to validate

    Returns:
        Validated IP address

    Raises:
        ValidationError: If IP is invalid
    """
    if not ip or not isinstance(ip, str):
        raise ValidationError("IP address is required", "ip")

    if not IP_ADDRESS_PATTERN.match(ip):
        raise ValidationError("Invalid IP address format", "ip")

    return ip


def validate_json_data(data: Any, required_fields: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Validate JSON data structure.

    Args:
        data: Data to validate
        required_fields: List of required field names

    Returns:
        Validated data dictionary

    Raises:
        ValidationError: If data is invalid
    """
    if not isinstance(data, dict):
        raise ValidationError("Data must be a valid JSON object", "data")

    if required_fields:
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)

        if missing_fields:
            raise ValidationError(f"Missing required fields: {', '.join(missing_fields)}", "data")

    # Sanitize string values in the data
    sanitized_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            sanitized_data[key] = sanitize_input(value)
        else:
            sanitized_data[key] = value

    return sanitized_data


def validate_file_size(size_bytes: int, max_size_mb: int = 10) -> bool:
    """
    Validate file size.

    Args:
        size_bytes: File size in bytes
        max_size_mb: Maximum allowed size in MB

    Returns:
        True if valid

    Raises:
        ValidationError: If file is too large
    """
    max_size_bytes = max_size_mb * 1024 * 1024

    if size_bytes > max_size_bytes:
        raise ValidationError(
            f"File size exceeds maximum allowed size of {max_size_mb}MB", "file_size"
        )

    return True


def validate_file_type(filename: str, allowed_extensions: List[str]) -> str:
    """
    Validate file type by extension.

    Args:
        filename: Name of the file
        allowed_extensions: List of allowed file extensions

    Returns:
        File extension

    Raises:
        ValidationError: If file type is not allowed
    """
    if not filename or "." not in filename:
        raise ValidationError("Invalid filename", "filename")

    extension = filename.split(".")[-1].lower()

    if extension not in [ext.lower() for ext in allowed_extensions]:
        raise ValidationError(
            f"File type '.{extension}' not allowed. Allowed types: {', '.join(allowed_extensions)}",
            "file_type",
        )

    return extension


# Common validation presets
class ValidationPresets:
    """Common validation configurations."""

    STRICT_PASSWORD = {
        "min_length": 12,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special": True,
    }

    BASIC_PASSWORD = {
        "min_length": 8,
        "require_uppercase": True,
        "require_lowercase": True,
        "require_numbers": True,
        "require_special": False,
    }

    IMAGE_FILES = ["jpg", "jpeg", "png", "gif", "webp", "svg"]
    DOCUMENT_FILES = ["pdf", "doc", "docx", "txt", "rtf"]
    ARCHIVE_FILES = ["zip", "rar", "7z", "tar", "gz"]

    MAX_UPLOAD_SIZE_MB = {
        "image": 5,
        "document": 10,
        "archive": 50,
        "video": 100,
    }
