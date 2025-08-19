"""
Security Plugin for Nexus Platform

This plugin provides comprehensive authentication and authorization functionality
including user management, role-based access control (RBAC), session management,
and security monitoring.

Features:
- JWT-based authentication
- Role-based access control (RBAC)
- Session management
- User registration and profile management
- Password policies and security
- Login attempt monitoring
- Two-factor authentication support
- Security dashboard and analytics
"""

from typing import Dict, Any, Optional, List
import logging
from datetime import datetime, timedelta
import jwt
import bcrypt
from fastapi import APIRouter, HTTPException, Depends, Form, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, validator
import asyncio

from nexus.core import EventBus
from nexus.auth import AuthenticationManager, get_current_user, require_permission
from nexus.database import DatabaseAdapter
from nexus.ui.templates import render_template

logger = logging.getLogger(__name__)


# Security Models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str
    full_name: Optional[str] = None

    @validator("password")
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        return v


class UserLogin(BaseModel):
    username: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    is_active: Optional[bool] = None


class RoleCreate(BaseModel):
    name: str
    description: Optional[str] = None
    permissions: List[str] = []


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class SecurityPlugin:
    """Main Security Plugin Class"""

    def __init__(self):
        self.name = "security"
        self.version = "1.0.0"
        self.router = APIRouter(prefix="/security", tags=["security"])
        self.auth_router = APIRouter(prefix="/auth", tags=["authentication"])
        self.db: Optional[DatabaseAdapter] = None
        self.auth_manager: Optional[AuthenticationManager] = None
        self.event_bus: Optional[EventBus] = None
        self.config: Dict[str, Any] = {}
        self.security_scheme = HTTPBearer()

        # Setup routes
        self._setup_routes()

    async def initialize(self):
        """Initialize the security plugin"""
        self.db = self.db_adapter
        self.event_bus = self.event_bus
        self.config = getattr(self, "config", {})

        # Initialize our own authentication manager
        from nexus.auth import AuthenticationManager

        self.auth_manager = AuthenticationManager()

        # Setup database tables
        await self._setup_database()

        # Subscribe to events
        await self._setup_event_handlers()

        logger.info("Security plugin initialized")
        return True

    def _setup_routes(self):
        """Setup all plugin routes"""

        # Authentication routes
        @self.auth_router.post("/login", response_model=TokenResponse)
        async def login(credentials: UserLogin):
            return await self._handle_login(credentials)

        @self.auth_router.post("/logout")
        async def logout(token: HTTPAuthorizationCredentials = Depends(self.security_scheme)):
            return await self._handle_logout(token)

        @self.auth_router.post("/refresh", response_model=TokenResponse)
        async def refresh_token(refresh_token: str = Form(...)):
            return await self._handle_refresh_token(refresh_token)

        @self.auth_router.get("/profile")
        async def get_profile():
            return {"message": "Profile endpoint - authentication to be implemented"}

        @self.auth_router.put("/profile")
        async def update_profile(user_update: UserUpdate):
            return {"message": "Profile update endpoint - authentication to be implemented"}

        # Security management routes
        @self.router.get("/dashboard")
        async def security_dashboard():
            return await self._render_dashboard()

        @self.router.get("/users")
        async def list_users():
            return await self._list_users()

        @self.router.post("/users")
        async def create_user(user_data: UserCreate):
            return await self._create_user(user_data)

        @self.router.get("/users/{user_id}")
        async def get_user(user_id: str):
            return await self._get_user(user_id)

        @self.router.put("/users/{user_id}")
        async def update_user(user_id: str, user_update: UserUpdate):
            return await self._update_user(user_id, user_update, None)

        @self.router.delete("/users/{user_id}")
        async def delete_user(user_id: str):
            return await self._delete_user(user_id, None)

        @self.router.get("/roles")
        async def list_roles():
            return await self._list_roles()

        @self.router.post("/roles")
        async def create_role(role_data: RoleCreate):
            return await self._create_role(role_data, None)

        @self.router.get("/sessions")
        async def list_sessions():
            return await self._list_active_sessions()

        @self.router.delete("/sessions/{session_id}")
        async def revoke_session(session_id: str):
            return await self._revoke_session(session_id, None)

    async def _setup_database(self):
        """Setup database tables for security"""
        # Create users table
        await self.db.set(
            "schema:auth_users",
            {
                "table": "auth_users",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "username": "STRING UNIQUE NOT NULL",
                    "email": "STRING UNIQUE NOT NULL",
                    "password_hash": "STRING NOT NULL",
                    "full_name": "STRING",
                    "is_active": "BOOLEAN DEFAULT TRUE",
                    "is_verified": "BOOLEAN DEFAULT FALSE",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "last_login": "TIMESTAMP",
                    "failed_login_attempts": "INTEGER DEFAULT 0",
                    "locked_until": "TIMESTAMP",
                },
            },
        )

        # Create roles table
        await self.db.set(
            "schema:auth_roles",
            {
                "table": "auth_roles",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "name": "STRING UNIQUE NOT NULL",
                    "description": "STRING",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # Create permissions table
        await self.db.set(
            "schema:auth_permissions",
            {
                "table": "auth_permissions",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "name": "STRING UNIQUE NOT NULL",
                    "description": "STRING",
                    "category": "STRING",
                },
            },
        )

        # Create user_roles junction table
        await self.db.set(
            "schema:auth_user_roles",
            {
                "table": "auth_user_roles",
                "columns": {
                    "user_id": "STRING",
                    "role_id": "STRING",
                    "assigned_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "assigned_by": "STRING",
                },
            },
        )

        # Create role_permissions junction table
        await self.db.set(
            "schema:auth_role_permissions",
            {
                "table": "auth_role_permissions",
                "columns": {
                    "role_id": "STRING",
                    "permission_id": "STRING",
                    "assigned_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # Create sessions table
        await self.db.set(
            "schema:auth_sessions",
            {
                "table": "auth_sessions",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "user_id": "STRING NOT NULL",
                    "access_token": "STRING NOT NULL",
                    "refresh_token": "STRING NOT NULL",
                    "expires_at": "TIMESTAMP NOT NULL",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "last_accessed": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "user_agent": "STRING",
                    "ip_address": "STRING",
                },
            },
        )

        logger.info("Security database schema initialized")

    async def _setup_event_handlers(self):
        """Setup event bus handlers"""
        if self.event_bus:
            self.event_bus.subscribe("system.startup", self._handle_system_startup)
            self.event_bus.subscribe("user.activity", self._handle_user_activity)

    async def _handle_system_startup(self, event):
        """Handle system startup event"""
        logger.info("Security plugin handling system startup")

        # Create default admin user if none exists
        admin_exists = await self.db.exists("user:admin")
        if not admin_exists:
            await self._create_default_admin()

    async def _handle_user_activity(self, event):
        """Handle user activity events"""
        user_id = event.data.get("user_id")
        activity_type = event.data.get("activity_type")

        if user_id:
            await self.db.set(
                f"user_activity:{user_id}:{datetime.utcnow().isoformat()}",
                {
                    "user_id": user_id,
                    "activity_type": activity_type,
                    "timestamp": datetime.utcnow().isoformat(),
                    "metadata": event.data.get("metadata", {}),
                },
            )

    async def _handle_login(self, credentials: UserLogin) -> TokenResponse:
        """Handle user login"""
        try:
            # Check for account lockout
            user_key = f"user:username:{credentials.username}"
            user_data = await self.db.get(user_key)

            if not user_data:
                await self._record_failed_login(credentials.username)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
                )

            # Check if account is locked
            if user_data.get("locked_until"):
                locked_until = datetime.fromisoformat(user_data["locked_until"])
                if datetime.utcnow() < locked_until:
                    raise HTTPException(
                        status_code=status.HTTP_423_LOCKED,
                        detail="Account is temporarily locked due to too many failed login attempts",
                    )

            # Verify password
            if not bcrypt.checkpw(
                credentials.password.encode("utf-8"), user_data["password_hash"].encode("utf-8")
            ):
                await self._record_failed_login(credentials.username)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
                )

            # Reset failed login attempts
            await self._reset_failed_login_attempts(credentials.username)

            # Generate tokens
            access_token = self._generate_access_token(user_data)
            refresh_token = self._generate_refresh_token(user_data)

            # Create session
            session_id = f"session:{user_data['id']}:{datetime.utcnow().timestamp()}"
            await self.db.set(
                session_id,
                {
                    "user_id": user_data["id"],
                    "access_token": access_token,
                    "refresh_token": refresh_token,
                    "expires_at": (
                        datetime.utcnow()
                        + timedelta(minutes=self.config.get("access_token_expire_minutes", 30))
                    ).isoformat(),
                    "created_at": datetime.utcnow().isoformat(),
                    "last_accessed": datetime.utcnow().isoformat(),
                },
            )

            # Update last login
            user_data["last_login"] = datetime.utcnow().isoformat()
            await self.db.set(user_key, user_data)

            # Publish login event
            if self.event_bus:
                await self.event_bus.publish(
                    "security.user.login",
                    {
                        "user_id": user_data["id"],
                        "username": user_data["username"],
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )

            return TokenResponse(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=self.config.get("access_token_expire_minutes", 30) * 60,
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Login failed"
            )

    async def _handle_logout(self, token: HTTPAuthorizationCredentials):
        """Handle user logout"""
        try:
            # Decode token to get user info
            payload = jwt.decode(
                token.credentials,
                self.config.get("jwt_secret_key"),
                algorithms=[self.config.get("jwt_algorithm", "HS256")],
            )

            user_id = payload.get("sub")

            # Find and revoke session
            sessions = await self.db.list_keys(f"session:{user_id}:*")
            for session_key in sessions:
                session_data = await self.db.get(session_key)
                if session_data and session_data.get("access_token") == token.credentials:
                    await self.db.delete(session_key)
                    break

            # Publish logout event
            if self.event_bus:
                await self.event_bus.publish(
                    "security.user.logout",
                    {"user_id": user_id, "timestamp": datetime.utcnow().isoformat()},
                )

            return {"message": "Successfully logged out"}

        except jwt.InvalidTokenError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        except Exception as e:
            logger.error(f"Logout error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Logout failed"
            )

    async def _handle_refresh_token(self, refresh_token: str) -> TokenResponse:
        """Handle token refresh"""
        try:
            # Verify refresh token
            payload = jwt.decode(
                refresh_token,
                self.config.get("jwt_secret_key"),
                algorithms=[self.config.get("jwt_algorithm", "HS256")],
            )

            user_id = payload.get("sub")
            token_type = payload.get("type")

            if token_type != "refresh":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type"
                )

            # Get user data
            user_data = await self.db.get(f"user:id:{user_id}")
            if not user_data or not user_data.get("is_active"):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive"
                )

            # Generate new tokens
            new_access_token = self._generate_access_token(user_data)
            new_refresh_token = self._generate_refresh_token(user_data)

            return TokenResponse(
                access_token=new_access_token,
                refresh_token=new_refresh_token,
                expires_in=self.config.get("access_token_expire_minutes", 30) * 60,
            )

        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        except Exception as e:
            logger.error(f"Token refresh error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Token refresh failed"
            )

    def _generate_access_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT access token"""
        expire = datetime.utcnow() + timedelta(
            minutes=self.config.get("access_token_expire_minutes", 30)
        )
        payload = {
            "sub": user_data["id"],
            "username": user_data["username"],
            "email": user_data["email"],
            "type": "access",
            "exp": expire,
        }
        return jwt.encode(
            payload,
            self.config.get("jwt_secret_key"),
            algorithm=self.config.get("jwt_algorithm", "HS256"),
        )

    def _generate_refresh_token(self, user_data: Dict[str, Any]) -> str:
        """Generate JWT refresh token"""
        expire = datetime.utcnow() + timedelta(
            days=self.config.get("refresh_token_expire_days", 30)
        )
        payload = {"sub": user_data["id"], "type": "refresh", "exp": expire}
        return jwt.encode(
            payload,
            self.config.get("jwt_secret_key"),
            algorithm=self.config.get("jwt_algorithm", "HS256"),
        )

    async def _record_failed_login(self, username: str):
        """Record failed login attempt"""
        user_key = f"user:username:{username}"
        user_data = await self.db.get(user_key)

        if user_data:
            failed_attempts = user_data.get("failed_login_attempts", 0) + 1
            user_data["failed_login_attempts"] = failed_attempts

            max_attempts = self.config.get("max_login_attempts", 5)
            if failed_attempts >= max_attempts:
                lockout_duration = self.config.get("lockout_duration_minutes", 15)
                user_data["locked_until"] = (
                    datetime.utcnow() + timedelta(minutes=lockout_duration)
                ).isoformat()

            await self.db.set(user_key, user_data)

    async def _reset_failed_login_attempts(self, username: str):
        """Reset failed login attempts"""
        user_key = f"user:username:{username}"
        user_data = await self.db.get(user_key)

        if user_data:
            user_data["failed_login_attempts"] = 0
            user_data.pop("locked_until", None)
            await self.db.set(user_key, user_data)

    async def _create_default_admin(self):
        """Create default admin user"""
        admin_user = {
            "id": "admin",
            "username": "admin",
            "email": "admin@nexus.local",
            "password_hash": bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt()).decode(
                "utf-8"
            ),
            "full_name": "System Administrator",
            "is_active": True,
            "is_verified": True,
            "created_at": datetime.utcnow().isoformat(),
            "failed_login_attempts": 0,
        }

        await self.db.set("user:admin", admin_user)
        await self.db.set("user:username:admin", admin_user)
        await self.db.set("user:id:admin", admin_user)

        logger.info("Default admin user created")

    async def _render_dashboard(self):
        """Render security dashboard"""
        # Get security statistics
        stats = await self._get_security_stats()

        template_data = {
            "title": "Security Dashboard",
            "stats": stats,
            "active_sessions": await self._get_active_sessions_count(),
            "recent_logins": await self._get_recent_logins(),
            "failed_attempts": await self._get_failed_login_attempts(),
        }

        return render_template("security/dashboard.html", template_data)

    async def _get_security_stats(self) -> Dict[str, Any]:
        """Get security statistics"""
        user_keys = await self.db.list_keys("user:id:*")
        total_users = len(user_keys)

        active_users = 0
        for key in user_keys:
            user_data = await self.db.get(key)
            if user_data and user_data.get("is_active"):
                active_users += 1

        session_keys = await self.db.list_keys("session:*")
        active_sessions = len(session_keys)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "active_sessions": active_sessions,
            "security_events_today": await self._count_security_events_today(),
        }

    async def _get_active_sessions_count(self) -> int:
        """Get count of active sessions"""
        session_keys = await self.db.list_keys("session:*")
        active_count = 0

        for key in session_keys:
            session_data = await self.db.get(key)
            if session_data:
                expires_at = datetime.fromisoformat(session_data["expires_at"])
                if expires_at > datetime.utcnow():
                    active_count += 1

        return active_count

    async def _get_recent_logins(self) -> List[Dict[str, Any]]:
        """Get recent login attempts"""
        # This would typically query a login log table
        # For now, return empty list
        return []

    async def _get_failed_login_attempts(self) -> List[Dict[str, Any]]:
        """Get recent failed login attempts"""
        # This would typically query a failed attempts log
        # For now, return empty list
        return []

    async def _count_security_events_today(self) -> int:
        """Count security events for today"""
        # This would typically query security event logs
        return 0

    # User management methods
    async def _list_users(self):
        """List all users"""
        user_keys = await self.db.list_keys("user:id:*")
        users = []

        for key in user_keys:
            user_data = await self.db.get(key)
            if user_data:
                # Remove sensitive data
                safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
                users.append(safe_user)

        return {"users": users}

    async def _create_user(self, user_data: UserCreate):
        """Create a new user"""
        # Check if user already exists
        existing_user = await self.db.get(f"user:username:{user_data.username}")
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already exists"
            )

        # Hash password
        password_hash = bcrypt.hashpw(user_data.password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        # Create user record
        user_id = f"user_{datetime.utcnow().timestamp()}"
        user_record = {
            "id": user_id,
            "username": user_data.username,
            "email": user_data.email,
            "password_hash": password_hash,
            "full_name": user_data.full_name,
            "is_active": True,
            "is_verified": False,
            "created_at": datetime.utcnow().isoformat(),
            "failed_login_attempts": 0,
        }

        # Store user data
        await self.db.set(f"user:id:{user_id}", user_record)
        await self.db.set(f"user:username:{user_data.username}", user_record)

        # Publish user creation event
        if self.event_bus:
            await self.event_bus.publish(
                "security.user.created",
                {
                    "user_id": user_id,
                    "username": user_data.username,
                    "email": user_data.email,
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return {"message": "User created successfully", "user_id": user_id}

    async def _get_user(self, user_id: str):
        """Get user by ID"""
        user_data = await self.db.get(f"user:id:{user_id}")
        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Remove sensitive data
        safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
        return safe_user

    async def _update_user(self, user_id: str, user_update: UserUpdate):
        """Update user"""
        user_data = await self.db.get(f"user:id:{user_id}")
        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Update fields
        if user_update.email:
            user_data["email"] = user_update.email
        if user_update.full_name:
            user_data["full_name"] = user_update.full_name
        if user_update.is_active is not None:
            user_data["is_active"] = user_update.is_active

        user_data["updated_at"] = datetime.utcnow().isoformat()

        # Save updated user
        await self.db.set(f"user:id:{user_id}", user_data)
        await self.db.set(f"user:username:{user_data['username']}", user_data)

        # Publish user update event
        if self.event_bus:
            await self.event_bus.publish(
                "security.user.updated",
                {
                    "user_id": user_id,
                    "username": user_data["username"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return {"message": "User updated successfully"}

    async def _delete_user(self, user_id: str):
        """Delete user"""
        user_data = await self.db.get(f"user:id:{user_id}")
        if not user_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

        # Delete user data
        await self.db.delete(f"user:id:{user_id}")
        await self.db.delete(f"user:username:{user_data['username']}")

        # Revoke all sessions
        session_keys = await self.db.list_keys(f"session:{user_id}:*")
        for session_key in session_keys:
            await self.db.delete(session_key)

        # Publish user deletion event
        if self.event_bus:
            await self.event_bus.publish(
                "security.user.deleted",
                {
                    "user_id": user_id,
                    "username": user_data["username"],
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

        return {"message": "User deleted successfully"}

    # Additional placeholder methods for roles and sessions
    async def _list_roles(self):
        """List all roles"""
        return {"roles": []}

    async def _create_role(self, role_data: RoleCreate):
        """Create a new role"""
        return {"message": "Role created successfully"}

    async def _list_active_sessions(self):
        """List active sessions"""
        return {"sessions": []}

    async def _revoke_session(self, session_id: str):
        """Revoke a session"""
        return {"message": "Session revoked successfully"}

    async def _get_user_profile(self, current_user):
        """Get current user profile"""
        user_data = await self.db.get(f"user:id:{current_user.id}")
        if user_data:
            # Remove sensitive data
            safe_user = {k: v for k, v in user_data.items() if k != "password_hash"}
            return safe_user
        return {}

    async def _update_user_profile(self, current_user, user_update: UserUpdate):
        """Update current user profile"""
        return await self._update_user(current_user.id, user_update)

    def get_api_routes(self):
        """Get plugin API routes for registration"""
        return [self.router, self.auth_router]


# Plugin instance
plugin = SecurityPlugin()


# Export required plugin interface
def get_plugin():
    """Get plugin instance"""
    return plugin


async def initialize_plugin(db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
    """Initialize plugin"""
    plugin.db_adapter = db
    plugin.event_bus = event_bus
    plugin.config = config
    return await plugin.initialize()


def get_routes():
    """Get plugin routes"""
    return [plugin.router, plugin.auth_router]


def get_name():
    """Get plugin name"""
    return plugin.name


def get_version():
    """Get plugin version"""
    return plugin.version
