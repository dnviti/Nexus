"""
Comprehensive unit tests for the Nexus auth module.

Tests cover authentication, authorization, user management, and basic auth functionality.
"""

from datetime import datetime
from unittest.mock import AsyncMock

import pytest

from nexus.auth import AuthenticationManager, User, create_default_admin, get_current_user


class TestUser:
    """Test User model."""

    def test_user_creation(self):
        """Test creating a user."""
        user = User(
            id="user123",
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            created_at=datetime.now(),
        )

        assert user.id == "user123"
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active == True
        assert user.is_superuser == False
        assert user.permissions == []
        assert user.roles == []

    def test_user_defaults(self):
        """Test user with default values."""
        user = User(
            id="user456",
            username="defaultuser",
            email="default@example.com",
            created_at=datetime.now(),
        )

        assert user.full_name is None
        assert user.is_active == True
        assert user.is_superuser == False
        assert user.last_login is None
        assert user.permissions == []
        assert user.roles == []

    def test_user_with_permissions_and_roles(self):
        """Test user with permissions and roles."""
        user = User(
            id="admin123",
            username="admin",
            email="admin@example.com",
            created_at=datetime.now(),
            is_superuser=True,
            permissions=["read", "write", "delete"],
            roles=["admin", "moderator"],
        )

        assert user.is_superuser == True
        assert "read" in user.permissions
        assert "write" in user.permissions
        assert "delete" in user.permissions
        assert "admin" in user.roles
        assert "moderator" in user.roles

    def test_user_inactive(self):
        """Test creating inactive user."""
        user = User(
            id="inactive123",
            username="inactive",
            email="inactive@example.com",
            created_at=datetime.now(),
            is_active=False,
        )

        assert user.is_active == False

    def test_user_with_last_login(self):
        """Test user with last login time."""
        login_time = datetime.now()
        user = User(
            id="logged123",
            username="loggeduser",
            email="logged@example.com",
            created_at=datetime.now(),
            last_login=login_time,
        )

        assert user.last_login == login_time


