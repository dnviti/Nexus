"""
Common Authentication and Authorization Utilities

This module provides shared authentication and authorization utilities
that can be used across all plugins to maintain consistent security practices.
"""

import jwt
import hashlib
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from functools import wraps
from fastapi import HTTPException, Request, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from .models import UserContext

logger = logging.getLogger(__name__)

# JWT Configuration
JWT_SECRET = "nexus-platform-secret-key-2024"  # In production, use environment variable
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

security = HTTPBearer(auto_error=False)


class AuthHelper:
    """Authentication helper class."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return AuthHelper.hash_password(password) == hashed_password

    @staticmethod
    def create_jwt_token(
        user_data: Dict[str, Any], expires_hours: int = JWT_EXPIRATION_HOURS
    ) -> str:
        """Create a JWT token for user authentication."""
        expiration = datetime.utcnow() + timedelta(hours=expires_hours)

        payload = {
            "user_id": user_data.get("id"),
            "username": user_data.get("username"),
            "email": user_data.get("email"),
            "roles": user_data.get("roles", []),
            "exp": expiration,
            "iat": datetime.utcnow(),
            "iss": "nexus-platform",
        }

        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def decode_jwt_token(token: str) -> Dict[str, Any]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    @staticmethod
    def extract_user_context(token_payload: Dict[str, Any]) -> UserContext:
        """Extract user context from token payload."""
        return UserContext(
            user_id=token_payload.get("user_id"),
            username=token_payload.get("username"),
            email=token_payload.get("email"),
            roles=token_payload.get("roles", []),
            permissions=token_payload.get("permissions", []),
            is_authenticated=True,
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> UserContext:
    """Get the current user from the JWT token."""
    if not credentials:
        return UserContext(is_authenticated=False)

    try:
        token_payload = AuthHelper.decode_jwt_token(credentials.credentials)
        return AuthHelper.extract_user_context(token_payload)
    except HTTPException:
        return UserContext(is_authenticated=False)


def require_auth(
    func=None, *, roles: Optional[List[str]] = None, permissions: Optional[List[str]] = None
):
    """Decorator to require authentication and optionally specific roles/permissions."""

    def decorator(f):
        @wraps(f)
        async def wrapper(*args, **kwargs):
            # Find user context in kwargs
            user_context = None
            for arg in args:
                if isinstance(arg, UserContext):
                    user_context = arg
                    break

            if not user_context:
                for value in kwargs.values():
                    if isinstance(value, UserContext):
                        user_context = value
                        break

            if not user_context or not user_context.is_authenticated:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            # Check roles if specified
            if roles:
                user_roles = set(user_context.roles)
                required_roles = set(roles)
                if not user_roles.intersection(required_roles):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required roles: {', '.join(roles)}",
                    )

            # Check permissions if specified
            if permissions:
                user_permissions = set(user_context.permissions)
                required_permissions = set(permissions)
                if not user_permissions.intersection(required_permissions):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Required permissions: {', '.join(permissions)}",
                    )

            return await f(*args, **kwargs)

        return wrapper

    if func is None:
        return decorator
    else:
        return decorator(func)


def require_roles(*roles: str):
    """Decorator to require specific roles."""
    return require_auth(roles=list(roles))


def require_permissions(*permissions: str):
    """Decorator to require specific permissions."""
    return require_auth(permissions=list(permissions))


class RoleManager:
    """Role and permission management utility."""

    DEFAULT_ROLES = {
        "admin": {
            "permissions": ["*"],  # All permissions
            "description": "System administrator with full access",
        },
        "user": {
            "permissions": ["read", "write_own"],
            "description": "Regular user with basic permissions",
        },
        "readonly": {"permissions": ["read"], "description": "Read-only access"},
        "manager": {
            "permissions": ["read", "write", "manage_users"],
            "description": "Manager with user management capabilities",
        },
    }

    @classmethod
    def has_permission(cls, user_context: UserContext, permission: str) -> bool:
        """Check if user has specific permission."""
        if not user_context.is_authenticated:
            return False

        # Admin role has all permissions
        if "admin" in user_context.roles:
            return True

        # Check explicit permissions
        if permission in user_context.permissions:
            return True

        # Check role-based permissions
        for role in user_context.roles:
            role_permissions = cls.DEFAULT_ROLES.get(role, {}).get("permissions", [])
            if "*" in role_permissions or permission in role_permissions:
                return True

        return False

    @classmethod
    def get_user_permissions(cls, user_context: UserContext) -> List[str]:
        """Get all permissions for a user."""
        if not user_context.is_authenticated:
            return []

        permissions = set(user_context.permissions)

        # Add role-based permissions
        for role in user_context.roles:
            role_permissions = cls.DEFAULT_ROLES.get(role, {}).get("permissions", [])
            permissions.update(role_permissions)

        return list(permissions)


def get_auth_headers(token: str) -> Dict[str, str]:
    """Get authorization headers for API requests."""
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


async def validate_api_key(api_key: str) -> bool:
    """Validate API key (placeholder implementation)."""
    # In a real implementation, this would check against a database
    # For now, just validate format
    return len(api_key) >= 32 and api_key.isalnum()


def create_session_id() -> str:
    """Create a unique session ID."""
    import uuid

    return str(uuid.uuid4())


class SecurityAudit:
    """Security auditing utilities."""

    @staticmethod
    def log_auth_attempt(username: str, success: bool, ip_address: str = "unknown"):
        """Log authentication attempt."""
        logger.info(
            f"Auth attempt - User: {username}, Success: {success}, IP: {ip_address}",
            extra={
                "event_type": "auth_attempt",
                "username": username,
                "success": success,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    def log_permission_check(user_id: str, permission: str, granted: bool):
        """Log permission check."""
        logger.info(
            f"Permission check - User: {user_id}, Permission: {permission}, Granted: {granted}",
            extra={
                "event_type": "permission_check",
                "user_id": user_id,
                "permission": permission,
                "granted": granted,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    @staticmethod
    def log_role_change(user_id: str, old_roles: List[str], new_roles: List[str], admin_id: str):
        """Log role change."""
        logger.warning(
            f"Role change - User: {user_id}, Old: {old_roles}, New: {new_roles}, Admin: {admin_id}",
            extra={
                "event_type": "role_change",
                "user_id": user_id,
                "old_roles": old_roles,
                "new_roles": new_roles,
                "admin_id": admin_id,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )
