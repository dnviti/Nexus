"""
User Management Plugin Services

This module contains business logic and service classes for the user management plugin.
"""

import logging
import json
import uuid
import hashlib
import secrets
from typing import Dict, Any, Optional, List, Set
from datetime import datetime, timedelta
import bcrypt

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

logger = logging.getLogger(__name__)


class UserService:
    """Core user management service"""

    def __init__(self, db: DatabaseAdapter, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    async def create_user(
        self, user_data: User, creator: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Create a new user"""
        user_id = str(uuid.uuid4())

        # Check if user already exists
        existing_user = await self.get_user_by_email(user_data.email)
        if existing_user:
            raise ValueError("User with this email already exists")

        existing_username = await self.get_user_by_username(user_data.username)
        if existing_username:
            raise ValueError("User with this username already exists")

        # Hash password if provided
        password_hash = None
        if user_data.password_hash:
            password_hash = bcrypt.hashpw(
                user_data.password_hash.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

        user_dict = user_data.dict(exclude={"password_hash"})
        user_dict.update(
            {
                "id": user_id,
                "password_hash": password_hash,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "created_by": creator.get("id") if creator else None,
            }
        )

        await self.db.insert("users", user_dict)

        # Create user profile
        profile = UserProfile(
            user_id=user_id,
            last_login=None,
            login_count=0,
        )
        await self.db.insert("user_profiles", profile.dict())

        # Log audit event
        await self._log_audit(
            action="user.created",
            actor_id=creator.get("id") if creator else None,
            actor_name=creator.get("username") if creator else "system",
            target_type="user",
            target_id=user_id,
            target_name=user_data.username,
            changes={"email": user_data.email, "username": user_data.username},
        )

        # Emit event
        await self.event_bus.emit(
            "user_management.user.created",
            {
                "user": user_dict,
                "creator": creator,
            },
        )

        logger.info(f"User {user_id} created with username {user_data.username}")
        return user_dict

    async def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID"""
        user = await self.db.get("users", user_id)
        if user:
            # Remove sensitive data
            user.pop("password_hash", None)
        return user

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Get user by email"""
        users = await self.db.query("SELECT * FROM users WHERE email = ?", [email])
        if users:
            user = users[0]
            user.pop("password_hash", None)
            return user
        return None

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username"""
        users = await self.db.query("SELECT * FROM users WHERE username = ?", [username.lower()])
        if users:
            user = users[0]
            user.pop("password_hash", None)
            return user
        return None

    async def update_user(
        self, user_id: str, update_data: Dict[str, Any], actor: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Update user information"""
        user = await self.db.get("users", user_id)
        if not user:
            raise ValueError("User not found")

        # Track changes for audit
        changes = {}
        for key, new_value in update_data.items():
            if key in user and user[key] != new_value:
                changes[key] = {"from": user[key], "to": new_value}

        # Update user
        update_data["updated_at"] = datetime.now().isoformat()
        await self.db.update("users", user_id, update_data)

        # Get updated user
        updated_user = await self.get_user(user_id)

        # Log audit event
        if changes:
            await self._log_audit(
                action="user.updated",
                actor_id=actor.get("id"),
                actor_name=actor.get("username"),
                target_type="user",
                target_id=user_id,
                target_name=user.get("username"),
                changes=changes,
            )

        # Emit event
        await self.event_bus.emit(
            "user_management.user.updated",
            {
                "user": updated_user,
                "changes": changes,
                "actor": actor,
            },
        )

        return updated_user

    async def delete_user(self, user_id: str, actor: Dict[str, Any]) -> bool:
        """Delete (deactivate) user"""
        user = await self.db.get("users", user_id)
        if not user:
            return False

        # Soft delete - deactivate user
        await self.db.update(
            "users",
            user_id,
            {
                "is_active": False,
                "deactivated_at": datetime.now().isoformat(),
                "deactivated_by": actor.get("id"),
            },
        )

        # Remove user sessions
        await self.db.execute("DELETE FROM user_sessions WHERE user_id = ?", [user_id])

        # Log audit event
        await self._log_audit(
            action="user.deleted",
            actor_id=actor.get("id"),
            actor_name=actor.get("username"),
            target_type="user",
            target_id=user_id,
            target_name=user.get("username"),
        )

        # Emit event
        await self.event_bus.emit(
            "user_management.user.deleted",
            {
                "user": user,
                "actor": actor,
            },
        )

        return True

    async def list_users(
        self, limit: int = 50, offset: int = 0, filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """List users with pagination and filtering"""
        query = "SELECT * FROM users WHERE 1=1"
        params = []

        if filters:
            if filters.get("is_active") is not None:
                query += " AND is_active = ?"
                params.append(filters["is_active"])

            if filters.get("department"):
                query += " AND department = ?"
                params.append(filters["department"])

            if filters.get("search"):
                query += " AND (username LIKE ? OR email LIKE ? OR first_name LIKE ? OR last_name LIKE ?)"
                search_term = f"%{filters['search']}%"
                params.extend([search_term, search_term, search_term, search_term])

        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        users = await self.db.query(query, params)

        # Remove sensitive data
        for user in users:
            user.pop("password_hash", None)

        return users

    async def verify_password(self, user_id: str, password: str) -> bool:
        """Verify user password"""
        user = await self.db.query("SELECT password_hash FROM users WHERE id = ?", [user_id])
        if not user or not user[0]["password_hash"]:
            return False

        return bcrypt.checkpw(password.encode("utf-8"), user[0]["password_hash"].encode("utf-8"))

    async def change_password(self, user_id: str, new_password: str, actor: Dict[str, Any]) -> bool:
        """Change user password"""
        password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        await self.db.update(
            "users",
            user_id,
            {
                "password_hash": password_hash,
                "password_changed_at": datetime.now().isoformat(),
                "must_change_password": False,
            },
        )

        # Update profile
        await self.db.update(
            "user_profiles",
            user_id,
            {
                "password_changed_at": datetime.now().isoformat(),
            },
        )

        # Log audit event
        await self._log_audit(
            action="user.password_changed",
            actor_id=actor.get("id"),
            actor_name=actor.get("username"),
            target_type="user",
            target_id=user_id,
        )

        return True


class RoleService:
    """Role management service"""

    def __init__(self, db: DatabaseAdapter, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    async def create_role(self, role_data: Role, creator: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new role"""
        role_id = str(uuid.uuid4())

        # Check if role already exists
        existing_role = await self.get_role_by_name(role_data.name)
        if existing_role:
            raise ValueError("Role with this name already exists")

        role_dict = role_data.dict()
        role_dict.update(
            {
                "id": role_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "created_by": creator.get("id"),
            }
        )

        await self.db.insert("roles", role_dict)

        # Log audit event
        await self._log_audit(
            action="role.created",
            actor_id=creator.get("id"),
            actor_name=creator.get("username"),
            target_type="role",
            target_id=role_id,
            target_name=role_data.name,
            changes={"permissions": role_data.permissions},
        )

        return role_dict

    async def get_role(self, role_id: str) -> Optional[Dict[str, Any]]:
        """Get role by ID"""
        return await self.db.get("roles", role_id)

    async def get_role_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """Get role by name"""
        roles = await self.db.query("SELECT * FROM roles WHERE name = ?", [name.lower()])
        return roles[0] if roles else None

    async def assign_role_to_user(
        self, user_id: str, role_id: str, actor: Dict[str, Any], scope: Optional[str] = None
    ) -> bool:
        """Assign role to user"""
        # Check if assignment already exists
        existing = await self.db.query(
            "SELECT * FROM user_roles WHERE user_id = ? AND role_id = ? AND scope = ?",
            [user_id, role_id, scope],
        )
        if existing:
            return False

        assignment = UserRole(
            user_id=user_id,
            role_id=role_id,
            assigned_by=actor.get("id"),
            assigned_at=datetime.now().isoformat(),
            scope=scope,
        )

        await self.db.insert("user_roles", assignment.dict())

        # Log audit event
        await self._log_audit(
            action="role.assigned",
            actor_id=actor.get("id"),
            actor_name=actor.get("username"),
            target_type="user",
            target_id=user_id,
            changes={"role_id": role_id, "scope": scope},
        )

        return True

    async def revoke_role_from_user(
        self, user_id: str, role_id: str, actor: Dict[str, Any], scope: Optional[str] = None
    ) -> bool:
        """Revoke role from user"""
        deleted = await self.db.delete(
            "user_roles",
            {
                "user_id": user_id,
                "role_id": role_id,
                "scope": scope,
            },
        )

        if deleted:
            # Log audit event
            await self._log_audit(
                action="role.revoked",
                actor_id=actor.get("id"),
                actor_name=actor.get("username"),
                target_type="user",
                target_id=user_id,
                changes={"role_id": role_id, "scope": scope},
            )

        return deleted

    async def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all roles for a user"""
        roles = await self.db.query(
            """
            SELECT r.*, ur.scope, ur.assigned_at, ur.expires_at
            FROM roles r
            JOIN user_roles ur ON r.id = ur.role_id
            WHERE ur.user_id = ? AND ur.is_active = 1
        """,
            [user_id],
        )
        return roles

    async def get_user_permissions(self, user_id: str) -> Set[str]:
        """Get all effective permissions for a user"""
        permissions = set()

        # Get permissions from roles
        roles = await self.get_user_roles(user_id)
        for role in roles:
            role_permissions = json.loads(role.get("permissions", "[]"))
            permissions.update(role_permissions)

        # Get direct permissions
        direct_perms = await self.db.query(
            """
            SELECT p.name, up.granted
            FROM permissions p
            JOIN user_permissions up ON p.id = up.permission_id
            WHERE up.user_id = ? AND up.granted = 1
        """,
            [user_id],
        )

        for perm in direct_perms:
            permissions.add(perm["name"])

        return permissions


class OrganizationService:
    """Organization management service"""

    def __init__(self, db: DatabaseAdapter, event_bus: EventBus):
        self.db = db
        self.event_bus = event_bus

    async def create_organization(
        self, org_data: Organization, creator: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create a new organization"""
        org_id = str(uuid.uuid4())

        org_dict = org_data.dict()
        org_dict.update(
            {
                "id": org_id,
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "created_by": creator.get("id"),
            }
        )

        await self.db.insert("organizations", org_dict)

        # Log audit event
        await self._log_audit(
            action="organization.created",
            actor_id=creator.get("id"),
            actor_name=creator.get("username"),
            target_type="organization",
            target_id=org_id,
            target_name=org_data.name,
        )

        return org_dict

    async def get_organization_hierarchy(self) -> List[Dict[str, Any]]:
        """Get organization hierarchy"""
        orgs = await self.db.query("SELECT * FROM organizations ORDER BY name")

        # Build hierarchy
        org_map = {org["id"]: org for org in orgs}
        hierarchy = []

        for org in orgs:
            if not org.get("parent_id"):
                org["children"] = self._build_org_children(org["id"], org_map)
                hierarchy.append(org)

        return hierarchy

    def _build_org_children(self, parent_id: str, org_map: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Recursively build organization children"""
        children = []
        for org in org_map.values():
            if org.get("parent_id") == parent_id:
                org["children"] = self._build_org_children(org["id"], org_map)
                children.append(org)
        return children


class AuditService:
    """Audit logging service"""

    def __init__(self, db: DatabaseAdapter):
        self.db = db

    async def log_audit(self, audit_data: AuditLog) -> str:
        """Log an audit event"""
        audit_id = str(uuid.uuid4())
        audit_dict = audit_data.dict()
        audit_dict["id"] = audit_id

        await self.db.insert("audit_logs", audit_dict)
        return audit_id

    async def get_audit_logs(
        self,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        actor_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get audit logs with filtering"""
        query = "SELECT * FROM audit_logs WHERE 1=1"
        params = []

        if target_type:
            query += " AND target_type = ?"
            params.append(target_type)

        if target_id:
            query += " AND target_id = ?"
            params.append(target_id)

        if actor_id:
            query += " AND actor_id = ?"
            params.append(actor_id)

        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        return await self.db.query(query, params)


class SessionService:
    """User session management service"""

    def __init__(self, db: DatabaseAdapter):
        self.db = db

    async def create_session(
        self, user_id: str, ip_address: str, user_agent: str
    ) -> Dict[str, Any]:
        """Create a new user session"""
        session_id = secrets.token_urlsafe(32)
        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

        session = UserSession(
            session_id=session_id,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            created_at=datetime.now().isoformat(),
            last_activity=datetime.now().isoformat(),
            expires_at=expires_at,
        )

        await self.db.insert("user_sessions", session.dict())
        return session.dict()

    async def validate_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Validate and update session"""
        sessions = await self.db.query(
            "SELECT * FROM user_sessions WHERE session_id = ? AND is_active = 1", [session_id]
        )

        if not sessions:
            return None

        session = sessions[0]

        # Check if expired
        if datetime.fromisoformat(session["expires_at"]) < datetime.now():
            await self.invalidate_session(session_id)
            return None

        # Update last activity
        await self.db.update(
            "user_sessions", session["id"], {"last_activity": datetime.now().isoformat()}
        )

        return session

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        return await self.db.update(
            "user_sessions",
            session_id,
            {
                "is_active": False,
                "ended_at": datetime.now().isoformat(),
            },
        )

    async def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        await self.db.execute(
            "DELETE FROM user_sessions WHERE expires_at < ?", [datetime.now().isoformat()]
        )


# Helper function for audit logging
async def _log_audit(
    db: DatabaseAdapter,
    action: str,
    actor_id: Optional[str] = None,
    actor_name: Optional[str] = None,
    target_type: str = "",
    target_id: str = "",
    target_name: Optional[str] = None,
    changes: Optional[Dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    result: str = "success",
    error_message: Optional[str] = None,
) -> str:
    """Helper function to log audit events"""
    audit_service = AuditService(db)

    audit_log = AuditLog(
        action=action,
        actor_id=actor_id,
        actor_name=actor_name,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        changes=changes or {},
        ip_address=ip_address,
        user_agent=user_agent,
        timestamp=datetime.now().isoformat(),
        result=result,
        error_message=error_message,
    )

    return await audit_service.log_audit(audit_log)
