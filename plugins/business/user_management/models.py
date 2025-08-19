"""
User Management Plugin Models

This module contains all data models and validation classes for the user management plugin.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
from pydantic import BaseModel, validator, EmailStr


class User(BaseModel):
    """Model for user accounts"""

    username: str
    email: EmailStr
    first_name: str
    last_name: str
    password_hash: Optional[str] = None
    is_active: bool = True
    is_verified: bool = False
    is_superuser: bool = False
    profile_image: Optional[str] = None
    phone: Optional[str] = None
    department: Optional[str] = None
    job_title: Optional[str] = None
    manager_id: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @validator("username")
    def validate_username(cls, v):
        if not v or len(v.strip()) < 3:
            raise ValueError("Username must be at least 3 characters long")
        if not v.replace("_", "").replace("-", "").isalnum():
            raise ValueError("Username can only contain letters, numbers, hyphens, and underscores")
        return v.lower().strip()

    @validator("password_hash")
    def validate_password_hash(cls, v):
        if v and len(v) < 8:
            raise ValueError("Password hash too short")
        return v


class Role(BaseModel):
    """Model for user roles"""

    name: str
    description: Optional[str] = None
    permissions: List[str] = []
    is_system_role: bool = False
    color: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Role name must be at least 2 characters long")
        return v.lower().strip()


class Permission(BaseModel):
    """Model for permissions"""

    name: str
    description: Optional[str] = None
    category: str = "general"
    is_system_permission: bool = False
    metadata: Dict[str, Any] = {}

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Permission name must be at least 2 characters long")
        # Permission names should follow a dotted notation like "users.create"
        if "." not in v:
            raise ValueError("Permission name should use dotted notation (e.g., 'users.create')")
        return v.lower().strip()


class Organization(BaseModel):
    """Model for organizational units"""

    name: str
    description: Optional[str] = None
    parent_id: Optional[str] = None
    org_type: str = "department"  # department, team, division, company
    manager_id: Optional[str] = None
    budget: Optional[float] = None
    cost_center: Optional[str] = None
    location: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Organization name must be at least 2 characters long")
        return v.strip()

    @validator("org_type")
    def validate_org_type(cls, v):
        valid_types = ["department", "team", "division", "company", "branch", "region"]
        if v not in valid_types:
            raise ValueError(f"Organization type must be one of: {valid_types}")
        return v


class UserRole(BaseModel):
    """Model for user-role assignments"""

    user_id: str
    role_id: str
    assigned_by: Optional[str] = None
    assigned_at: Optional[str] = None
    expires_at: Optional[str] = None
    is_active: bool = True
    scope: Optional[str] = None  # For scoped permissions (e.g., organization-specific)
    metadata: Dict[str, Any] = {}


class UserPermission(BaseModel):
    """Model for direct user permission assignments"""

    user_id: str
    permission_id: str
    granted: bool = True  # True for grant, False for explicit deny
    assigned_by: Optional[str] = None
    assigned_at: Optional[str] = None
    expires_at: Optional[str] = None
    scope: Optional[str] = None
    reason: Optional[str] = None
    metadata: Dict[str, Any] = {}


class UserProfile(BaseModel):
    """Extended user profile model"""

    user_id: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
    timezone: str = "UTC"
    language: str = "en"
    theme: str = "light"
    notifications_enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    two_factor_enabled: bool = False
    last_login: Optional[str] = None
    login_count: int = 0
    failed_login_attempts: int = 0
    account_locked_until: Optional[str] = None
    password_changed_at: Optional[str] = None
    must_change_password: bool = False
    preferences: Dict[str, Any] = {}
    social_links: Dict[str, str] = {}
    skills: List[str] = []
    certifications: List[str] = []


class UserSession(BaseModel):
    """Model for user sessions"""

    session_id: str
    user_id: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str
    last_activity: str
    expires_at: str
    is_active: bool = True
    session_data: Dict[str, Any] = {}


class AuditLog(BaseModel):
    """Model for audit logging"""

    action: str
    actor_id: Optional[str] = None
    actor_name: Optional[str] = None
    target_type: str
    target_id: str
    target_name: Optional[str] = None
    changes: Dict[str, Any] = {}
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    timestamp: str
    result: str = "success"  # success, failure, error
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @validator("action")
    def validate_action(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Action must be specified")
        return v.lower().strip()

    @validator("result")
    def validate_result(cls, v):
        valid_results = ["success", "failure", "error"]
        if v not in valid_results:
            raise ValueError(f"Result must be one of: {valid_results}")
        return v


class UserGroup(BaseModel):
    """Model for user groups"""

    name: str
    description: Optional[str] = None
    group_type: str = "custom"  # system, department, project, custom
    owner_id: Optional[str] = None
    is_active: bool = True
    auto_join_rules: Dict[str, Any] = {}
    metadata: Dict[str, Any] = {}

    @validator("name")
    def validate_name(cls, v):
        if not v or len(v.strip()) < 2:
            raise ValueError("Group name must be at least 2 characters long")
        return v.strip()

    @validator("group_type")
    def validate_group_type(cls, v):
        valid_types = ["system", "department", "project", "custom"]
        if v not in valid_types:
            raise ValueError(f"Group type must be one of: {valid_types}")
        return v


class UserGroupMembership(BaseModel):
    """Model for user group memberships"""

    user_id: str
    group_id: str
    role: str = "member"  # owner, admin, moderator, member
    joined_at: str
    added_by: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = {}

    @validator("role")
    def validate_role(cls, v):
        valid_roles = ["owner", "admin", "moderator", "member"]
        if v not in valid_roles:
            raise ValueError(f"Role must be one of: {valid_roles}")
        return v


class UserInvitation(BaseModel):
    """Model for user invitations"""

    email: EmailStr
    invited_by: str
    role_ids: List[str] = []
    organization_id: Optional[str] = None
    invitation_code: str
    expires_at: str
    message: Optional[str] = None
    is_accepted: bool = False
    accepted_at: Optional[str] = None
    accepted_by: Optional[str] = None
    metadata: Dict[str, Any] = {}


class PasswordResetToken(BaseModel):
    """Model for password reset tokens"""

    user_id: str
    token: str
    created_at: str
    expires_at: str
    is_used: bool = False
    used_at: Optional[str] = None
    ip_address: Optional[str] = None


class UserActivity(BaseModel):
    """Model for tracking user activities"""

    user_id: str
    activity_type: str
    activity_description: str
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    timestamp: str
    metadata: Dict[str, Any] = {}

    @validator("activity_type")
    def validate_activity_type(cls, v):
        valid_types = [
            "login",
            "logout",
            "password_change",
            "profile_update",
            "permission_change",
            "role_change",
            "create",
            "update",
            "delete",
            "view",
            "export",
            "import",
            "upload",
            "download",
        ]
        if v not in valid_types:
            raise ValueError(f"Activity type must be one of: {valid_types}")
        return v


class UserPreferences(BaseModel):
    """Model for user preferences and settings"""

    user_id: str
    category: str
    settings: Dict[str, Any] = {}
    updated_at: str

    @validator("category")
    def validate_category(cls, v):
        valid_categories = [
            "appearance",
            "notifications",
            "privacy",
            "security",
            "language",
            "timezone",
            "dashboard",
            "reports",
            "general",
        ]
        if v not in valid_categories:
            raise ValueError(f"Category must be one of: {valid_categories}")
        return v


class ComplianceRecord(BaseModel):
    """Model for compliance and regulatory records"""

    user_id: str
    regulation_type: str  # GDPR, CCPA, HIPAA, etc.
    action: str
    details: Dict[str, Any] = {}
    timestamp: str
    compliance_officer: Optional[str] = None
    retention_until: Optional[str] = None
    metadata: Dict[str, Any] = {}

    @validator("regulation_type")
    def validate_regulation_type(cls, v):
        valid_types = ["GDPR", "CCPA", "HIPAA", "SOX", "PCI", "ISO27001", "CUSTOM"]
        if v not in valid_types:
            raise ValueError(f"Regulation type must be one of: {valid_types}")
        return v
