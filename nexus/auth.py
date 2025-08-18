"""
Nexus Framework Authentication Module
Basic authentication and authorization functionality.
"""

import logging
import secrets
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from fastapi import HTTPException, status
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class User(BaseModel):
    """User model."""

    id: str
    username: str
    email: str
    full_name: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    created_at: datetime
    last_login: Optional[datetime] = None
    permissions: List[str] = []
    roles: List[str] = []


class AuthenticationManager:
    """Basic authentication manager."""

    def __init__(self) -> None:
        """Initialize authentication manager."""
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, str] = {}  # token -> user_id

    async def create_user(
        self,
        username: str,
        email: str,
        password: str,
        full_name: Optional[str] = None,
        is_superuser: bool = False,
    ) -> User:
        """Create a new user."""
        user_id = f"user_{len(self.users) + 1}"
        user = User(
            id=user_id,
            username=username,
            email=email,
            full_name=full_name,
            is_superuser=is_superuser,
            created_at=datetime.utcnow(),
            permissions=["read"] if not is_superuser else ["read", "write", "admin"],
            roles=["user"] if not is_superuser else ["admin", "user"],
        )
        self.users[user_id] = user
        logger.info(f"Created user: {username}")
        return user

    async def authenticate(self, username: str, password: str) -> Optional[User]:
        """Authenticate user by username and password."""
        for user in self.users.values():
            if user.username == username:
                # In a real implementation, verify password hash
                return user
        return None

    async def get_user(self, user_id: str) -> Optional[User]:
        """Get user by ID."""
        return self.users.get(user_id)

    async def get_user_by_token(self, token: str) -> Optional[User]:
        """Get user by authentication token."""
        user_id = self.sessions.get(token)
        if user_id:
            return await self.get_user(user_id)
        return None

    async def create_session(self, user: User) -> str:
        """Create authentication session."""
        # Use timestamp + random component for uniqueness
        timestamp = datetime.utcnow().timestamp()
        random_part = secrets.token_hex(8)
        token = f"token_{user.id}_{timestamp}_{random_part}"
        self.sessions[token] = user.id
        user.last_login = datetime.utcnow()
        return token

    async def validate_permission(self, user: User, permission: str) -> bool:
        """Validate user permission."""
        return permission in user.permissions or "admin" in user.permissions

    async def validate_role(self, user: User, role: str) -> bool:
        """Validate user role."""
        return role in user.roles

    async def add_permission(self, user_id: str, permission: str) -> bool:
        """Add permission to user."""
        user = self.users.get(user_id)
        if not user:
            return False

        if permission not in user.permissions:
            user.permissions.append(permission)
            logger.info(f"Added permission '{permission}' to user {user.username}")
        return True

    async def remove_permission(self, user_id: str, permission: str) -> bool:
        """Remove permission from user."""
        user = self.users.get(user_id)
        if not user:
            return False

        if permission in user.permissions:
            user.permissions.remove(permission)
            logger.info(f"Removed permission '{permission}' from user {user.username}")
        return True

    async def add_role(self, user_id: str, role: str) -> bool:
        """Add role to user."""
        user = self.users.get(user_id)
        if not user:
            return False

        if role not in user.roles:
            user.roles.append(role)
            # Add default permissions for role
            role_permissions = self._get_role_permissions(role)
            for perm in role_permissions:
                if perm not in user.permissions:
                    user.permissions.append(perm)
            logger.info(f"Added role '{role}' to user {user.username}")
        return True

    async def remove_role(self, user_id: str, role: str) -> bool:
        """Remove role from user."""
        user = self.users.get(user_id)
        if not user:
            return False

        if role in user.roles:
            user.roles.remove(role)
            # Remove role-specific permissions
            role_permissions = self._get_role_permissions(role)
            for perm in role_permissions:
                if perm in user.permissions:
                    # Only remove if not granted by other roles
                    if not any(perm in self._get_role_permissions(r) for r in user.roles):
                        user.permissions.remove(perm)
            logger.info(f"Removed role '{role}' from user {user.username}")
        return True

    def _get_role_permissions(self, role: str) -> List[str]:
        """Get default permissions for a role."""
        role_permissions = {
            "admin": [
                "read",
                "write",
                "admin",
                "users:create",
                "users:delete",
                "plugins:manage",
                "system:admin",
            ],
            "moderator": ["read", "write", "users:moderate", "content:moderate"],
            "user": ["read", "profile:write"],
            "guest": ["read"],
        }
        return role_permissions.get(role, [])

    async def has_permission(self, user_id: str, permission: str) -> bool:
        """Check if user has specific permission."""
        user = self.users.get(user_id)
        if not user:
            return False
        return await self.validate_permission(user, permission)

    async def has_role(self, user_id: str, role: str) -> bool:
        """Check if user has specific role."""
        user = self.users.get(user_id)
        if not user:
            return False
        return await self.validate_role(user, role)

    async def get_user_permissions(self, user_id: str) -> List[str]:
        """Get all permissions for a user."""
        user = self.users.get(user_id)
        if not user:
            return []
        return user.permissions.copy()

    async def get_user_roles(self, user_id: str) -> List[str]:
        """Get all roles for a user."""
        user = self.users.get(user_id)
        if not user:
            return []
        return user.roles.copy()

    async def revoke_session(self, token: str) -> bool:
        """Revoke a user session."""
        if token in self.sessions:
            user_id = self.sessions[token]
            del self.sessions[token]
            logger.info(f"Revoked session for user {user_id}")
            return True
        return False

    async def revoke_all_sessions(self, user_id: str) -> int:
        """Revoke all sessions for a user."""
        revoked_count = 0
        tokens_to_remove = []

        for token, uid in self.sessions.items():
            if uid == user_id:
                tokens_to_remove.append(token)

        for token in tokens_to_remove:
            del self.sessions[token]
            revoked_count += 1

        logger.info(f"Revoked {revoked_count} sessions for user {user_id}")
        return revoked_count

    async def is_session_valid(self, token: str) -> bool:
        """Check if session token is valid."""
        return token in self.sessions

    async def get_active_sessions(self, user_id: str) -> List[str]:
        """Get all active sessions for a user."""
        return [token for token, uid in self.sessions.items() if uid == user_id]

    async def update_user_status(self, user_id: str, is_active: bool) -> bool:
        """Update user active status."""
        user = self.users.get(user_id)
        if not user:
            return False

        user.is_active = is_active
        logger.info(f"Updated user {user.username} active status to {is_active}")

        # If deactivating, revoke all sessions
        if not is_active:
            await self.revoke_all_sessions(user_id)

        return True

    async def list_users(self) -> List[User]:
        """List all users."""
        return list(self.users.values())

    async def delete_user(self, user_id: str) -> bool:
        """Delete a user by ID."""
        if user_id in self.users:
            del self.users[user_id]
            logger.info(f"Deleted user with ID: {user_id}")
            return True
        return False

    async def update_user(self, user_id: str, **updates: Any) -> Optional[User]:
        """Update user information."""
        user = self.users.get(user_id)
        if not user:
            return None

        for key, value in updates.items():
            if hasattr(user, key):
                setattr(user, key, value)

        logger.info(f"Updated user: {user.username}")
        return user


