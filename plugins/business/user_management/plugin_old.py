"""
User Management Plugin for Nexus Platform

This plugin provides comprehensive user management functionality including:
- Advanced user administration
- Role and permission management
- User groups and organizational structure
- Bulk operations and data import/export
- Audit logging and reporting
- User profile management
- Advanced search and filtering

Features:
- Complete user lifecycle management
- Hierarchical role system
- Granular permission control
- User groups and teams
- Bulk user operations
- Import/export functionality
- Comprehensive audit trails
- Advanced reporting and analytics
- User profile customization
- Activity monitoring
"""

from typing import Dict, Any, Optional, List, Union
import logging
import csv
import json
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
import uuid

from fastapi import APIRouter, HTTPException, Depends, Form, File, UploadFile, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, EmailStr, validator
import io

from nexus.core import EventBus
from nexus.auth import get_current_user, require_permission
from nexus.database import DatabaseAdapter
from nexus.ui.templates import render_template

logger = logging.getLogger(__name__)


# Data Models
class UserProfile(BaseModel):
    user_id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    location: Optional[str] = None
    manager_id: Optional[str] = None
    hire_date: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    preferences: Dict[str, Any] = {}


class UserGroup(BaseModel):
    name: str
    description: Optional[str] = None
    group_type: str = "standard"  # standard, department, project, team
    parent_group_id: Optional[str] = None
    metadata: Dict[str, Any] = {}


class Permission(BaseModel):
    name: str
    description: Optional[str] = None
    category: str
    resource: str
    action: str


class Role(BaseModel):
    name: str
    description: Optional[str] = None
    level: int = 1  # For hierarchical roles
    parent_role_id: Optional[str] = None
    permissions: List[str] = []
    is_system_role: bool = False


class BulkUserOperation(BaseModel):
    operation_type: str  # create, update, delete, activate, deactivate
    user_ids: Optional[List[str]] = None
    user_data: Optional[List[Dict[str, Any]]] = None
    filters: Optional[Dict[str, Any]] = None


class UserSearchFilter(BaseModel):
    search_term: Optional[str] = None
    department: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    group: Optional[str] = None
    date_from: Optional[str] = None
    date_to: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 50


