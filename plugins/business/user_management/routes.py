"""
User Management Plugin API Routes

This module contains all API route handlers for the user management plugin.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from fastapi import (
    APIRouter,
    HTTPException,
    Depends,
    Form,
    Query,
    BackgroundTasks,
    status,
)
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from nexus.database import DatabaseAdapter
from nexus.core import EventBus
from nexus.auth import get_current_user_dependency

from .models import (
    User,
    Role,
    Permission,
    Organization,
    UserRole,
    UserPermission,
    UserProfile,
    UserGroup,
    UserInvitation,
    AuditLog,
)

logger = logging.getLogger(__name__)


class UserManagementRoutes:
    """User management plugin routes handler"""

    def __init__(self, plugin_instance):
        self.plugin = plugin_instance
        self.router = APIRouter(prefix="/user_management", tags=["user_management"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup all user management routes"""

        # Dashboard and UI routes
        @self.router.get("/", response_class=HTMLResponse)
        async def dashboard(user=Depends(get_current_user_dependency)):
            """User management dashboard"""
            return await self.plugin._render_dashboard(user)

        # User management routes
        @self.router.get("/users", response_model=List[Dict[str, Any]])
        async def list_users(
            limit: int = Query(50, le=100),
            offset: int = Query(0, ge=0),
            search: Optional[str] = Query(None),
            department: Optional[str] = Query(None),
            is_active: Optional[bool] = Query(None),
            user=Depends(get_current_user_dependency),
        ):
            """List users with filtering and pagination"""
            return await self.plugin._list_users(user, limit, offset, search, department, is_active)

        @self.router.post("/users", response_model=Dict[str, Any])
        async def create_user(
            user_data: User,
            background_tasks: BackgroundTasks,
            user=Depends(get_current_user_dependency),
        ):
            """Create a new user"""
            return await self.plugin._create_user(user_data, user, background_tasks)

        @self.router.get("/users/{user_id}", response_model=Dict[str, Any])
        async def get_user(user_id: str, user=Depends(get_current_user_dependency)):
            """Get user details"""
            return await self.plugin._get_user(user_id, user)

        @self.router.put("/users/{user_id}", response_model=Dict[str, Any])
        async def update_user(
            user_id: str,
            update_data: Dict[str, Any],
            background_tasks: BackgroundTasks,
            user=Depends(get_current_user_dependency),
        ):
            """Update user information"""
            return await self.plugin._update_user(user_id, update_data, user, background_tasks)

        @self.router.delete("/users/{user_id}")
        async def delete_user(user_id: str, user=Depends(get_current_user_dependency)):
            """Delete (deactivate) user"""
            return await self.plugin._delete_user(user_id, user)

        @self.router.post("/users/{user_id}/activate")
        async def activate_user(user_id: str, user=Depends(get_current_user_dependency)):
            """Activate a user account"""
            return await self.plugin._activate_user(user_id, user)

        @self.router.post("/users/{user_id}/deactivate")
        async def deactivate_user(user_id: str, user=Depends(get_current_user_dependency)):
            """Deactivate a user account"""
            return await self.plugin._deactivate_user(user_id, user)

        # Password management
        @self.router.post("/users/{user_id}/reset-password")
        async def reset_password(
            user_id: str,
            background_tasks: BackgroundTasks,
            user=Depends(get_current_user_dependency),
        ):
            """Reset user password"""
            return await self.plugin._reset_password(user_id, user, background_tasks)

        @self.router.post("/users/{user_id}/change-password")
        async def change_password(
            user_id: str,
            current_password: str = Form(...),
            new_password: str = Form(...),
            user=Depends(get_current_user_dependency),
        ):
            """Change user password"""
            return await self.plugin._change_password(user_id, current_password, new_password, user)

        @self.router.post("/users/{user_id}/force-password-change")
        async def force_password_change(user_id: str, user=Depends(get_current_user_dependency)):
            """Force user to change password on next login"""
            return await self.plugin._force_password_change(user_id, user)

        # Profile management
        @self.router.get("/users/{user_id}/profile", response_model=Dict[str, Any])
        async def get_user_profile(user_id: str, user=Depends(get_current_user_dependency)):
            """Get user profile"""
            return await self.plugin._get_user_profile(user_id, user)

        @self.router.put("/users/{user_id}/profile", response_model=Dict[str, Any])
        async def update_user_profile(
            user_id: str,
            profile_data: Dict[str, Any],
            user=Depends(get_current_user_dependency),
        ):
            """Update user profile"""
            return await self.plugin._update_user_profile(user_id, profile_data, user)

        # Role management routes
        @self.router.get("/roles", response_model=List[Dict[str, Any]])
        async def list_roles(
            limit: int = Query(50, le=100),
            offset: int = Query(0, ge=0),
            user=Depends(get_current_user_dependency),
        ):
            """List all roles"""
            return await self.plugin._list_roles(user, limit, offset)

        @self.router.post("/roles", response_model=Dict[str, Any])
        async def create_role(role_data: Role, user=Depends(get_current_user_dependency)):
            """Create a new role"""
            return await self.plugin._create_role(role_data, user)

        @self.router.get("/roles/{role_id}", response_model=Dict[str, Any])
        async def get_role(role_id: str, user=Depends(get_current_user_dependency)):
            """Get role details"""
            return await self.plugin._get_role(role_id, user)

        @self.router.put("/roles/{role_id}", response_model=Dict[str, Any])
        async def update_role(
            role_id: str, role_data: Dict[str, Any], user=Depends(get_current_user_dependency)
        ):
            """Update role"""
            return await self.plugin._update_role(role_id, role_data, user)

        @self.router.delete("/roles/{role_id}")
        async def delete_role(role_id: str, user=Depends(get_current_user_dependency)):
            """Delete role"""
            return await self.plugin._delete_role(role_id, user)

        # User-Role assignment routes
        @self.router.get("/users/{user_id}/roles", response_model=List[Dict[str, Any]])
        async def get_user_roles(user_id: str, user=Depends(get_current_user_dependency)):
            """Get roles assigned to user"""
            return await self.plugin._get_user_roles(user_id, user)

        @self.router.post("/users/{user_id}/roles/{role_id}")
        async def assign_role_to_user(
            user_id: str,
            role_id: str,
            scope: Optional[str] = Form(None),
            user=Depends(get_current_user_dependency),
        ):
            """Assign role to user"""
            return await self.plugin._assign_role_to_user(user_id, role_id, scope, user)

        @self.router.delete("/users/{user_id}/roles/{role_id}")
        async def revoke_role_from_user(
            user_id: str,
            role_id: str,
            scope: Optional[str] = Query(None),
            user=Depends(get_current_user_dependency),
        ):
            """Revoke role from user"""
            return await self.plugin._revoke_role_from_user(user_id, role_id, scope, user)

        # Permission management routes
        @self.router.get("/permissions", response_model=List[Dict[str, Any]])
        async def list_permissions(user=Depends(get_current_user_dependency)):
            """List all permissions"""
            return await self.plugin._list_permissions(user)

        @self.router.post("/permissions", response_model=Dict[str, Any])
        async def create_permission(
            permission_data: Permission, user=Depends(get_current_user_dependency)
        ):
            """Create a new permission"""
            return await self.plugin._create_permission(permission_data, user)

        @self.router.get("/users/{user_id}/permissions", response_model=List[str])
        async def get_user_permissions(user_id: str, user=Depends(get_current_user_dependency)):
            """Get effective permissions for user"""
            return await self.plugin._get_user_permissions(user_id, user)

        # Organization management routes
        @self.router.get("/organizations", response_model=List[Dict[str, Any]])
        async def list_organizations(user=Depends(get_current_user_dependency)):
            """List organizations"""
            return await self.plugin._list_organizations(user)

        @self.router.post("/organizations", response_model=Dict[str, Any])
        async def create_organization(
            org_data: Organization, user=Depends(get_current_user_dependency)
        ):
            """Create organization"""
            return await self.plugin._create_organization(org_data, user)

        @self.router.get("/organizations/hierarchy", response_model=List[Dict[str, Any]])
        async def get_organization_hierarchy(user=Depends(get_current_user_dependency)):
            """Get organization hierarchy"""
            return await self.plugin._get_organization_hierarchy(user)

        # User invitation routes
        @self.router.post("/invitations", response_model=Dict[str, Any])
        async def send_invitation(
            invitation_data: UserInvitation,
            background_tasks: BackgroundTasks,
            user=Depends(get_current_user_dependency),
        ):
            """Send user invitation"""
            return await self.plugin._send_invitation(invitation_data, user, background_tasks)

        @self.router.get("/invitations", response_model=List[Dict[str, Any]])
        async def list_invitations(
            limit: int = Query(50, le=100),
            offset: int = Query(0, ge=0),
            user=Depends(get_current_user_dependency),
        ):
            """List pending invitations"""
            return await self.plugin._list_invitations(user, limit, offset)

        @self.router.post("/invitations/{invitation_id}/accept")
        async def accept_invitation(
            invitation_id: str,
            password: str = Form(...),
            user=Depends(get_current_user_dependency),
        ):
            """Accept user invitation"""
            return await self.plugin._accept_invitation(invitation_id, password, user)

        @self.router.delete("/invitations/{invitation_id}")
        async def revoke_invitation(invitation_id: str, user=Depends(get_current_user_dependency)):
            """Revoke invitation"""
            return await self.plugin._revoke_invitation(invitation_id, user)

        # Group management routes
        @self.router.get("/groups", response_model=List[Dict[str, Any]])
        async def list_groups(
            limit: int = Query(50, le=100),
            offset: int = Query(0, ge=0),
            user=Depends(get_current_user_dependency),
        ):
            """List user groups"""
            return await self.plugin._list_groups(user, limit, offset)

        @self.router.post("/groups", response_model=Dict[str, Any])
        async def create_group(group_data: UserGroup, user=Depends(get_current_user_dependency)):
            """Create user group"""
            return await self.plugin._create_group(group_data, user)

        @self.router.get("/groups/{group_id}/members", response_model=List[Dict[str, Any]])
        async def get_group_members(group_id: str, user=Depends(get_current_user_dependency)):
            """Get group members"""
            return await self.plugin._get_group_members(group_id, user)

        @self.router.post("/groups/{group_id}/members/{user_id}")
        async def add_user_to_group(
            group_id: str, user_id: str, user=Depends(get_current_user_dependency)
        ):
            """Add user to group"""
            return await self.plugin._add_user_to_group(group_id, user_id, user)

        @self.router.delete("/groups/{group_id}/members/{user_id}")
        async def remove_user_from_group(
            group_id: str, user_id: str, user=Depends(get_current_user_dependency)
        ):
            """Remove user from group"""
            return await self.plugin._remove_user_from_group(group_id, user_id, user)

        # Session management routes
        @self.router.get("/users/{user_id}/sessions", response_model=List[Dict[str, Any]])
        async def get_user_sessions(user_id: str, user=Depends(get_current_user_dependency)):
            """Get user sessions"""
            return await self.plugin._get_user_sessions(user_id, user)

        @self.router.delete("/users/{user_id}/sessions/{session_id}")
        async def terminate_session(
            user_id: str, session_id: str, user=Depends(get_current_user_dependency)
        ):
            """Terminate user session"""
            return await self.plugin._terminate_session(user_id, session_id, user)

        @self.router.delete("/users/{user_id}/sessions")
        async def terminate_all_sessions(user_id: str, user=Depends(get_current_user_dependency)):
            """Terminate all user sessions"""
            return await self.plugin._terminate_all_sessions(user_id, user)

        # Audit and reporting routes
        @self.router.get("/audit", response_model=List[Dict[str, Any]])
        async def get_audit_logs(
            target_type: Optional[str] = Query(None),
            target_id: Optional[str] = Query(None),
            actor_id: Optional[str] = Query(None),
            limit: int = Query(100, le=500),
            offset: int = Query(0, ge=0),
            user=Depends(get_current_user_dependency),
        ):
            """Get audit logs"""
            return await self.plugin._get_audit_logs(
                user, target_type, target_id, actor_id, limit, offset
            )

        @self.router.get("/reports/user-activity", response_model=Dict[str, Any])
        async def get_user_activity_report(
            start_date: Optional[str] = Query(None),
            end_date: Optional[str] = Query(None),
            user_id: Optional[str] = Query(None),
            user=Depends(get_current_user_dependency),
        ):
            """Get user activity report"""
            return await self.plugin._get_user_activity_report(user, start_date, end_date, user_id)

        @self.router.get("/reports/role-distribution", response_model=Dict[str, Any])
        async def get_role_distribution_report(user=Depends(get_current_user_dependency)):
            """Get role distribution report"""
            return await self.plugin._get_role_distribution_report(user)

        @self.router.get("/reports/user-stats", response_model=Dict[str, Any])
        async def get_user_statistics(user=Depends(get_current_user_dependency)):
            """Get user statistics"""
            return await self.plugin._get_user_statistics(user)

        # Import/Export routes
        @self.router.post("/import/users")
        async def import_users(
            background_tasks: BackgroundTasks,
            import_data: List[Dict[str, Any]],
            user=Depends(get_current_user_dependency),
        ):
            """Import users from data"""
            return await self.plugin._import_users(import_data, user, background_tasks)

        @self.router.get("/export/users")
        async def export_users(
            format: str = Query("csv", regex="^(csv|json|xlsx)$"),
            user=Depends(get_current_user_dependency),
        ):
            """Export users data"""
            return await self.plugin._export_users(format, user)

        # Advanced user management
        @self.router.post("/users/{user_id}/impersonate")
        async def impersonate_user(user_id: str, user=Depends(get_current_user_dependency)):
            """Start impersonating another user (admin only)"""
            return await self.plugin._impersonate_user(user_id, user)

        @self.router.post("/users/{user_id}/unlock")
        async def unlock_user_account(user_id: str, user=Depends(get_current_user_dependency)):
            """Unlock locked user account"""
            return await self.plugin._unlock_user_account(user_id, user)

        @self.router.get("/users/{user_id}/activity", response_model=List[Dict[str, Any]])
        async def get_user_activity(
            user_id: str,
            limit: int = Query(50, le=100),
            offset: int = Query(0, ge=0),
            user=Depends(get_current_user_dependency),
        ):
            """Get user activity log"""
            return await self.plugin._get_user_activity(user_id, user, limit, offset)

        # Preferences and settings
        @self.router.get("/users/{user_id}/preferences", response_model=Dict[str, Any])
        async def get_user_preferences(user_id: str, user=Depends(get_current_user_dependency)):
            """Get user preferences"""
            return await self.plugin._get_user_preferences(user_id, user)

        @self.router.put("/users/{user_id}/preferences")
        async def update_user_preferences(
            user_id: str,
            preferences: Dict[str, Any],
            user=Depends(get_current_user_dependency),
        ):
            """Update user preferences"""
            return await self.plugin._update_user_preferences(user_id, preferences, user)

        # Compliance and GDPR
        @self.router.post("/users/{user_id}/data-export")
        async def export_user_data(
            user_id: str,
            background_tasks: BackgroundTasks,
            user=Depends(get_current_user_dependency),
        ):
            """Export all user data (GDPR compliance)"""
            return await self.plugin._export_user_data(user_id, user, background_tasks)

        @self.router.post("/users/{user_id}/anonymize")
        async def anonymize_user_data(user_id: str, user=Depends(get_current_user_dependency)):
            """Anonymize user data"""
            return await self.plugin._anonymize_user_data(user_id, user)

        @self.router.delete("/users/{user_id}/data")
        async def delete_user_data(user_id: str, user=Depends(get_current_user_dependency)):
            """Permanently delete user data"""
            return await self.plugin._delete_user_data(user_id, user)

        # Health and monitoring
        @self.router.get("/health", response_model=Dict[str, Any])
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "plugin": "user_management",
                "version": self.plugin.version,
            }

        @self.router.get("/stats", response_model=Dict[str, Any])
        async def get_system_stats(user=Depends(get_current_user_dependency)):
            """Get system statistics"""
            return await self.plugin._get_system_stats(user)