async def create_default_admin(auth_manager: AuthenticationManager) -> User:
    """Create default admin user."""
    # Generate a secure random password for the admin user
    import secrets
    import string

    # Generate a 16-character secure password
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    secure_password = "".join(secrets.choice(alphabet) for _ in range(16))

    admin_user = await auth_manager.create_user(
        username="admin",
        email="admin@nexus.local",
        password=secure_password,
        full_name="System Administrator",
        is_superuser=True,
    )

    # Log the generated password securely (in production, use proper secret management)
    logger.warning(f"Default admin user created with password: {secure_password}")
    logger.warning("SECURITY: Change the admin password immediately in production!")
    logger.info("Created default admin user")
    return admin_user


# Authentication dependency for FastAPI
async def get_current_user(token: Optional[str] = None) -> Optional[User]:
    """Get current authenticated user."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
        )

    # This would typically validate JWT token
    # For demo purposes, return a mock user
    return User(
        id="demo_user",
        username="demo",
        email="demo@nexus.local",
        full_name="Demo User",
        created_at=datetime.utcnow(),
        permissions=["read", "write"],
        roles=["user"],
    )


# FastAPI Dependencies and Decorators
from functools import wraps
from typing import Callable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

# Global auth manager instance
_auth_manager: Optional[AuthenticationManager] = None


def set_auth_manager(auth_manager: AuthenticationManager) -> None:
    """Set the global auth manager instance."""
    global _auth_manager
    _auth_manager = auth_manager


def get_auth_manager() -> AuthenticationManager:
    """Get the global auth manager instance."""
    if _auth_manager is None:
        raise RuntimeError("Auth manager not initialized")
    return _auth_manager


# Security scheme
security = HTTPBearer(auto_error=False)


async def get_current_user_dependency(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),  # noqa: B008
) -> Optional[User]:
    """Get current authenticated user from authorization credentials."""
    if not credentials:
        return None

    auth_manager = get_auth_manager()
    token = credentials.credentials

    if not await auth_manager.is_session_valid(token):
        return None

    return await auth_manager.get_user_by_token(token)


async def require_authentication(
    current_user: Optional[User] = Depends(get_current_user_dependency),  # noqa: B008
) -> User:
    """Require authentication for the endpoint."""
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="User account is disabled"
        )

    return current_user


def require_permission(permission: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator factory for requiring specific permissions."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current user from dependencies
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            auth_manager = get_auth_manager()
            if not await auth_manager.validate_permission(current_user, permission):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Permission '{permission}' required",
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def require_role(role: str) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Decorator factory for requiring specific roles."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Get current user from dependencies
            current_user = None
            for arg in args:
                if isinstance(arg, User):
                    current_user = arg
                    break

            if not current_user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            auth_manager = get_auth_manager()
            if not await auth_manager.validate_role(current_user, role):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' required"
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def create_permission_dependency(permission: str) -> Callable[..., Any]:
    """Create a FastAPI dependency that requires a specific permission."""

    async def permission_dependency(
        current_user: User = Depends(require_authentication),
    ) -> User:  # noqa: B008
        auth_manager = get_auth_manager()
        if not await auth_manager.validate_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Permission '{permission}' required"
            )
        return current_user

    return permission_dependency


def create_role_dependency(role: str) -> Callable[..., Any]:
    """Create a FastAPI dependency that requires a specific role."""

    async def role_dependency(
        current_user: User = Depends(require_authentication),
    ) -> User:  # noqa: B008
        auth_manager = get_auth_manager()
        if not await auth_manager.validate_role(current_user, role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, detail=f"Role '{role}' required"
            )
        return current_user

    return role_dependency


# Common permission dependencies
require_admin = create_permission_dependency("admin")
require_write = create_permission_dependency("write")
require_read = create_permission_dependency("read")

# Common role dependencies
require_admin_role = create_role_dependency("admin")
require_moderator_role = create_role_dependency("moderator")

__all__ = [
    "User",
    "AuthenticationManager",
    "create_default_admin",
    "get_current_user",
    "set_auth_manager",
    "get_auth_manager",
    "get_current_user_dependency",
    "require_authentication",
    "require_permission",
    "require_role",
    "create_permission_dependency",
    "create_role_dependency",
    "require_admin",
    "require_write",
    "require_read",
    "require_admin_role",
    "require_moderator_role",
]
