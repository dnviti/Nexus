"""
Common Plugin Models

This module provides base models and response schemas that can be used
across all plugins to maintain consistency and reduce code duplication.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum


class PluginStatus(str, Enum):
    """Plugin status enumeration."""

    ACTIVE = "active"
    INACTIVE = "inactive"
    ERROR = "error"
    LOADING = "loading"
    DISABLED = "disabled"


class PluginCategory(str, Enum):
    """Plugin category enumeration."""

    CORE = "core"
    BUSINESS = "business"
    ANALYTICS = "analytics"
    INTEGRATION = "integration"
    SECURITY = "security"
    UI = "ui"
    CUSTOM = "custom"


class BasePluginModel(BaseModel):
    """Base model for all plugin data models."""

    id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}
        use_enum_values = True


class PluginInfo(BasePluginModel):
    """Plugin information model."""

    name: str
    version: str = "1.0.0"
    category: PluginCategory
    description: str = ""
    author: str = ""
    status: PluginStatus = PluginStatus.INACTIVE
    dependencies: List[str] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)


class PluginResponse(BaseModel):
    """Standard plugin response model."""

    success: bool = True
    message: str = ""
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def success_response(
        cls, message: str = "Operation successful", data: Optional[Dict[str, Any]] = None
    ) -> "PluginResponse":
        """Create a success response."""
        return cls(success=True, message=message, data=data or {})

    @classmethod
    def error_response(
        cls, message: str = "Operation failed", error: Optional[str] = None
    ) -> "PluginResponse":
        """Create an error response."""
        return cls(success=False, message=message, error=error)


class PluginError(BaseModel):
    """Plugin error model."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    plugin_name: Optional[str] = None


class EventPayload(BaseModel):
    """Base event payload model."""

    event_type: str
    source_plugin: str
    target_plugin: Optional[str] = None
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    correlation_id: Optional[str] = None


class PluginMetrics(BaseModel):
    """Plugin metrics model."""

    plugin_name: str
    requests_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    last_request: Optional[datetime] = None
    uptime_seconds: int = 0
    memory_usage: Optional[int] = None  # bytes
    cpu_usage: Optional[float] = None  # percentage


class HealthCheck(BaseModel):
    """Plugin health check model."""

    plugin_name: str
    status: PluginStatus
    message: str = "Healthy"
    checks: Dict[str, bool] = Field(default_factory=dict)
    last_check: datetime = Field(default_factory=datetime.utcnow)
    response_time_ms: Optional[float] = None


class PluginConfig(BaseModel):
    """Plugin configuration model."""

    enabled: bool = True
    auto_start: bool = True
    settings: Dict[str, Any] = Field(default_factory=dict)
    environment: str = "production"
    debug_mode: bool = False
    max_retries: int = 3
    timeout_seconds: int = 30


class UserContext(BaseModel):
    """User context model for plugin operations."""

    user_id: Optional[str] = None
    username: Optional[str] = None
    email: Optional[str] = None
    roles: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    session_id: Optional[str] = None
    is_authenticated: bool = False


class APIResponse(BaseModel):
    """Standard API response wrapper."""

    status_code: int = 200
    message: str = "Success"
    data: Optional[Union[Dict[str, Any], List[Any]]] = None
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic configuration."""

        json_encoders = {datetime: lambda v: v.isoformat()}


class PaginatedResponse(APIResponse):
    """Paginated response model."""

    page: int = 1
    per_page: int = 10
    total: int = 0
    total_pages: int = 0
    has_next: bool = False
    has_prev: bool = False

    @classmethod
    def create(
        cls, data: List[Any], page: int, per_page: int, total: int, message: str = "Success"
    ) -> "PaginatedResponse":
        """Create a paginated response."""
        total_pages = (total + per_page - 1) // per_page

        return cls(
            data=data,
            page=page,
            per_page=per_page,
            total=total,
            total_pages=total_pages,
            has_next=page < total_pages,
            has_prev=page > 1,
            message=message,
        )
