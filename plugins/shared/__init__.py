"""
Shared Plugin Components

This module provides common utilities, models, and components that can be
reused across different plugins to avoid code duplication.

Components:
- models: Common data models and schemas
- auth: Authentication and authorization utilities
- database: Database connection and ORM helpers
- events: Event publishing and subscription utilities
- validators: Common validation functions
- decorators: Useful decorators for plugins
"""

# Common imports that plugins might need
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

__all__ = [
    "BaseModel",
    "Field",
    "HTTPException",
    "status",
    "datetime",
    "Dict",
    "List",
    "Optional",
    "Any",
]
