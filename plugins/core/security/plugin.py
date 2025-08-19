"""
Security Plugin for Nexus Platform

This plugin provides comprehensive security functionality including:
- JWT-based authentication and authorization
- Session management and security
- Role-based access control (RBAC)
- Security event logging and monitoring
- API key management
- Security dashboard and analytics
- Two-factor authentication support
- Password policies and management
- Security audit trails
- Threat detection and prevention

Architecture:
- models.py: Data models and validation (to be created)
- services.py: Business logic and services (to be created)
- routes.py: API route handlers (to be created)
- auth.py: Authentication and authorization logic (to be created)
- plugin.py: Main plugin class (legacy compatibility)
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid
import jwt
import secrets
import bcrypt
from passlib.context import CryptContext

from nexus.database import DatabaseAdapter
from nexus.core import EventBus

logger = logging.getLogger(__name__)


class SecurityPlugin:
    """Main Security Plugin Class"""

    def __init__(self):
        self.name = "security"
        self.version = "1.0.0"
        self.db: Optional[DatabaseAdapter] = None
        self.event_bus: Optional[EventBus] = None
        self.config: Dict[str, Any] = {}

        # Security components
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        self.jwt_secret = "your-secret-key"  # In production, use environment variable

        # Rate limiting and security tracking
        self.login_attempts: Dict[str, List[datetime]] = {}
        self.blocked_ips: Dict[str, datetime] = {}

    async def initialize(self, db: DatabaseAdapter, event_bus: EventBus, config: Dict[str, Any]):
        """Initialize the security plugin"""
        self.db = db
        self.event_bus = event_bus
        self.config = config

        # Setup database tables
        await self._setup_database()

        # Setup event handlers
        await self._setup_event_handlers()

        # Initialize security policies
        await self._initialize_security_policies()

        # Create default admin user if it doesn't exist
        await self._create_default_admin()

        logger.info("Security plugin initialized")

    async def _setup_database(self):
        """Setup database tables for security functionality"""
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
            "security_sessions": """
                CREATE TABLE IF NOT EXISTS security_sessions (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    session_token TEXT UNIQUE NOT NULL,
                    refresh_token TEXT UNIQUE,
                    ip_address TEXT,
                    user_agent TEXT,
                    created_at TEXT,
                    expires_at TEXT,
                    last_activity TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT DEFAULT '{}'
                )
            """,
            "api_keys": """
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY,
                    key_hash TEXT UNIQUE NOT NULL,
                    name TEXT,
                    user_id TEXT,
                    permissions TEXT DEFAULT '[]',
                    expires_at TEXT,
                    created_at TEXT,
                    last_used TEXT,
                    is_active BOOLEAN DEFAULT TRUE,
                    metadata TEXT DEFAULT '{}'
                )
            """,
            "security_events": """
                CREATE TABLE IF NOT EXISTS security_events (
                    id TEXT PRIMARY KEY,
                    event_type TEXT NOT NULL,
                    user_id TEXT,
                    ip_address TEXT,
                    user_agent TEXT,
                    details TEXT DEFAULT '{}',
                    timestamp TEXT,
                    severity TEXT DEFAULT 'info',
                    resolved BOOLEAN DEFAULT FALSE
                )
            """,
            "login_attempts": """
                CREATE TABLE IF NOT EXISTS login_attempts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT,
                    ip_address TEXT,
                    success BOOLEAN,
                    timestamp TEXT,
                    user_agent TEXT,
                    failure_reason TEXT
                )
            """,
            "security_policies": """
                CREATE TABLE IF NOT EXISTS security_policies (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    policy_type TEXT NOT NULL,
                    settings TEXT DEFAULT '{}',
                    is_active BOOLEAN DEFAULT TRUE,
                    created_at TEXT,
                    updated_at TEXT
                )
            """,
            "two_factor_tokens": """
                CREATE TABLE IF NOT EXISTS two_factor_tokens (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    secret_key TEXT NOT NULL,
                    backup_codes TEXT DEFAULT '[]',
                    is_enabled BOOLEAN DEFAULT FALSE,
                    created_at TEXT,
                    last_used TEXT
                )
            """,
        }

        for table_name, create_sql in tables.items():
            await self.db.execute(create_sql)

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)",
            "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
            "CREATE INDEX IF NOT EXISTS idx_users_active ON users(is_active)",
            "CREATE INDEX IF NOT EXISTS idx_user_profiles_user_id ON user_profiles(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_security_sessions_user_id ON security_sessions(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_security_sessions_token ON security_sessions(session_token)",
            "CREATE INDEX IF NOT EXISTS idx_api_keys_user_id ON api_keys(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_security_events_type ON security_events(event_type)",
            "CREATE INDEX IF NOT EXISTS idx_security_events_user_id ON security_events(user_id)",
            "CREATE INDEX IF NOT EXISTS idx_security_events_timestamp ON security_events(timestamp)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_ip ON login_attempts(ip_address)",
            "CREATE INDEX IF NOT EXISTS idx_login_attempts_timestamp ON login_attempts(timestamp)",
        ]

        for index_sql in indexes:
            await self.db.execute(index_sql)

    async def _setup_event_handlers(self):
        """Setup event handlers"""
        self.event_bus.subscribe("user.login_attempt", self._handle_login_attempt)
        self.event_bus.subscribe("user.login_success", self._handle_login_success)
        self.event_bus.subscribe("user.login_failure", self._handle_login_failure)
        self.event_bus.subscribe("user.logout", self._handle_logout)
        self.event_bus.subscribe("api.suspicious_activity", self._handle_suspicious_activity)

    async def _initialize_security_policies(self):
        """Initialize default security policies"""
        default_policies = [
            {
                "name": "password_policy",
                "policy_type": "password",
                "settings": {
                    "min_length": 8,
                    "require_uppercase": True,
                    "require_lowercase": True,
                    "require_numbers": True,
                    "require_symbols": True,
                    "max_age_days": 90,
                    "history_count": 5,
                },
            },
            {
                "name": "session_policy",
                "policy_type": "session",
                "settings": {
                    "max_duration_hours": 24,
                    "idle_timeout_minutes": 30,
                    "max_concurrent_sessions": 5,
                },
            },
            {
                "name": "rate_limiting",
                "policy_type": "rate_limit",
                "settings": {
                    "max_login_attempts": 5,
                    "lockout_duration_minutes": 15,
                    "api_calls_per_minute": 100,
                },
            },
        ]

        for policy in default_policies:
            # Check if policy exists
            existing = await self.db.query(
                "SELECT id FROM security_policies WHERE name = ?", [policy["name"]]
            )

            if not existing:
                await self.db.insert(
                    "security_policies",
                    {
                        "id": str(uuid.uuid4()),
                        "name": policy["name"],
                        "policy_type": policy["policy_type"],
                        "settings": str(policy["settings"]),
                        "is_active": True,
                        "created_at": datetime.now().isoformat(),
                        "updated_at": datetime.now().isoformat(),
                    },
                )

    # Authentication methods
    async def authenticate_user(
        self, username: str, password: str, ip_address: str = None
    ) -> Optional[Dict[str, Any]]:
        """Authenticate user with username and password"""
        # Check rate limiting
        if await self._is_rate_limited(username, ip_address):
            await self._log_security_event("rate_limit_exceeded", None, ip_address)
            return None

        # Get user from database
        users = await self.db.query(
            "SELECT * FROM users WHERE username = ? AND is_active = 1", [username]
        )
        if not users:
            await self._log_login_attempt(username, ip_address, False, "user_not_found")
            return None

        user = users[0]

        # Verify password
        if not self.pwd_context.verify(password, user.get("password_hash", "")):
            await self._log_login_attempt(username, ip_address, False, "invalid_password")
            await self._track_failed_login(username, ip_address)
            return None

        # Check if account is locked
        if await self._is_account_locked(user["id"]):
            await self._log_security_event("locked_account_access", user["id"], ip_address)
            return None

        # Successful authentication
        await self._log_login_attempt(username, ip_address, True)
        await self._clear_failed_attempts(username, ip_address)

        return user

    async def create_session(
        self, user_id: str, ip_address: str = None, user_agent: str = None
    ) -> Dict[str, Any]:
        """Create a new user session"""
        session_id = str(uuid.uuid4())
        session_token = secrets.token_urlsafe(32)
        refresh_token = secrets.token_urlsafe(32)

        expires_at = (datetime.now() + timedelta(hours=24)).isoformat()

        session_data = {
            "id": session_id,
            "user_id": user_id,
            "session_token": session_token,
            "refresh_token": refresh_token,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": datetime.now().isoformat(),
            "expires_at": expires_at,
            "last_activity": datetime.now().isoformat(),
            "is_active": True,
        }

        await self.db.insert("security_sessions", session_data)

        # Emit event
        await self.event_bus.emit(
            "security.session.created",
            {"session_id": session_id, "user_id": user_id, "ip_address": ip_address},
        )

        return {
            "session_id": session_id,
            "session_token": session_token,
            "refresh_token": refresh_token,
            "expires_at": expires_at,
        }

    async def validate_session(self, session_token: str) -> Optional[Dict[str, Any]]:
        """Validate and refresh session"""
        sessions = await self.db.query(
            "SELECT * FROM security_sessions WHERE session_token = ? AND is_active = 1",
            [session_token],
        )

        if not sessions:
            return None

        session = sessions[0]

        # Check if expired
        if datetime.fromisoformat(session["expires_at"]) < datetime.now():
            await self.invalidate_session(session["id"])
            return None

        # Update last activity
        await self.db.update(
            "security_sessions", session["id"], {"last_activity": datetime.now().isoformat()}
        )

        return session

    async def invalidate_session(self, session_id: str) -> bool:
        """Invalidate a session"""
        return await self.db.update(
            "security_sessions",
            session_id,
            {"is_active": False, "ended_at": datetime.now().isoformat()},
        )

    async def generate_jwt_token(self, user_id: str, permissions: List[str] = None) -> str:
        """Generate JWT token for API access"""
        payload = {
            "user_id": user_id,
            "permissions": permissions or [],
            "iat": datetime.utcnow(),
            "exp": datetime.utcnow() + timedelta(hours=1),
        }

        return jwt.encode(payload, self.jwt_secret, algorithm="HS256")

    async def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT token"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            await self._log_security_event("expired_token", payload.get("user_id"))
            return None
        except jwt.InvalidTokenError:
            await self._log_security_event("invalid_token")
            return None

    # Event handlers
    async def _handle_login_attempt(self, event_data: Dict[str, Any]):
        """Handle login attempt event"""
        await self._log_security_event(
            "login_attempt",
            event_data.get("user_id"),
            event_data.get("ip_address"),
            {"username": event_data.get("username")},
        )

    async def _handle_login_success(self, event_data: Dict[str, Any]):
        """Handle successful login"""
        await self._log_security_event(
            "login_success", event_data.get("user_id"), event_data.get("ip_address")
        )

    async def _handle_login_failure(self, event_data: Dict[str, Any]):
        """Handle login failure"""
        await self._log_security_event(
            "login_failure",
            event_data.get("user_id"),
            event_data.get("ip_address"),
            {"reason": event_data.get("reason")},
        )

    async def _handle_logout(self, event_data: Dict[str, Any]):
        """Handle logout event"""
        session_token = event_data.get("session_token")
        if session_token:
            sessions = await self.db.query(
                "SELECT id FROM security_sessions WHERE session_token = ?", [session_token]
            )
            if sessions:
                await self.invalidate_session(sessions[0]["id"])

    async def _handle_suspicious_activity(self, event_data: Dict[str, Any]):
        """Handle suspicious activity"""
        await self._log_security_event(
            "suspicious_activity",
            event_data.get("user_id"),
            event_data.get("ip_address"),
            event_data.get("details", {}),
            "warning",
        )

    # Helper methods
    async def _log_security_event(
        self,
        event_type: str,
        user_id: str = None,
        ip_address: str = None,
        details: Dict[str, Any] = None,
        severity: str = "info",
    ):
        """Log security event"""
        event_data = {
            "id": str(uuid.uuid4()),
            "event_type": event_type,
            "user_id": user_id,
            "ip_address": ip_address,
            "details": str(details or {}),
            "timestamp": datetime.now().isoformat(),
            "severity": severity,
            "resolved": False,
        }

        await self.db.insert("security_events", event_data)

        # Emit event for other components
        await self.event_bus.emit("security.event", event_data)

    async def _log_login_attempt(
        self, username: str, ip_address: str, success: bool, failure_reason: str = None
    ):
        """Log login attempt"""
        attempt_data = {
            "username": username,
            "ip_address": ip_address,
            "success": success,
            "timestamp": datetime.now().isoformat(),
            "failure_reason": failure_reason,
        }

        await self.db.insert("login_attempts", attempt_data)

    async def _is_rate_limited(self, username: str, ip_address: str) -> bool:
        """Check if user/IP is rate limited"""
        # Get rate limiting policy
        policy = await self.db.query(
            "SELECT settings FROM security_policies WHERE name = 'rate_limiting' AND is_active = 1"
        )

        if not policy:
            return False

        settings = eval(policy[0]["settings"])  # Note: In production, use json.loads
        max_attempts = settings.get("max_login_attempts", 5)
        lockout_duration = settings.get("lockout_duration_minutes", 15)

        # Check recent failed attempts
        since = (datetime.now() - timedelta(minutes=lockout_duration)).isoformat()

        failed_attempts = await self.db.query(
            """
            SELECT COUNT(*) as count FROM login_attempts
            WHERE (username = ? OR ip_address = ?)
            AND success = 0 AND timestamp > ?
            """,
            [username, ip_address, since],
        )

        return failed_attempts[0]["count"] >= max_attempts

    async def _track_failed_login(self, username: str, ip_address: str):
        """Track failed login attempt"""
        if username not in self.login_attempts:
            self.login_attempts[username] = []

        self.login_attempts[username].append(datetime.now())

        # Clean old attempts
        cutoff = datetime.now() - timedelta(minutes=15)
        self.login_attempts[username] = [dt for dt in self.login_attempts[username] if dt > cutoff]

    async def _clear_failed_attempts(self, username: str, ip_address: str):
        """Clear failed login attempts after successful login"""
        self.login_attempts.pop(username, None)

    async def _is_account_locked(self, user_id: str) -> bool:
        """Check if account is locked"""
        profiles = await self.db.query(
            "SELECT account_locked_until FROM user_profiles WHERE user_id = ?", [user_id]
        )

        if not profiles or not profiles[0]["account_locked_until"]:
            return False

        locked_until = datetime.fromisoformat(profiles[0]["account_locked_until"])
        return datetime.now() < locked_until

    def get_api_routes(self):
        """Get API routes for the plugin"""
        from fastapi import APIRouter, Form, HTTPException, status, Response, Request
        from fastapi.responses import HTMLResponse, RedirectResponse
        from fastapi.templating import Jinja2Templates
        from pydantic import BaseModel
        import os

        router = APIRouter(prefix="/auth", tags=["authentication"])

        # Setup templates
        templates_dir = os.path.join(os.path.dirname(__file__), "templates")
        templates = Jinja2Templates(directory=templates_dir)

        class LoginRequest(BaseModel):
            username: str
            password: str

        class LoginResponse(BaseModel):
            access_token: str
            token_type: str
            user: dict

        @router.get("/login", response_class=HTMLResponse)
        async def login_page(request: Request):
            """Display login page"""
            return templates.TemplateResponse("login.html", {"request": request})

        @router.post("/login", response_model=LoginResponse)
        async def login(username: str = Form(...), password: str = Form(...)):
            """Authenticate user and create session"""
            # Query user from user management plugin
            users = await self.db.query(
                "SELECT * FROM users WHERE username = ? AND is_active = 1", [username.lower()]
            )

            if not users:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
                )

            user = users[0]

            # Verify password directly using bcrypt
            import bcrypt

            stored_password_hash = user.get("password_hash")
            if not stored_password_hash or not bcrypt.checkpw(
                password.encode("utf-8"), stored_password_hash.encode("utf-8")
            ):
                # Log failed attempt
                await self._track_failed_login(username, "127.0.0.1")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password"
                )

            # Create session
            session_data = await self.create_session(user["id"], "127.0.0.1", "web")

            # Generate JWT token
            jwt_token = await self.generate_jwt_token(
                {
                    "user_id": user["id"],
                    "username": user["username"],
                    "session_id": session_data["session_id"],
                }
            )

            # Clear failed attempts
            await self._clear_failed_attempts(username)

            # Log successful login
            await self.event_bus.publish(
                "security.user.login",
                {"user": user, "session_id": session_data["session_id"], "ip_address": "127.0.0.1"},
            )

            return LoginResponse(
                access_token=jwt_token,
                token_type="bearer",
                user={
                    "id": user["id"],
                    "username": user["username"],
                    "email": user["email"],
                    "full_name": f"{user['first_name']} {user['last_name']}",
                },
            )

        @router.post("/logout")
        async def logout(request: Request):
            """Logout user and invalidate session"""
            # Get token from authorization header
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

                # Verify and get session info
                try:
                    payload = await self.verify_jwt_token(token)
                    session_id = payload.get("session_id")
                    user_id = payload.get("user_id")

                    if session_id:
                        await self.invalidate_session(session_id)

                    # Publish logout event
                    await self.event_bus.publish(
                        "security.user.logout", {"user_id": user_id, "session_id": session_id}
                    )

                except Exception:
                    pass  # Invalid token, but still return success

            return {"message": "Logged out successfully"}

        @router.get("/profile")
        async def get_profile(request: Request):
            """Get current user profile"""
            # Get token from authorization header
            auth_header = request.headers.get("authorization")
            if not auth_header or not auth_header.startswith("Bearer "):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required"
                )

            token = auth_header.split(" ")[1]

            try:
                payload = await self.verify_jwt_token(token)
                user_id = payload.get("user_id")

                # Get user details
                users = await self.db.query("SELECT * FROM users WHERE id = ?", [user_id])
                if not users:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
                    )

                user = users[0]
                # Remove sensitive data
                user.pop("password_hash", None)

                return user

            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
                )

        return [router]

    async def _create_default_admin(self):
        """Create default admin user if it doesn't exist"""
        # Check if admin user already exists
        admin_users = await self.db.query("SELECT id FROM users WHERE username = ?", ["admin"])

        if admin_users:
            return  # Admin user already exists

        import bcrypt

        # Create default admin user
        admin_password = "admin"  # In production, this should be generated and logged
        password_hash = bcrypt.hashpw(admin_password.encode("utf-8"), bcrypt.gensalt()).decode(
            "utf-8"
        )

        admin_user_data = {
            "id": str(uuid.uuid4()),
            "username": "admin",
            "email": "admin@nexus.local",
            "first_name": "System",
            "last_name": "Administrator",
            "password_hash": password_hash,
            "is_active": True,
            "is_verified": True,
            "is_superuser": True,
            "profile_image": None,
            "phone": None,
            "department": "IT",
            "job_title": "System Administrator",
            "manager_id": None,
            "metadata": "{}",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "created_by": None,
            "deactivated_at": None,
            "deactivated_by": None,
        }

        await self.db.insert("users", admin_user_data)

        # Create user profile
        profile_data = {
            "user_id": admin_user_data["id"],
            "bio": "System Administrator",
            "avatar": None,
            "timezone": "UTC",
            "language": "en",
            "theme": "light",
            "notifications_enabled": True,
            "email_notifications": True,
            "sms_notifications": False,
            "two_factor_enabled": False,
            "last_login": None,
            "login_count": 0,
            "failed_login_attempts": 0,
            "account_locked_until": None,
            "password_changed_at": None,
            "must_change_password": False,
            "preferences": "{}",
            "social_links": "{}",
            "skills": "[]",
            "certifications": "[]",
        }

        await self.db.insert("user_profiles", profile_data)

        logger.info("Created default admin user (username: admin, password: admin)")

    async def cleanup(self):
        """Cleanup expired sessions and old security events"""
        # Clean expired sessions
        await self.db.execute(
            "DELETE FROM security_sessions WHERE expires_at < ?", [datetime.now().isoformat()]
        )

        # Clean old security events (keep 90 days)
        cutoff = (datetime.now() - timedelta(days=90)).isoformat()
        await self.db.execute(
            "DELETE FROM security_events WHERE timestamp < ? AND resolved = 1", [cutoff]
        )

        logger.info("Security plugin cleanup completed")


# Plugin instance
plugin = SecurityPlugin()


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