class TestAuthenticationManager:
    """Test AuthenticationManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_manager = AuthenticationManager()

    def test_auth_manager_creation(self):
        """Test creating AuthenticationManager."""
        assert self.auth_manager is not None
        assert self.auth_manager.users == {}
        assert self.auth_manager.sessions == {}

    @pytest.mark.asyncio
    async def test_create_user_basic(self):
        """Test creating a basic user."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name is None
        assert user.is_superuser == False
        assert user.is_active == True
        assert "read" in user.permissions
        assert "user" in user.roles
        assert user.id in self.auth_manager.users

    @pytest.mark.asyncio
    async def test_create_user_with_full_name(self):
        """Test creating user with full name."""
        user = await self.auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="test_password",
            full_name="Test User",
        )

        assert user.full_name == "Test User"

    @pytest.mark.asyncio
    async def test_create_superuser(self):
        """Test creating a superuser."""
        user = await self.auth_manager.create_user(
            username="admin",
            email="admin@example.com",
            password="admin_password",
            is_superuser=True,
        )

        assert user.is_superuser == True
        assert "admin" in user.permissions
        assert "read" in user.permissions
        assert "write" in user.permissions
        assert "admin" in user.roles
        assert "user" in user.roles

    @pytest.mark.asyncio
    async def test_create_multiple_users(self):
        """Test creating multiple users."""
        user1 = await self.auth_manager.create_user(
            username="user1", email="user1@example.com", password="password1"
        )
        user2 = await self.auth_manager.create_user(
            username="user2", email="user2@example.com", password="password2"
        )

        assert len(self.auth_manager.users) == 2
        assert user1.id != user2.id
        assert user1.id in self.auth_manager.users
        assert user2.id in self.auth_manager.users

    @pytest.mark.asyncio
    async def test_authenticate_existing_user(self):
        """Test authenticating existing user."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        authenticated_user = await self.auth_manager.authenticate("testuser", "test_password")

        assert authenticated_user is not None
        assert authenticated_user.id == user.id
        assert authenticated_user.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_nonexistent_user(self):
        """Test authenticating non-existent user."""
        result = await self.auth_manager.authenticate("nonexistent", "password")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_user_existing(self):
        """Test getting existing user by ID."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        retrieved_user = await self.auth_manager.get_user(user.id)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id
        assert retrieved_user.username == user.username

    @pytest.mark.asyncio
    async def test_get_user_nonexistent(self):
        """Test getting non-existent user."""
        result = await self.auth_manager.get_user("nonexistent_id")

        assert result is None

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Test creating authentication session."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        token = await self.auth_manager.create_session(user)

        assert isinstance(token, str)
        assert len(token) > 0
        assert token in self.auth_manager.sessions
        assert self.auth_manager.sessions[token] == user.id
        assert user.last_login is not None

    @pytest.mark.asyncio
    async def test_get_user_by_token_valid(self):
        """Test getting user by valid token."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )
        token = await self.auth_manager.create_session(user)

        retrieved_user = await self.auth_manager.get_user_by_token(token)

        assert retrieved_user is not None
        assert retrieved_user.id == user.id

    @pytest.mark.asyncio
    async def test_get_user_by_token_invalid(self):
        """Test getting user by invalid token."""
        result = await self.auth_manager.get_user_by_token("invalid_token")

        assert result is None

    @pytest.mark.asyncio
    async def test_validate_permission_allowed(self):
        """Test validating permission when user has it."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        result = await self.auth_manager.validate_permission(user, "read")

        assert result == True

    @pytest.mark.asyncio
    async def test_validate_permission_denied(self):
        """Test validating permission when user doesn't have it."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        result = await self.auth_manager.validate_permission(user, "admin")

        assert result == False

    @pytest.mark.asyncio
    async def test_validate_permission_admin_user(self):
        """Test validating permission for admin user."""
        user = await self.auth_manager.create_user(
            username="admin",
            email="admin@example.com",
            password="admin_password",
            is_superuser=True,
        )

        result = await self.auth_manager.validate_permission(user, "any_permission")

        assert result == True

    @pytest.mark.asyncio
    async def test_validate_role_allowed(self):
        """Test validating role when user has it."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        result = await self.auth_manager.validate_role(user, "user")

        assert result == True

    @pytest.mark.asyncio
    async def test_validate_role_denied(self):
        """Test validating role when user doesn't have it."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        result = await self.auth_manager.validate_role(user, "admin")

        assert result == False

    @pytest.mark.asyncio
    async def test_validate_role_admin_user(self):
        """Test validating role for admin user."""
        user = await self.auth_manager.create_user(
            username="admin",
            email="admin@example.com",
            password="admin_password",
            is_superuser=True,
        )

        result = await self.auth_manager.validate_role(user, "admin")

        assert result == True


class TestAuthenticationIntegration:
    """Test complete authentication workflows."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_manager = AuthenticationManager()

    @pytest.mark.asyncio
    async def test_full_authentication_flow(self):
        """Test complete authentication flow."""
        # Create user
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        # Authenticate user
        authenticated_user = await self.auth_manager.authenticate("testuser", "test_password")
        assert authenticated_user is not None
        assert authenticated_user.id == user.id

        # Create session
        token = await self.auth_manager.create_session(authenticated_user)
        assert token is not None

        # Get user by token
        token_user = await self.auth_manager.get_user_by_token(token)
        assert token_user is not None
        assert token_user.id == user.id

        # Validate permissions
        can_read = await self.auth_manager.validate_permission(token_user, "read")
        assert can_read == True

        can_admin = await self.auth_manager.validate_permission(token_user, "admin")
        assert can_admin == False

    @pytest.mark.asyncio
    async def test_admin_user_workflow(self):
        """Test admin user complete workflow."""
        # Create admin user
        admin = await self.auth_manager.create_user(
            username="admin",
            email="admin@example.com",
            password="admin_password",
            is_superuser=True,
        )

        # Verify admin permissions
        assert admin.is_superuser == True
        assert "admin" in admin.permissions
        assert "admin" in admin.roles

        # Validate admin can do everything
        can_read = await self.auth_manager.validate_permission(admin, "read")
        can_write = await self.auth_manager.validate_permission(admin, "write")
        can_admin = await self.auth_manager.validate_permission(admin, "admin")
        can_anything = await self.auth_manager.validate_permission(admin, "anything")

        assert all([can_read, can_write, can_admin, can_anything])

    @pytest.mark.asyncio
    async def test_multiple_sessions(self):
        """Test multiple sessions for same user."""
        user = await self.auth_manager.create_user(
            username="testuser", email="test@example.com", password="test_password"
        )

        # Create multiple sessions
        token1 = await self.auth_manager.create_session(user)
        token2 = await self.auth_manager.create_session(user)

        assert token1 != token2
        assert len(self.auth_manager.sessions) == 2

        # Both tokens should work
        user1 = await self.auth_manager.get_user_by_token(token1)
        user2 = await self.auth_manager.get_user_by_token(token2)

        assert user1 is not None
        assert user2 is not None
        assert user1.id == user.id
        assert user2.id == user.id