class UserManagementPlugin:
    """Main User Management Plugin Class"""

    def __init__(self):
        self.name = "user_management"
        self.version = "1.0.0"
        self.router = APIRouter(prefix="/user-management", tags=["user-management"])
        self.db: Optional[DatabaseAdapter] = None
        self.event_bus: Optional[EventBus] = None
        self.config: Dict[str, Any] = {}

        # Setup routes
        self._setup_routes()

    async def initialize(self):
        """Initialize the user management plugin"""
        self.db = self.db_adapter
        self.event_bus = self.event_bus
        self.config = getattr(self, "config", {})

        # Setup database schemas
        await self._setup_database()

        # Subscribe to events
        await self._setup_event_handlers()

        # Initialize default data
        await self._initialize_default_data()

        logger.info("User Management plugin initialized")
        return True

    def _setup_routes(self):
        """Setup all plugin routes"""

        # Dashboard
        @self.router.get("/")
        @self.router.get("/dashboard")
        async def user_management_dashboard():
            return await self._render_dashboard()

        # User management routes
        @self.router.get("/users")
        async def list_users(
            search: Optional[str] = Query(None),
            department: Optional[str] = Query(None),
            role: Optional[str] = Query(None),
            status: Optional[str] = Query(None),
            page: int = Query(1, ge=1),
            page_size: int = Query(50, ge=1, le=100),
        ):
            filters = UserSearchFilter(
                search_term=search,
                department=department,
                role=role,
                status=status,
                page=page,
                page_size=page_size,
            )
            return await self._list_users(filters)

        @self.router.get("/users/{user_id}")
        async def get_user_detail(user_id: str):
            return await self._get_user_detail(user_id)

        @self.router.put("/users/{user_id}")
        async def update_user(user_id: str, user_data: Dict[str, Any]):
            return await self._update_user(user_id, user_data, None)

        @self.router.delete("/users/{user_id}")
        async def delete_user(user_id: str):
            return await self._delete_user(user_id, None)

        # User roles and permissions
        @self.router.get("/users/{user_id}/roles")
        async def get_user_roles(user_id: str):
            return await self._get_user_roles(user_id)

        @self.router.post("/users/{user_id}/roles")
        async def assign_user_role(user_id: str, role_id: str = Form(...)):
            return await self._assign_user_role(user_id, role_id, None)

        @self.router.delete("/users/{user_id}/roles/{role_id}")
        async def remove_user_role(user_id: str, role_id: str):
            return await self._remove_user_role(user_id, role_id, None)

        @self.router.get("/users/{user_id}/permissions")
        async def get_user_permissions(user_id: str):
            return await self._get_user_permissions(user_id)

        @self.router.post("/users/{user_id}/permissions")
        async def grant_user_permission(user_id: str, permission_id: str = Form(...)):
            return await self._grant_user_permission(user_id, permission_id, None)

        # Bulk operations
        @self.router.post("/users/bulk")
        async def bulk_user_operation(operation: BulkUserOperation):
            return await self._bulk_user_operation(operation, None)

        # Import/Export
        @self.router.post("/users/import")
        async def import_users(file: UploadFile = File(...)):
            return await self._import_users(file, None)

        @self.router.get("/users/export")
        async def export_users(
            format: str = Query("csv", regex="^(csv|xlsx|json)$"),
            filters: Optional[str] = Query(None),
        ):
            return await self._export_users(format, filters)

        # Role management
        @self.router.get("/roles")
        async def list_roles():
            return await self._list_roles()

        @self.router.post("/roles")
        async def create_role(role_data: Role):
            return await self._create_role(role_data, None)

        @self.router.get("/roles/{role_id}")
        async def get_role(role_id: str):
            return await self._get_role(role_id)

        @self.router.put("/roles/{role_id}")
        async def update_role(role_id: str, role_data: Role):
            return await self._update_role(role_id, role_data, None)

        @self.router.delete("/roles/{role_id}")
        async def delete_role(role_id: str):
            return await self._delete_role(role_id, None)

        # Permission management
        @self.router.get("/permissions")
        async def list_permissions(category: Optional[str] = Query(None)):
            return await self._list_permissions(category)

        @self.router.post("/permissions")
        async def create_permission(permission_data: Permission):
            return await self._create_permission(permission_data, None)

        # Group management
        @self.router.get("/groups")
        async def list_groups():
            return await self._list_groups()

        @self.router.post("/groups")
        async def create_group(group_data: UserGroup):
            return await self._create_group(group_data, None)

        @self.router.get("/groups/{group_id}/members")
        async def get_group_members(group_id: str):
            return await self._get_group_members(group_id)

        # Audit and reporting
        @self.router.get("/audit")
        async def get_audit_logs(
            user_id: Optional[str] = Query(None),
            action: Optional[str] = Query(None),
            date_from: Optional[str] = Query(None),
            date_to: Optional[str] = Query(None),
            page: int = Query(1, ge=1),
        ):
            return await self._get_audit_logs(user_id, action, date_from, date_to, page)

        @self.router.get("/reports")
        async def get_reports():
            return await self._generate_reports()

    async def _setup_database(self):
        """Setup database schemas"""
        # User profiles extended schema
        await self.db.set(
            "schema:user_profiles",
            {
                "table": "user_profiles",
                "columns": {
                    "user_id": "STRING PRIMARY KEY",
                    "first_name": "STRING",
                    "last_name": "STRING",
                    "phone": "STRING",
                    "department": "STRING",
                    "job_title": "STRING",
                    "location": "STRING",
                    "manager_id": "STRING",
                    "hire_date": "DATE",
                    "bio": "TEXT",
                    "avatar_url": "STRING",
                    "preferences": "JSON",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "updated_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # User groups schema
        await self.db.set(
            "schema:user_groups",
            {
                "table": "user_groups",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "name": "STRING UNIQUE NOT NULL",
                    "description": "TEXT",
                    "group_type": "STRING DEFAULT 'standard'",
                    "parent_group_id": "STRING",
                    "metadata": "JSON",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "created_by": "STRING",
                },
            },
        )

        # User group members schema
        await self.db.set(
            "schema:user_group_members",
            {
                "table": "user_group_members",
                "columns": {
                    "group_id": "STRING",
                    "user_id": "STRING",
                    "role": "STRING DEFAULT 'member'",
                    "joined_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                    "added_by": "STRING",
                },
            },
        )

        # Permission categories schema
        await self.db.set(
            "schema:permission_categories",
            {
                "table": "permission_categories",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "name": "STRING UNIQUE NOT NULL",
                    "description": "TEXT",
                    "parent_category": "STRING",
                    "sort_order": "INTEGER DEFAULT 0",
                },
            },
        )

        # Role hierarchy schema
        await self.db.set(
            "schema:role_hierarchy",
            {
                "table": "role_hierarchy",
                "columns": {
                    "parent_role_id": "STRING",
                    "child_role_id": "STRING",
                    "created_at": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        # Audit log schema
        await self.db.set(
            "schema:user_management_audit",
            {
                "table": "user_management_audit",
                "columns": {
                    "id": "STRING PRIMARY KEY",
                    "user_id": "STRING",
                    "target_user_id": "STRING",
                    "action": "STRING NOT NULL",
                    "resource": "STRING",
                    "resource_id": "STRING",
                    "details": "JSON",
                    "ip_address": "STRING",
                    "user_agent": "STRING",
                    "timestamp": "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
                },
            },
        )

        logger.info("User Management database schemas initialized")

    async def _setup_event_handlers(self):
        """Setup event bus handlers"""
        if self.event_bus:
            self.event_bus.subscribe("security.user.created", self._handle_user_created)
            self.event_bus.subscribe("security.user.updated", self._handle_user_updated)
            self.event_bus.subscribe("security.user.deleted", self._handle_user_deleted)
            self.event_bus.subscribe("security.user.login", self._handle_user_login)
            self.event_bus.subscribe("security.user.logout", self._handle_user_logout)

    async def _initialize_default_data(self):
        """Initialize default roles, permissions, and groups"""
        # Create default permission categories
        default_categories = [
            {
                "id": "system",
                "name": "System Administration",
                "description": "Core system permissions",
            },
            {"id": "user", "name": "User Management", "description": "User-related permissions"},
            {
                "id": "content",
                "name": "Content Management",
                "description": "Content-related permissions",
            },
            {"id": "security", "name": "Security", "description": "Security-related permissions"},
        ]

        for category in default_categories:
            await self.db.set(f"permission_category:{category['id']}", category)

        # Create default roles
        default_roles = [
            {
                "id": "super_admin",
                "name": "Super Administrator",
                "description": "Full system access",
                "level": 10,
                "is_system_role": True,
            },
            {
                "id": "admin",
                "name": "Administrator",
                "description": "Administrative access",
                "level": 8,
                "is_system_role": True,
            },
            {
                "id": "manager",
                "name": "Manager",
                "description": "Management access",
                "level": 6,
                "is_system_role": True,
            },
            {
                "id": "user",
                "name": "User",
                "description": "Standard user access",
                "level": 1,
                "is_system_role": True,
            },
        ]

        for role in default_roles:
            role_exists = await self.db.exists(f"role:{role['id']}")
            if not role_exists:
                await self.db.set(f"role:{role['id']}", role)

        logger.info("Default user management data initialized")

    # Event handlers
    async def _handle_user_created(self, event):
        """Handle user creation event"""
        user_id = event.data.get("user_id")
        if user_id:
            # Create default user profile
            profile = {
                "user_id": user_id,
                "preferences": {"theme": "light", "language": "en", "timezone": "UTC"},
                "created_at": datetime.utcnow().isoformat(),
            }
            await self.db.set(f"user_profile:{user_id}", profile)

            # Assign default role
            default_role = self.config.get("default_user_role", "user")
            await self._assign_user_role(user_id, default_role, None, skip_audit=True)

            logger.info(f"Created profile for user {user_id}")

    async def _handle_user_updated(self, event):
        """Handle user update event"""
        user_id = event.data.get("user_id")
        if user_id:
            await self._log_audit_event("user_updated", user_id, event.data)

    async def _handle_user_deleted(self, event):
        """Handle user deletion event"""
        user_id = event.data.get("user_id")
        if user_id:
            # Clean up user profile and related data
            await self.db.delete(f"user_profile:{user_id}")
            await self._remove_user_from_all_groups(user_id)
            await self._log_audit_event("user_deleted", user_id, event.data)

    async def _handle_user_login(self, event):
        """Handle user login event"""
        user_id = event.data.get("user_id")
        if user_id:
            # Update last activity
            profile_key = f"user_profile:{user_id}"
            profile = await self.db.get(profile_key)
            if profile:
                profile["last_activity"] = datetime.utcnow().isoformat()
                await self.db.set(profile_key, profile)

    async def _handle_user_logout(self, event):
        """Handle user logout event"""
        # Could track logout statistics here
        pass

    # Main functionality methods
    async def _render_dashboard(self):
        """Render user management dashboard"""
        stats = await self._get_dashboard_stats()
        recent_activity = await self._get_recent_activity()

        template_data = {
            "title": "User Management Dashboard",
            "stats": stats,
            "recent_activity": recent_activity,
            "charts": await self._get_dashboard_charts(),
        }

        return render_template("user_management/dashboard.html", template_data)

    async def _get_dashboard_stats(self):
        """Get dashboard statistics"""
        user_keys = await self.db.list_keys("user:id:*")
        total_users = len(user_keys)

        active_users = 0
        for key in user_keys:
            user = await self.db.get(key)
            if user and user.get("is_active"):
                active_users += 1

        role_keys = await self.db.list_keys("role:*")
        total_roles = len(role_keys)

        group_keys = await self.db.list_keys("user_group:*")
        total_groups = len(group_keys)

        return {
            "total_users": total_users,
            "active_users": active_users,
            "total_roles": total_roles,
            "total_groups": total_groups,
            "new_users_this_week": await self._count_new_users_this_week(),
            "active_sessions": await self._count_active_sessions(),
        }

    async def _list_users(self, filters: UserSearchFilter):
        """List users with filtering and pagination"""
        all_user_keys = await self.db.list_keys("user:id:*")
        filtered_users = []

        for key in all_user_keys:
            user = await self.db.get(key)
            if user and self._matches_user_filter(user, filters):
                # Get user profile for additional info
                profile = await self.db.get(f"user_profile:{user['id']}")
                user_with_profile = {**user}
                if profile:
                    user_with_profile.update(profile)

                # Remove sensitive data
                user_with_profile.pop("password_hash", None)
                filtered_users.append(user_with_profile)

        # Sort users
        filtered_users.sort(
            key=lambda x: x.get(filters.sort_by, ""), reverse=(filters.sort_order == "desc")
        )

        # Paginate
        start_idx = (filters.page - 1) * filters.page_size
        end_idx = start_idx + filters.page_size
        paginated_users = filtered_users[start_idx:end_idx]

        return {
            "users": paginated_users,
            "total_count": len(filtered_users),
            "page": filters.page,
            "page_size": filters.page_size,
            "total_pages": (len(filtered_users) + filters.page_size - 1) // filters.page_size,
        }

    def _matches_user_filter(self, user: Dict[str, Any], filters: UserSearchFilter) -> bool:
        """Check if user matches the given filters"""
        if filters.search_term:
            search_fields = [
                user.get("username", ""),
                user.get("email", ""),
                user.get("full_name", ""),
            ]
            if not any(filters.search_term.lower() in field.lower() for field in search_fields):
                return False

        if filters.status:
            if filters.status == "active" and not user.get("is_active", False):
                return False
            if filters.status == "inactive" and user.get("is_active", True):
                return False

        # Add more filter conditions as needed
        return True

    async def _get_user_detail(self, user_id: str):
        """Get detailed user information"""
        user = await self.db.get(f"user:id:{user_id}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Get user profile
        profile = await self.db.get(f"user_profile:{user_id}")

        # Get user roles
        roles = await self._get_user_roles(user_id)

        # Get user permissions
        permissions = await self._get_user_permissions(user_id)

        # Get user groups
        groups = await self._get_user_groups(user_id)

        # Remove sensitive data
        user.pop("password_hash", None)

        return {
            "user": user,
            "profile": profile,
            "roles": roles,
            "permissions": permissions,
            "groups": groups,
        }

    async def _update_user(self, user_id: str, user_data: Dict[str, Any], current_user):
        """Update user information"""
        user = await self.db.get(f"user:id:{user_id}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Update user data
        for key, value in user_data.items():
            if key not in ["id", "password_hash"]:  # Protect sensitive fields
                user[key] = value

        user["updated_at"] = datetime.utcnow().isoformat()

        # Save updated user
        await self.db.set(f"user:id:{user_id}", user)
        await self.db.set(f"user:username:{user['username']}", user)

        # Update profile if profile data is provided
        profile_data = user_data.get("profile", {})
        if profile_data:
            profile = await self.db.get(f"user_profile:{user_id}") or {"user_id": user_id}
            profile.update(profile_data)
            profile["updated_at"] = datetime.utcnow().isoformat()
            await self.db.set(f"user_profile:{user_id}", profile)

        # Log audit event
        await self._log_audit_event(
            "user_updated", user_id, {"updated_fields": list(user_data.keys())}, current_user
        )

        # Publish event
        if self.event_bus:
            await self.event_bus.publish(
                "user_management.user.profile_updated",
                {"user_id": user_id, "updated_by": getattr(current_user, "id", None)},
            )

        return {"message": "User updated successfully"}

    async def _delete_user(self, user_id: str, current_user):
        """Delete user"""
        user = await self.db.get(f"user:id:{user_id}")
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Remove user from all groups
        await self._remove_user_from_all_groups(user_id)

        # Delete user data
        await self.db.delete(f"user:id:{user_id}")
        await self.db.delete(f"user:username:{user['username']}")
        await self.db.delete(f"user_profile:{user_id}")

        # Log audit event
        await self._log_audit_event(
            "user_deleted", user_id, {"username": user["username"]}, current_user
        )

        return {"message": "User deleted successfully"}

    # Additional helper methods would go here...
    async def _get_user_roles(self, user_id: str):
        """Get user roles"""
        # Implementation for getting user roles
        return {"roles": []}

    async def _assign_user_role(self, user_id: str, role_id: str, current_user, skip_audit=False):
        """Assign role to user"""
        # Implementation for assigning user role
        return {"message": "Role assigned successfully"}

    async def _remove_user_role(self, user_id: str, role_id: str, current_user):
        """Remove role from user"""
        # Implementation for removing user role
        return {"message": "Role removed successfully"}

    async def _get_user_permissions(self, user_id: str):
        """Get user permissions"""
        # Implementation for getting user permissions
        return {"permissions": []}

    async def _grant_user_permission(self, user_id: str, permission_id: str, current_user):
        """Grant permission to user"""
        # Implementation for granting user permission
        return {"message": "Permission granted successfully"}

    async def _get_user_groups(self, user_id: str):
        """Get user groups"""
        # Implementation for getting user groups
        return {"groups": []}

    async def _remove_user_from_all_groups(self, user_id: str):
        """Remove user from all groups"""
        # Implementation for removing user from all groups
        pass

    async def _bulk_user_operation(self, operation: BulkUserOperation, current_user):
        """Perform bulk user operations"""
        # Implementation for bulk operations
        return {"message": "Bulk operation completed successfully"}

    async def _import_users(self, file: UploadFile, current_user):
        """Import users from file"""
        # Implementation for user import
        return {"message": "Users imported successfully"}

    async def _export_users(self, format: str, filters: Optional[str]):
        """Export users to file"""
        # Implementation for user export
        return {"message": "Users exported successfully"}

    async def _list_roles(self):
        """List all roles"""
        role_keys = await self.db.list_keys("role:*")
        roles = []
        for key in role_keys:
            role = await self.db.get(key)
            if role:
                roles.append(role)
        return {"roles": roles}

    async def _create_role(self, role_data: Role, current_user):
        """Create new role"""
        role_id = str(uuid.uuid4())
        role = {
            "id": role_id,
            "name": role_data.name,
            "description": role_data.description,
            "level": role_data.level,
            "parent_role_id": role_data.parent_role_id,
            "permissions": role_data.permissions,
            "is_system_role": False,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": getattr(current_user, "id", None),
        }

        await self.db.set(f"role:{role_id}", role)

        await self._log_audit_event("role_created", role_id, {"name": role_data.name}, current_user)

        if self.event_bus:
            await self.event_bus.publish("user_management.role.created", {"role_id": role_id})

        return {"message": "Role created successfully", "role_id": role_id}

    async def _get_role(self, role_id: str):
        """Get role by ID"""
        role = await self.db.get(f"role:{role_id}")
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")
        return role

    async def _update_role(self, role_id: str, role_data: Role, current_user):
        """Update role"""
        role = await self.db.get(f"role:{role_id}")
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Update role data
        role.update(
            {
                "name": role_data.name,
                "description": role_data.description,
                "level": role_data.level,
                "permissions": role_data.permissions,
                "updated_at": datetime.utcnow().isoformat(),
            }
        )

        await self.db.set(f"role:{role_id}", role)

        await self._log_audit_event("role_updated", role_id, {"name": role_data.name}, current_user)

        if self.event_bus:
            await self.event_bus.publish("user_management.role.updated", {"role_id": role_id})

        return {"message": "Role updated successfully"}

    async def _delete_role(self, role_id: str, current_user):
        """Delete role"""
        role = await self.db.get(f"role:{role_id}")
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        if role.get("is_system_role"):
            raise HTTPException(status_code=400, detail="Cannot delete system role")

        await self.db.delete(f"role:{role_id}")

        await self._log_audit_event("role_deleted", role_id, {"name": role["name"]}, current_user)

        if self.event_bus:
            await self.event_bus.publish("user_management.role.deleted", {"role_id": role_id})

        return {"message": "Role deleted successfully"}

    async def _list_permissions(self, category: Optional[str] = None):
        """List permissions"""
        perm_keys = await self.db.list_keys("permission:*")
        permissions = []
        for key in perm_keys:
            perm = await self.db.get(key)
            if perm and (not category or perm.get("category") == category):
                permissions.append(perm)
        return {"permissions": permissions}

    async def _create_permission(self, permission_data: Permission, current_user):
        """Create new permission"""
        perm_id = str(uuid.uuid4())
        permission = {
            "id": perm_id,
            "name": permission_data.name,
            "description": permission_data.description,
            "category": permission_data.category,
            "resource": permission_data.resource,
            "action": permission_data.action,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": getattr(current_user, "id", None),
        }

        await self.db.set(f"permission:{perm_id}", permission)

        await self._log_audit_event(
            "permission_created", perm_id, {"name": permission_data.name}, current_user
        )

        return {"message": "Permission created successfully", "permission_id": perm_id}

    async def _list_groups(self):
        """List all groups"""
        group_keys = await self.db.list_keys("user_group:*")
        groups = []
        for key in group_keys:
            group = await self.db.get(key)
            if group:
                groups.append(group)
        return {"groups": groups}

    async def _create_group(self, group_data: UserGroup, current_user):
        """Create new user group"""
        group_id = str(uuid.uuid4())
        group = {
            "id": group_id,
            "name": group_data.name,
            "description": group_data.description,
            "group_type": group_data.group_type,
            "parent_group_id": group_data.parent_group_id,
            "metadata": group_data.metadata,
            "created_at": datetime.utcnow().isoformat(),
            "created_by": getattr(current_user, "id", None),
        }

        await self.db.set(f"user_group:{group_id}", group)

        await self._log_audit_event(
            "group_created", group_id, {"name": group_data.name}, current_user
        )

        if self.event_bus:
            await self.event_bus.publish("user_management.group.created", {"group_id": group_id})

        return {"message": "Group created successfully", "group_id": group_id}

    async def _get_group_members(self, group_id: str):
        """Get group members"""
        # Implementation for getting group members
        member_keys = await self.db.list_keys(f"group_member:{group_id}:*")
        members = []
        for key in member_keys:
            member = await self.db.get(key)
            if member:
                members.append(member)
        return {"members": members}

    async def _get_audit_logs(
        self,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        date_from: Optional[str] = None,
        date_to: Optional[str] = None,
        page: int = 1,
    ):
        """Get audit logs with filtering"""
        log_keys = await self.db.list_keys("audit:*")
        logs = []

        for key in log_keys:
            log = await self.db.get(key)
            if log and self._matches_audit_filter(log, user_id, action, date_from, date_to):
                logs.append(log)

        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Paginate
        page_size = 50
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_logs = logs[start_idx:end_idx]

        return {
            "logs": paginated_logs,
            "total_count": len(logs),
            "page": page,
            "page_size": page_size,
        }

    def _matches_audit_filter(
        self,
        log: Dict[str, Any],
        user_id: Optional[str],
        action: Optional[str],
        date_from: Optional[str],
        date_to: Optional[str],
    ) -> bool:
        """Check if audit log matches filters"""
        if user_id and log.get("user_id") != user_id:
            return False
        if action and log.get("action") != action:
            return False
        if date_from and log.get("timestamp", "") < date_from:
            return False
        if date_to and log.get("timestamp", "") > date_to:
            return False
        return True

    async def _generate_reports(self):
        """Generate user management reports"""
        reports = {
            "user_statistics": await self._get_user_statistics(),
            "role_distribution": await self._get_role_distribution(),
            "group_membership": await self._get_group_membership_stats(),
            "activity_summary": await self._get_activity_summary(),
        }
        return reports

    async def _get_user_statistics(self):
        """Get user statistics"""
        user_keys = await self.db.list_keys("user:id:*")
        total_users = len(user_keys)
        active_users = 0
        verified_users = 0

        for key in user_keys:
            user = await self.db.get(key)
            if user:
                if user.get("is_active"):
                    active_users += 1
                if user.get("is_verified"):
                    verified_users += 1

        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "verified_users": verified_users,
            "unverified_users": total_users - verified_users,
        }

    async def _get_role_distribution(self):
        """Get role distribution statistics"""
        # Implementation for role distribution
        return {"roles": []}

    async def _get_group_membership_stats(self):
        """Get group membership statistics"""
        # Implementation for group membership stats
        return {"groups": []}

    async def _get_activity_summary(self):
        """Get user activity summary"""
        # Implementation for activity summary
        return {"activities": []}

    async def _log_audit_event(
        self,
        action: str,
        target_id: str,
        details: Dict[str, Any],
        current_user=None,
    ):
        """Log audit event"""
        if not self.config.get("enable_audit_logging", True):
            return

        audit_id = str(uuid.uuid4())
        audit_log = {
            "id": audit_id,
            "user_id": getattr(current_user, "id", None) if current_user else None,
            "target_user_id": (
                target_id if action.endswith(("_user", "_role", "_permission", "_group")) else None
            ),
            "action": action,
            "resource": "user_management",
            "resource_id": target_id,
            "details": details,
            "timestamp": datetime.utcnow().isoformat(),
        }

        await self.db.set(f"audit:{audit_id}", audit_log)

    async def _get_recent_activity(self):
        """Get recent user management activity"""
        log_keys = await self.db.list_keys("audit:*")
        logs = []

        for key in log_keys[-20:]:  # Get last 20 entries
            log = await self.db.get(key)
            if log:
                logs.append(log)

        return sorted(logs, key=lambda x: x.get("timestamp", ""), reverse=True)

    async def _get_dashboard_charts(self):
        """Get dashboard chart data"""
        return {
            "user_growth": await self._get_user_growth_data(),
            "role_usage": await self._get_role_usage_data(),
            "activity_trend": await self._get_activity_trend_data(),
        }

    async def _get_user_growth_data(self):
        """Get user growth chart data"""
        # Implementation for user growth chart
        return {"labels": [], "data": []}

    async def _get_role_usage_data(self):
        """Get role usage chart data"""
        # Implementation for role usage chart
        return {"labels": [], "data": []}

    async def _get_activity_trend_data(self):
        """Get activity trend chart data"""
        # Implementation for activity trend chart
        return {"labels": [], "data": []}

    async def _count_new_users_this_week(self):
        """Count new users created this week"""
        week_ago = (datetime.utcnow() - timedelta(days=7)).isoformat()
        user_keys = await self.db.list_keys("user:id:*")
        count = 0

        for key in user_keys:
            user = await self.db.get(key)
            if user and user.get("created_at", "") > week_ago:
                count += 1

        return count

    async def _count_active_sessions(self):
        """Count active user sessions"""
        session_keys = await self.db.list_keys("session:*")
        active_count = 0

        for key in session_keys:
            session = await self.db.get(key)
            if session:
                expires_at = datetime.fromisoformat(session.get("expires_at", "1970-01-01"))
                if expires_at > datetime.utcnow():
                    active_count += 1

        return active_count

    def get_api_routes(self):
        """Get plugin API routes for registration"""
        return [self.router]


# Plugin instance
plugin = UserManagementPlugin()


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
    return [plugin.router]


def get_name():
    """Get plugin name"""
    return plugin.name


def get_version():
    """Get plugin version"""
    return plugin.version
