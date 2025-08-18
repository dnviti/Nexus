"""
User Management Plugin

A comprehensive user management system providing user registration, authentication,
profile management, and administrative functions with web API and UI.
"""

import hashlib
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Depends, status
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, EmailStr

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)

security = HTTPBearer()


# Data Models
class UserRole(BaseModel):
    """User role model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    permissions: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class User(BaseModel):
    """User model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    username: str
    email: EmailStr
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    is_verified: bool = False
    roles: List[str] = Field(default_factory=list)
    profile_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    password_hash: str = ""


class UserCreate(BaseModel):
    """User creation model."""

    username: str
    email: EmailStr
    password: str
    first_name: str = ""
    last_name: str = ""
    roles: List[str] = Field(default_factory=list)


class UserUpdate(BaseModel):
    """User update model."""

    email: Optional[EmailStr] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    is_active: Optional[bool] = None
    roles: Optional[List[str]] = None
    profile_data: Optional[Dict[str, Any]] = None


class UserLogin(BaseModel):
    """User login model."""

    username: str
    password: str


class UserSession(BaseModel):
    """User session model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    token: str
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    ip_address: str = ""
    user_agent: str = ""


class ActivityLog(BaseModel):
    """User activity log model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    action: str
    description: str
    ip_address: str = ""
    user_agent: str = ""
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class UserManagementPlugin(BasePlugin):
    """User Management Plugin with comprehensive user lifecycle management."""

    def __init__(self):
        super().__init__()
        self.name = "user_management"
        self.version = "1.0.0"
        self.category = "business"
        self.description = (
            "Comprehensive user management system with authentication and administration"
        )

        # In-memory storage for demo (replace with real database)
        self.users: List[User] = []
        self.roles: List[UserRole] = []
        self.sessions: List[UserSession] = []
        self.activity_logs: List[ActivityLog] = []

        # Initialize with sample data
        self._initialize_sample_data()

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin v{self.version}")

        # Create database schema
        await self._create_database_schema()

        # Initialize default roles
        await self._create_default_roles()

        # Start session cleanup task
        await self._start_session_cleanup()

        logger.info(f"{self.name} plugin initialized successfully")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")
        await self.publish_event(
            "user_management.shutdown",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix="/plugins/user_management", tags=["user_management"])

        # Authentication endpoints
        @router.post("/auth/register")
        async def register_user(user_data: UserCreate, request: Request):
            """Register a new user."""
            # Check if user already exists
            existing_user = self._find_user_by_username_or_email(
                user_data.username, user_data.email
            )
            if existing_user:
                raise HTTPException(
                    status_code=400, detail="User with this username or email already exists"
                )

            # Create new user
            password_hash = self._hash_password(user_data.password)
            user = User(
                username=user_data.username,
                email=user_data.email,
                first_name=user_data.first_name,
                last_name=user_data.last_name,
                password_hash=password_hash,
                roles=user_data.roles or ["user"],
            )

            self.users.append(user)

            # Log activity
            await self._log_activity(
                user.id, "user_registered", f"User {user.username} registered", request
            )

            # Publish event
            await self.publish_event(
                "user_management.user.registered",
                {
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "roles": user.roles,
                },
            )

            return {
                "message": "User registered successfully",
                "user_id": user.id,
                "username": user.username,
            }

        @router.post("/auth/login")
        async def login_user(login_data: UserLogin, request: Request):
            """Login user and create session."""
            user = self._find_user_by_username_or_email(login_data.username)
            if not user or not self._verify_password(login_data.password, user.password_hash):
                raise HTTPException(status_code=401, detail="Invalid username or password")

            if not user.is_active:
                raise HTTPException(status_code=403, detail="User account is disabled")

            # Create session
            token = self._generate_token()
            session = UserSession(
                user_id=user.id,
                token=token,
                expires_at=datetime.utcnow() + timedelta(days=7),
                ip_address=self._get_client_ip(request),
                user_agent=request.headers.get("user-agent", ""),
            )

            self.sessions.append(session)
            user.last_login = datetime.utcnow()

            # Log activity
            await self._log_activity(
                user.id, "user_login", f"User {user.username} logged in", request
            )

            # Publish event
            await self.publish_event(
                "user_management.user.login",
                {
                    "user_id": user.id,
                    "username": user.username,
                    "session_id": session.id,
                },
            )

            return {
                "message": "Login successful",
                "token": token,
                "expires_at": session.expires_at.isoformat(),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "roles": user.roles,
                },
            }

        @router.post("/auth/logout")
        async def logout_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Logout user and invalidate session."""
            session = self._find_session_by_token(credentials.credentials)
            if not session:
                raise HTTPException(status_code=401, detail="Invalid token")

            # Remove session
            self.sessions = [s for s in self.sessions if s.id != session.id]

            # Log activity
            user = self._find_user_by_id(session.user_id)
            if user:
                await self._log_activity(
                    user.id, "user_logout", f"User {user.username} logged out", None
                )

            return {"message": "Logout successful"}

        # User management endpoints
        @router.get("/users")
        async def get_users(
            skip: int = 0,
            limit: int = 100,
            search: Optional[str] = None,
            role: Optional[str] = None,
            credentials: HTTPAuthorizationCredentials = Depends(security),
        ):
            """Get users list with filtering."""
            current_user = await self._get_current_user(credentials.credentials)
            if not self._has_permission(current_user, "users.read"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            filtered_users = self.users

            # Apply filters
            if search:
                filtered_users = [
                    u
                    for u in filtered_users
                    if search.lower() in u.username.lower()
                    or search.lower() in u.email.lower()
                    or search.lower() in f"{u.first_name} {u.last_name}".lower()
                ]

            if role:
                filtered_users = [u for u in filtered_users if role in u.roles]

            total = len(filtered_users)
            users = filtered_users[skip : skip + limit]

            # Remove sensitive data
            safe_users = []
            for user in users:
                user_dict = user.dict()
                del user_dict["password_hash"]
                safe_users.append(user_dict)

            return {
                "users": safe_users,
                "total": total,
                "skip": skip,
                "limit": limit,
            }

        @router.get("/users/{user_id}")
        async def get_user(
            user_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Get user details."""
            current_user = await self._get_current_user(credentials.credentials)

            # Users can view their own profile, admins can view any
            if current_user.id != user_id and not self._has_permission(current_user, "users.read"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            user_dict = user.dict()
            del user_dict["password_hash"]
            return {"user": user_dict}

        @router.put("/users/{user_id}")
        async def update_user(
            user_id: str,
            update_data: UserUpdate,
            credentials: HTTPAuthorizationCredentials = Depends(security),
        ):
            """Update user."""
            current_user = await self._get_current_user(credentials.credentials)

            # Users can update their own profile, admins can update any
            if current_user.id != user_id and not self._has_permission(current_user, "users.write"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Update fields
            if update_data.email is not None:
                user.email = update_data.email
            if update_data.first_name is not None:
                user.first_name = update_data.first_name
            if update_data.last_name is not None:
                user.last_name = update_data.last_name
            if update_data.profile_data is not None:
                user.profile_data.update(update_data.profile_data)

            # Only admins can change these
            if self._has_permission(current_user, "users.admin"):
                if update_data.is_active is not None:
                    user.is_active = update_data.is_active
                if update_data.roles is not None:
                    user.roles = update_data.roles

            # Log activity
            await self._log_activity(
                current_user.id, "user_updated", f"User {user.username} updated", None
            )

            return {"message": "User updated successfully"}

        @router.delete("/users/{user_id}")
        async def delete_user(
            user_id: str, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Delete user."""
            current_user = await self._get_current_user(credentials.credentials)
            if not self._has_permission(current_user, "users.admin"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            user = self._find_user_by_id(user_id)
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            # Remove user and associated data
            self.users = [u for u in self.users if u.id != user_id]
            self.sessions = [s for s in self.sessions if s.user_id != user_id]

            # Log activity
            await self._log_activity(
                current_user.id, "user_deleted", f"User {user.username} deleted", None
            )

            return {"message": "User deleted successfully"}

        # Role management endpoints
        @router.get("/roles")
        async def get_roles(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Get all roles."""
            current_user = await self._get_current_user(credentials.credentials)
            if not self._has_permission(current_user, "roles.read"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            return {"roles": [role.dict() for role in self.roles]}

        @router.post("/roles")
        async def create_role(
            role_data: UserRole, credentials: HTTPAuthorizationCredentials = Depends(security)
        ):
            """Create a new role."""
            current_user = await self._get_current_user(credentials.credentials)
            if not self._has_permission(current_user, "roles.admin"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            # Check if role exists
            existing_role = next((r for r in self.roles if r.name == role_data.name), None)
            if existing_role:
                raise HTTPException(status_code=400, detail="Role already exists")

            self.roles.append(role_data)

            return {"message": "Role created successfully", "role_id": role_data.id}

        # Activity logs
        @router.get("/activity")
        async def get_activity_logs(
            user_id: Optional[str] = None,
            action: Optional[str] = None,
            limit: int = 100,
            credentials: HTTPAuthorizationCredentials = Depends(security),
        ):
            """Get activity logs."""
            current_user = await self._get_current_user(credentials.credentials)
            if not self._has_permission(current_user, "activity.read"):
                raise HTTPException(status_code=403, detail="Insufficient permissions")

            logs = self.activity_logs

            if user_id:
                logs = [log for log in logs if log.user_id == user_id]
            if action:
                logs = [log for log in logs if log.action == action]

            # Sort by timestamp (newest first)
            logs = sorted(logs, key=lambda x: x.timestamp, reverse=True)[:limit]

            return {"activity_logs": [log.dict() for log in logs]}

        # Web UI endpoint
        @router.get("/ui", response_class=HTMLResponse)
        async def user_management_ui():
            """Serve the user management UI."""
            return self._get_user_management_html()

        @router.get("/ui/dashboard-data")
        async def get_dashboard_data(credentials: HTTPAuthorizationCredentials = Depends(security)):
            """Get dashboard data for UI."""
            current_user = await self._get_current_user(credentials.credentials)

            total_users = len(self.users)
            active_users = len([u for u in self.users if u.is_active])
            total_roles = len(self.roles)
            active_sessions = len([s for s in self.sessions if s.expires_at > datetime.utcnow()])

            # Recent activity
            recent_logs = sorted(self.activity_logs, key=lambda x: x.timestamp, reverse=True)[:10]

            # User registrations by day (last 7 days)
            today = datetime.utcnow().date()
            registration_stats = {}
            for i in range(7):
                date = today - timedelta(days=i)
                count = len([u for u in self.users if u.created_at.date() == date])
                registration_stats[date.isoformat()] = count

            return {
                "stats": {
                    "total_users": total_users,
                    "active_users": active_users,
                    "total_roles": total_roles,
                    "active_sessions": active_sessions,
                },
                "recent_activity": [log.dict() for log in recent_logs],
                "registration_stats": registration_stats,
                "current_user": {
                    "id": current_user.id,
                    "username": current_user.username,
                    "roles": current_user.roles,
                },
            }

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_users": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "username", "unique": True},
                        {"field": "email", "unique": True},
                        {"field": "created_at"},
                        {"field": "roles"},
                    ]
                },
                f"{self.name}_roles": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "name", "unique": True},
                    ]
                },
                f"{self.name}_sessions": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "token", "unique": True},
                        {"field": "user_id"},
                        {"field": "expires_at"},
                    ]
                },
                f"{self.name}_activity_logs": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "user_id"},
                        {"field": "action"},
                        {"field": "timestamp"},
                    ]
                },
            }
        }

    # Helper methods
    def _initialize_sample_data(self):
        """Initialize with sample data."""
        # Create default roles
        self.roles = [
            UserRole(
                name="admin",
                description="Administrator with full access",
                permissions=[
                    "users.read",
                    "users.write",
                    "users.admin",
                    "roles.read",
                    "roles.admin",
                    "activity.read",
                ],
            ),
            UserRole(
                name="moderator",
                description="Moderator with limited admin access",
                permissions=["users.read", "users.write", "activity.read"],
            ),
            UserRole(
                name="user",
                description="Regular user",
                permissions=["profile.read", "profile.write"],
            ),
        ]

        # Create sample users
        admin_user = User(
            username="admin",
            email="admin@example.com",
            first_name="System",
            last_name="Administrator",
            password_hash=self._hash_password("admin123"),
            roles=["admin"],
            is_verified=True,
        )

        demo_user = User(
            username="demo",
            email="demo@example.com",
            first_name="Demo",
            last_name="User",
            password_hash=self._hash_password("demo123"),
            roles=["user"],
            is_verified=True,
        )

        self.users = [admin_user, demo_user]

    def _hash_password(self, password: str) -> str:
        """Hash password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verify password against hash."""
        return self._hash_password(password) == password_hash

    def _generate_token(self) -> str:
        """Generate session token."""
        import secrets

        return secrets.token_urlsafe(32)

    def _find_user_by_username_or_email(
        self, username: str, email: Optional[str] = None
    ) -> Optional[User]:
        """Find user by username or email."""
        for user in self.users:
            if user.username == username or (email and user.email == email):
                return user
        return None

    def _find_user_by_id(self, user_id: str) -> Optional[User]:
        """Find user by ID."""
        return next((u for u in self.users if u.id == user_id), None)

    def _find_session_by_token(self, token: str) -> Optional[UserSession]:
        """Find session by token."""
        session = next((s for s in self.sessions if s.token == token), None)
        if session and session.expires_at > datetime.utcnow():
            return session
        return None

    async def _get_current_user(self, token: str) -> User:
        """Get current user from token."""
        session = self._find_session_by_token(token)
        if not session:
            raise HTTPException(status_code=401, detail="Invalid or expired token")

        user = self._find_user_by_id(session.user_id)
        if not user:
            raise HTTPException(status_code=401, detail="User not found")

        return user

    def _has_permission(self, user: User, permission: str) -> bool:
        """Check if user has permission."""
        for role_name in user.roles:
            role = next((r for r in self.roles if r.name == role_name), None)
            if role and permission in role.permissions:
                return True
        return False

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"

    async def _log_activity(
        self, user_id: str, action: str, description: str, request: Optional[Request] = None
    ):
        """Log user activity."""
        log = ActivityLog(
            user_id=user_id,
            action=action,
            description=description,
            ip_address=self._get_client_ip(request) if request else "",
            user_agent=request.headers.get("user-agent", "") if request else "",
        )
        self.activity_logs.append(log)

    async def _create_database_schema(self):
        """Create database schema."""
        if self.db_adapter:
            schema = self.get_database_schema()
            logger.info(f"Database schema defined: {list(schema['collections'].keys())}")

    async def _create_default_roles(self):
        """Create default roles."""
        logger.info("Default roles created")

    async def _start_session_cleanup(self):
        """Start session cleanup task."""
        # Remove expired sessions
        now = datetime.utcnow()
        self.sessions = [s for s in self.sessions if s.expires_at > now]
        logger.info("Session cleanup started")

    def _get_user_management_html(self) -> str:
        """Generate the user management HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>User Management - Nexus Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }

        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #1e40af;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            text-align: center;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #1e40af;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: #64748b;
            font-size: 0.9rem;
        }

        .main-grid {
            display: grid;
            grid-template-columns: 1fr 300px;
            gap: 2rem;
        }

        .main-content {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }

        .sidebar {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            padding: 1.5rem;
        }

        .section-header {
            padding: 1.5rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: between;
            align-items: center;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #1e293b;
        }

        .section-content {
            padding: 1.5rem;
        }

        .user-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .user-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            transition: background-color 0.2s;
        }

        .user-item:hover {
            background-color: #f8fafc;
        }

        .user-avatar {
            width: 40px;
            height: 40px;
            border-radius: 50%;
            background: linear-gradient(45deg, #3b82f6, #1d4ed8);
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            margin-right: 1rem;
        }

        .user-info {
            flex: 1;
        }

        .user-name {
            font-weight: 600;
            color: #1e293b;
        }

        .user-email {
            color: #64748b;
            font-size: 0.9rem;
        }

        .user-roles {
            display: flex;
            gap: 0.25rem;
            margin-top: 0.25rem;
        }

        .role-badge {
            padding: 0.125rem 0.5rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .role-admin { background: #fee2e2; color: #dc2626; }
        .role-moderator { background: #fef3c7; color: #d97706; }
        .role-user { background: #dbeafe; color: #2563eb; }

        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .status-active { background: #dcfce7; color: #16a34a; }
        .status-inactive { background: #fee2e2; color: #dc2626; }

        .activity-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }

        .activity-item {
            padding: 0.75rem;
            border-bottom: 1px solid #f1f5f9;
            font-size: 0.9rem;
        }

        .activity-item:last-child {
            border-bottom: none;
        }

        .activity-action {
            font-weight: 600;
            color: #1e293b;
        }

        .activity-time {
            color: #64748b;
            font-size: 0.8rem;
        }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: background-color 0.2s;
        }

        .btn-primary {
            background: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background: #2563eb;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }

        @media (max-width: 768px) {
            .main-grid {
                grid-template-columns: 1fr;
            }

            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>👥 User Management</h1>
    </div>

    <div class="container">
        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-value" id="totalUsers">-</div>
                <div class="stat-label">Total Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="activeUsers">-</div>
                <div class="stat-label">Active Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="totalRoles">-</div>
                <div class="stat-label">Total Roles</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="activeSessions">-</div>
                <div class="stat-label">Active Sessions</div>
            </div>
        </div>

        <div class="main-grid">
            <div class="main-content">
                <div class="section-header">
                    <div class="section-title">Users</div>
                    <button class="btn btn-primary" onclick="refreshData()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div id="usersList" class="loading">Loading users...</div>
                </div>
            </div>

            <div class="sidebar">
                <h3 class="section-title" style="margin-bottom: 1rem;">Recent Activity</h3>
                <div id="recentActivity" class="loading">Loading activity...</div>
            </div>
        </div>
    </div>

    <script>
        let currentUser = null;

        async function loadDashboard() {
            try {
                // Get token from localStorage (in real app, handle authentication properly)
                const token = localStorage.getItem('auth_token');
                if (!token) {
                    showLoginRequired();
                    return;
                }

                const response = await fetch('/plugins/user_management/ui/dashboard-data', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to load dashboard data');
                }

                const data = await response.json();
                currentUser = data.current_user;

                // Update stats
                document.getElementById('totalUsers').textContent = data.stats.total_users;
                document.getElementById('activeUsers').textContent = data.stats.active_users;
                document.getElementById('totalRoles').textContent = data.stats.total_roles;
                document.getElementById('activeSessions').textContent = data.stats.active_sessions;

                // Load users list
                await loadUsers();

                // Load recent activity
                loadRecentActivity(data.recent_activity);

            } catch (error) {
                console.error('Error loading dashboard:', error);
                showError('Failed to load dashboard data');
            }
        }

        async function loadUsers() {
            try {
                const token = localStorage.getItem('auth_token');
                const response = await fetch('/plugins/user_management/users', {
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to load users');
                }

                const data = await response.json();
                displayUsers(data.users);

            } catch (error) {
                console.error('Error loading users:', error);
                document.getElementById('usersList').innerHTML = '<div class="loading">Error loading users</div>';
            }
        }

        function displayUsers(users) {
            const container = document.getElementById('usersList');

            if (!users || users.length === 0) {
                container.innerHTML = '<div class="loading">No users found</div>';
                return;
            }

            container.innerHTML = users.map(user => `
                <div class="user-item">
                    <div class="user-avatar">${getInitials(user.first_name, user.last_name, user.username)}</div>
                    <div class="user-info">
                        <div class="user-name">${user.first_name} ${user.last_name} (${user.username})</div>
                        <div class="user-email">${user.email}</div>
                        <div class="user-roles">
                            ${user.roles.map(role => `<span class="role-badge role-${role}">${role}</span>`).join('')}
                        </div>
                    </div>
                    <div>
                        <span class="status-badge ${user.is_active ? 'status-active' : 'status-inactive'}">
                            ${user.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            `).join('');
        }

        function loadRecentActivity(activities) {
            const container = document.getElementById('recentActivity');

            if (!activities || activities.length === 0) {
                container.innerHTML = '<div class="loading">No recent activity</div>';
                return;
            }

            container.innerHTML = activities.map(activity => `
                <div class="activity-item">
                    <div class="activity-action">${activity.action.replace('_', ' ').toUpperCase()}</div>
                    <div>${activity.description}</div>
                    <div class="activity-time">${formatTime(activity.timestamp)}</div>
                </div>
            `).join('');
        }

        function getInitials(firstName, lastName, username) {
            if (firstName && lastName) {
                return (firstName[0] + lastName[0]).toUpperCase();
            }
            return username.substring(0, 2).toUpperCase();
        }

        function formatTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);

            if (days > 0) return `${days}d ago`;
            if (hours > 0) return `${hours}h ago`;
            if (minutes > 0) return `${minutes}m ago`;
            return 'Just now';
        }

        function showLoginRequired() {
            document.querySelector('.container').innerHTML = `
                <div style="text-align: center; padding: 4rem;">
                    <h2>Authentication Required</h2>
                    <p>Please login to access the user management dashboard.</p>
                    <div style="margin-top: 2rem;">
                        <button class="btn btn-primary" onclick="showLoginForm()">Login</button>
                    </div>
                </div>
            `;
        }

        function showError(message) {
            document.querySelector('.container').innerHTML = `
                <div style="text-align: center; padding: 4rem; color: #dc2626;">
                    <h2>Error</h2>
                    <p>${message}</p>
                    <div style="margin-top: 2rem;">
                        <button class="btn btn-primary" onclick="location.reload()">Retry</button>
                    </div>
                </div>
            `;
        }

        function refreshData() {
            loadDashboard();
        }

        // Demo login function (in real app, implement proper authentication)
        function showLoginForm() {
            const loginHtml = `
                <div style="max-width: 400px; margin: 2rem auto; padding: 2rem; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                    <h2 style="text-align: center; margin-bottom: 2rem;">Login</h2>
                    <form onsubmit="handleLogin(event)" style="display: flex; flex-direction: column; gap: 1rem;">
                        <input type="text" id="loginUsername" placeholder="Username" required style="padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                        <input type="password" id="loginPassword" placeholder="Password" required style="padding: 0.75rem; border: 1px solid #e2e8f0; border-radius: 4px;">
                        <button type="submit" class="btn btn-primary" style="margin-top: 1rem;">Login</button>
                    </form>
                    <div style="margin-top: 1rem; text-align: center; font-size: 0.9rem; color: #64748b;">
                        Demo credentials: admin/admin123 or demo/demo123
                    </div>
                </div>
            `;

            document.querySelector('.container').innerHTML = loginHtml;
        }

        async function handleLogin(event) {
            event.preventDefault();
            const username = document.getElementById('loginUsername').value;
            const password = document.getElementById('loginPassword').value;

            try {
                const response = await fetch('/plugins/user_management/auth/login', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ username, password })
                });

                if (!response.ok) {
                    throw new Error('Login failed');
                }

                const data = await response.json();
                localStorage.setItem('auth_token', data.token);

                // Reload the page to show the dashboard
                location.reload();

            } catch (error) {
                alert('Login failed. Please check your credentials.');
            }
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', loadDashboard);
    </script>
</body>
</html>
        """