class TestCreateDefaultAdmin:
    """Test create_default_admin function."""

    @pytest.mark.asyncio
    async def test_create_default_admin(self):
        """Test creating default admin user."""
        auth_manager = AuthenticationManager()

        admin = await create_default_admin(auth_manager)

        assert admin is not None
        assert admin.username == "admin"
        assert admin.email == "admin@nexus.local"
        assert admin.full_name == "System Administrator"
        assert admin.is_superuser == True
        assert "admin" in admin.permissions
        assert "admin" in admin.roles

    @pytest.mark.asyncio
    async def test_create_default_admin_adds_to_manager(self):
        """Test that default admin is added to auth manager."""
        auth_manager = AuthenticationManager()
        initial_count = len(auth_manager.users)

        admin = await create_default_admin(auth_manager)

        assert len(auth_manager.users) == initial_count + 1
        assert admin.id in auth_manager.users
        assert auth_manager.users[admin.id] == admin


class TestGetCurrentUser:
    """Test get_current_user function."""

    @pytest.mark.asyncio
    async def test_get_current_user_with_token(self):
        """Test getting current user with token."""
        token = "valid_token"

        user = await get_current_user(token)

        assert user is not None
        assert user.id == "demo_user"
        assert user.username == "demo"
        assert user.email == "demo@nexus.local"
        assert user.full_name == "Demo User"
        assert "read" in user.permissions
        assert "write" in user.permissions
        assert "user" in user.roles

    @pytest.mark.asyncio
    async def test_get_current_user_without_token(self):
        """Test getting current user without token."""
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(None)

        assert exc_info.value.status_code == 401
        assert "Authentication required" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_get_current_user_empty_token(self):
        """Test getting current user with empty token."""
        import pytest
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("")

        assert exc_info.value.status_code == 401


class TestUserModel:
    """Test User model edge cases."""

    def test_user_model_validation(self):
        """Test user model with various inputs."""
        # Test with minimal required fields
        user = User(
            id="test_id", username="test", email="test@example.com", created_at=datetime.now()
        )

        assert user.id == "test_id"
        assert user.username == "test"
        assert user.email == "test@example.com"

    def test_user_model_with_all_fields(self):
        """Test user model with all fields populated."""
        now = datetime.now()
        login_time = datetime.now()

        user = User(
            id="full_user",
            username="fulluser",
            email="full@example.com",
            full_name="Full User Name",
            is_active=True,
            is_superuser=True,
            created_at=now,
            last_login=login_time,
            permissions=["read", "write", "admin"],
            roles=["user", "admin", "moderator"],
        )

        assert user.id == "full_user"
        assert user.username == "fulluser"
        assert user.email == "full@example.com"
        assert user.full_name == "Full User Name"
        assert user.is_active == True
        assert user.is_superuser == True
        assert user.created_at == now
        assert user.last_login == login_time
        assert len(user.permissions) == 3
        assert len(user.roles) == 3

    def test_user_model_permissions_list(self):
        """Test user model permissions list operations."""
        user = User(
            id="perm_user",
            username="permuser",
            email="perm@example.com",
            created_at=datetime.now(),
            permissions=["read", "write"],
        )

        assert "read" in user.permissions
        assert "write" in user.permissions
        assert "admin" not in user.permissions
        assert len(user.permissions) == 2

    def test_user_model_roles_list(self):
        """Test user model roles list operations."""
        user = User(
            id="role_user",
            username="roleuser",
            email="role@example.com",
            created_at=datetime.now(),
            roles=["user", "editor"],
        )

        assert "user" in user.roles
        assert "editor" in user.roles
        assert "admin" not in user.roles
        assert len(user.roles) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
