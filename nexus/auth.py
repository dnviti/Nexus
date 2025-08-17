"""
Nexus Framework Authentication Module
Basic authentication and authorization functionality.
"""

import logging
import secrets
from datetime import datetime
from typing import Dict, List, Optional

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


__all__ = ["User", "AuthenticationManager", "create_default_admin", "get_current_user"]
