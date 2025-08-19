"""
User Management Plugin for Nexus Platform

This plugin provides comprehensive user management functionality including:
- User account management (create, read, update, delete)
- Role-based access control (RBAC)
- Permission management and assignment
- Organizational structure management
- User invitations and onboarding
- Session management and monitoring
- Audit logging and compliance
- User groups and team management
- Profile and preference management
- Import/export capabilities
- GDPR compliance features

Architecture:
- models.py: Data models and validation
- services.py: Business logic and services
- routes.py: API route handlers
- plugin.py: Main plugin class (legacy compatibility)
"""

import json
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime

from nexus.database import DatabaseAdapter
from nexus.core import EventBus

from .models import (
    User,
    Role,
    Permission,
    Organization,
    UserRole,
    UserPermission,
    UserProfile,
    UserSession,
    AuditLog,
    UserGroup,
    UserGroupMembership,
    UserInvitation,
    PasswordResetToken,
    UserActivity,
    UserPreferences,
    ComplianceRecord,
)
from .services import (
    UserService,
    RoleService,
    OrganizationService,
    AuditService,
    SessionService,
)
from .routes import UserManagementRoutes

logger = logging.getLogger(__name__)


class UserManagementPlugin:
    """Main User Management Plugin Class"""

    def __init__(self):
        self.name = "user_management"
        self.version = "1.0.0"
        self.db: Optional[DatabaseAdapter] = None
        self.event_bus: Optional[EventBus] = None
        self.config: Dict[str, Any] = {}

        # Service instances
        self.user_service: Optional[UserService] = None
        self.role_service: Optional[RoleService] = None
        self.org_service: Optional[OrganizationService] = None
        self.audit_service: Optional[AuditService] = None
        self.session_service: Optional[SessionService] = None

        # Routes handler
        self.routes: Optional[UserManagementRoutes] = None

    async def initialize(self, db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize the user management plugin"""
        self.db = db
        self.event_bus = event_bus
        self.config = config

        # Initialize services
        self.user_service = UserService(db, event_bus)
        self.role_service = RoleService(db, event_bus)
        self.org_service = OrganizationService(db, event_bus)
        self.audit_service = AuditService(db)
        self.session_service = SessionService(db)

        # Initialize routes
        self.routes = UserManagementRoutes(self)

        # Setup database tables
        await self._setup_database()

        # Setup event handlers
        await self._setup_event_handlers()

        # Create default system data
        await self._create_system_data()

        logger.info("User Management plugin initialized")

    async def _setup_database(self):
        """Setup database tables for user management functionality"""
        # Create tables if they don't exist
        tables = {
            "users": """
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    first_name TEXT NOT NULL,
                    last_name TEXT NOT NULL,
                    password_hash TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    is_verified BOOLEAN DEFAULT FALSE,
                    is_superuser BOOLEAN DEFAULT FALSE,
                    profile_image TEXT,
                    phone TEXT,
                    department TEXT,
                    job_title TEXT,
                    manager_id TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    created_by TEXT,
                    deactivated_at TEXT,
                    deactivated_by TEXT
                )
            """,
            "user_profiles": """
                CREATE TABLE IF NOT EXISTS user_profiles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT UNIQUE NOT NULL,
                    bio TEXT,
                    avatar TEXT,
                    timezone TEXT DEFAULT 'UTC',
                    language TEXT DEFAULT 'en',
                    theme TEXT DEFAULT 'light',
                    notifications_enabled BOOLEAN DEFAULT TRUE,
                    email_notifications BOOLEAN DEFAULT TRUE,
                    sms_notifications BOOLEAN DEFAULT FALSE,
                    two_factor_enabled BOOLEAN DEFAULT FALSE,
                    last_login TEXT,
                    login_count INTEGER DEFAULT 0,
                    failed_login_attempts INTEGER DEFAULT 0,
                    account_locked_until TEXT,
                    password_changed_at TEXT,
                    must_change_password BOOLEAN DEFAULT FALSE,
                    preferences TEXT DEFAULT '{}',
                    social_links TEXT DEFAULT '{}',
                    skills TEXT DEFAULT '[]',
                    certifications TEXT DEFAULT '[]'
                )
            """,
            "roles": """
                CREATE TABLE IF NOT EXISTS roles (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    permissions TEXT DEFAULT '[]',
                    is_system_role BOOLEAN DEFAULT FALSE,
                    color TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    created_by TEXT
                )
            """,
            "permissions": """
                CREATE TABLE IF NOT EXISTS permissions (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    description TEXT,
                    category TEXT DEFAULT 'general',
                    is_system_permission BOOLEAN DEFAULT FALSE,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    created_by TEXT
                )
            """,
            "user_roles": """
                CREATE TABLE IF NOT EXISTS user_roles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    role_id TEXT NOT NULL,
                    assigned_by TEXT,
                    assigned_at TEXT,
                    expires_at TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    scope TEXT,
                    metadata TEXT DEFAULT '{}',
                    UNIQUE(user_id, role_id, scope)
                )
            """,
            "user_permissions": """
                CREATE TABLE IF NOT EXISTS user_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    permission_id TEXT NOT NULL,
                    granted BOOLEAN DEFAULT TRUE,
                    assigned_by TEXT,
                    assigned_at TEXT,
                    expires_at TEXT,
                    scope TEXT,
                    reason TEXT,
                    metadata TEXT DEFAULT '{}',
                    UNIQUE(user_id, permission_id, scope)
                )
            """,
            "organizations": """
                CREATE TABLE IF NOT EXISTS organizations (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    parent_id TEXT,
                    org_type TEXT DEFAULT 'department',
                    manager_id TEXT,
                    budget REAL,
                    cost_center TEXT,
                    location TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    created_by TEXT
                )
            """,
            "user_groups": """
                CREATE TABLE IF NOT EXISTS user_groups (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    group_type TEXT DEFAULT 'custom',
                    owner_id TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    auto_join_rules TEXT DEFAULT '{}',
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT,
                    updated_at TEXT,
                    created_by TEXT
                )
            """,
            "user_group_memberships": """
                CREATE TABLE IF NOT EXISTS user_group_memberships (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    group_id TEXT NOT NULL,
                    role TEXT DEFAULT 'member',
                    joined_at TEXT,
                    added_by TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT DEFAULT '{}',
                    UNIQUE(user_id, group_id)
                )
            """,
            "user_sessions": """
                CREATE TABLE IF NOT EXISTS user_sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT UNIQUE NOT NULL,
                    user_id TEXT NOT NULL,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT,
                    last_activity TEXT,
                    expires_at TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    ended_at TEXT,
                    session_data TEXT DEFAULT '{}'
                )
            """,
            "user_invitations": """
                CREATE TABLE IF NOT EXISTS user_invitations (
                    id TEXT PRIMARY KEY,
                    email TEXT NOT NULL,
                    invited_by TEXT,
                    role_ids TEXT DEFAULT '[]',
                    organization_id TEXT,
                    invitation_code TEXT UNIQUE,
                    expires_at TEXT,
                    message TEXT,
                    is_accepted BOOLEAN DEFAULT FALSE,
                    accepted_at TEXT,
                    accepted_by TEXT,
                    metadata TEXT DEFAULT '{}',
                    created_at TEXT
                )
            """,
            "password_reset_tokens": """
                CREATE TABLE IF NOT EXISTS password_reset_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    token TEXT UNIQUE NOT NULL,
                    created_at TEXT,
                    expires_at TEXT,
                    is_used BOOLEAN DEFAULT FALSE,
                    used_at TEXT,
                    ip_address TEXT
                )
            """,
            "user_activities": """
                CREATE TABLE IF NOT EXISTS user_activities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    activity_type TEXT NOT NULL,
                    activity_description TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    timestamp TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """,
            "user_preferences": """
                CREATE TABLE IF NOT EXISTS user_preferences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    settings TEXT DEFAULT '{}',
                    updated_at TEXT,
                    UNIQUE(user_id, category)
                )
            """,
            "audit_logs": """
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id TEXT PRIMARY KEY,
                    action TEXT NOT NULL,
                    actor_id TEXT,
                    actor_name TEXT,
                    target_type TEXT,
                    target_id TEXT,
                    target_name TEXT,
                    changes TEXT DEFAULT '{}',
                    ip_address TEXT,
                    user_agent TEXT,
                    timestamp TEXT,
                    result TEXT DEFAULT 'success',
                    error_message TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """,
            "compliance_records": """
                CREATE TABLE IF NOT EXISTS compliance_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    regulation_type TEXT NOT NULL,
                    action TEXT NOT NULL,
                    details TEXT DEFAULT '{}',
                    timestamp TEXT,
                    compliance_officer TEXT,
                    retention_until TEXT,
                    metadata TEXT DEFAULT '{}'
                )
            """,
        }

        for table_name, create_sql in tables.items():
            await self.db.execute(create_sql)

        # Create indexes for better performance
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_roles_user_id ON user_roles(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_roles_role_id ON user_roles(role_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_permissions_user_id ON user_permissions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_user_id ON user_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_sessions_session_id ON user_sessions(session_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_target_type ON audit_logs(target_type)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_target_id ON audit_logs(target_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_actor_id ON audit_logs(actor_id)",
            "CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp ON audit_logs(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_user_activities_user_id ON user_activities(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_activities_timestamp ON user_activities(timestamp)",
        ]

        for index_sql in indexes:
            await self.db.execute(index_sql)

    async def _setup_event_handlers(self):
        """Setup event handlers"""
        self.event_bus.subscribe("security.user.login", self._handle_user_login)
        self.event_bus.subscribe("security.user.logout", self._handle_user_logout)
        self.event_bus.subscribe("security.authentication.failed", self._handle_auth_failed)

    async def _create_system_data(self):
        """Create default system roles and permissions"""
        # Check if system data already exists
        admin_role = await self.role_service.get_role_by_name("admin")
        if admin_role:
            return  # System data already created

        # Create system permissions
        system_permissions = [
            {"name": "users.create", "description": "Create users", "category": "users"},
            {"name": "users.read", "description": "View users", "category": "users"},
            {"name": "users.update", "description": "Update users", "category": "users"},
            {"name": "users.delete", "description": "Delete users", "category": "users"},
            {"name": "roles.create", "description": "Create roles", "category": "roles"},
            {"name": "roles.read", "description": "View roles", "category": "roles"},
            {"name": "roles.update", "description": "Update roles", "category": "roles"},
            {"name": "roles.delete", "description": "Delete roles", "category": "roles"},
            {
                "name": "permissions.manage",
                "description": "Manage permissions",
                "category": "permissions",
            },
            {
                "name": "organizations.manage",
                "description": "Manage organizations",
                "category": "organizations",
            },
            {"name": "audit.read", "description": "View audit logs", "category": "audit"},
            {"name": "system.admin", "description": "System administration", "category": "system"},
        ]

        for perm_data in system_permissions:
            permission = Permission(**perm_data, is_system_permission=True)
            await self.db.insert(
                "permissions",
                {
                    **permission.dict(),
                    "id": str(uuid.uuid4()),
                    "created_at": datetime.now().isoformat(),
                },
            )

        # Create system roles
        admin_role_data = Role(
            name="admin",
            description="System Administrator",
            permissions=[p["name"] for p in system_permissions],
            is_system_role=True,
        )

        user_role_data = Role(
            name="user",
            description="Regular User",
            permissions=["users.read"],
            is_system_role=True,
        )

        for role_data in [admin_role_data, user_role_data]:
            await self.db.insert(
                "roles",
                {
                    **role_data.dict(),
                    "id": str(uuid.uuid4()),
                    "created_at": datetime.now().isoformat(),
                    "permissions": json.dumps(role_data.permissions),
                },
            )

        logger.info("System roles and permissions created")

    # Event handlers
    async def _handle_user_login(self, event_data: Dict[str, Any]):
        """Handle user login event"""
        user = event_data.get("user")
        if user:
            # Update login statistics
            await self.db.execute(
                """
                UPDATE user_profiles
                SET last_login = ?, login_count = login_count + 1, failed_login_attempts = 0
                WHERE user_id = ?
                """,
                [datetime.now().isoformat(), user.get("id")],
            )

            # Log activity
            await self._log_user_activity(
                user.get("id"),
                "login",
                "User logged in",
                event_data.get("ip_address"),
                event_data.get("user_agent"),
            )

    async def _handle_user_logout(self, event_data: Dict[str, Any]):
        """Handle user logout event"""
        user = event_data.get("user")
        if user:
            # Log activity
            await self._log_user_activity(
                user.get("id"),
                "logout",
                "User logged out",
                event_data.get("ip_address"),
                event_data.get("user_agent"),
            )

    async def _handle_auth_failed(self, event_data: Dict[str, Any]):
        """Handle authentication failure event"""
        user_id = event_data.get("user_id")
        if user_id:
            # Increment failed login attempts
            await self.db.execute(
                "UPDATE user_profiles SET failed_login_attempts = failed_login_attempts + 1 WHERE user_id = ?",
                [user_id],
            )

            # Check if account should be locked
            profile = await self.db.query(
                "SELECT failed_login_attempts FROM user_profiles WHERE user_id = ?", [user_id]
            )
            if profile and profile[0]["failed_login_attempts"] >= 5:
                lock_until = (datetime.now() + timedelta(minutes=30)).isoformat()
                await self.db.execute(
                    "UPDATE user_profiles SET account_locked_until = ? WHERE user_id = ?",
                    [lock_until, user_id],
                )

    async def _log_user_activity(
        self,
        user_id: str,
        activity_type: str,
        description: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ):
        """Log user activity"""
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            activity_description=description,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now().isoformat(),
        )
        await self.db.insert("user_activities", activity.dict())

    def get_api_routes(self):
        """Get API routes for the plugin"""
        if self.routes:
            return [self.routes.router]
        return []

    async def cleanup(self):
        """Cleanup plugin resources"""
        if self.session_service:
            await self.session_service.cleanup_expired_sessions()


# Plugin instance
plugin = UserManagementPlugin()


# Plugin interface functions
def get_plugin():
    """Get plugin instance"""
    return plugin


async def initialize_plugin(db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
    """Initialize plugin"""
    await plugin.initialize(db, event_bus, config)


def get_routes():
    """Get plugin routes"""
    return plugin.get_api_routes()


def get_name():
    """Get plugin name"""
    return plugin.name


def get_version():
    """Get plugin version"""
    return plugin.version
