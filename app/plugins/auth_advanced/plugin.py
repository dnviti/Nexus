"""
Advanced Authentication Plugin for Nexus Framework

Comprehensive authentication and authorization system featuring:
- JWT-based authentication
- Role-based access control (RBAC)
- OAuth2 integration
- Multi-factor authentication (MFA)
- API key management
- Session management
- Password policies
- Account lockout protection
"""

import asyncio
import logging
import secrets
import hashlib
import base64
from typing import Optional, List, Dict, Any, Set
from datetime import datetime, timedelta
from enum import Enum
import uuid
import pyotp
import qrcode
from io import BytesIO

from fastapi import APIRouter, HTTPException, Depends, Security, status, Request, Response
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm, APIKeyHeader, HTTPBearer
from pydantic import BaseModel, Field, EmailStr, validator
import jwt
import bcrypt
from sqlalchemy import Column, String, Text, DateTime, Boolean, Integer, JSON, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, relationship

from nexus.plugins import BasePlugin, PluginMetadata, PluginLifecycle
from nexus.core import Event, EventPriority
from nexus.database import get_db

logger = logging.getLogger(__name__)

# Database Models
Base = declarative_base()

# Security schemes
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    """User role types."""
    ADMIN = "admin"
    MODERATOR = "moderator"
    USER = "user"
    GUEST = "guest"


class AuthProvider(str, Enum):
    """Authentication providers."""
    LOCAL = "local"
    GOOGLE = "google"
    GITHUB = "github"
    MICROSOFT = "microsoft"
    FACEBOOK = "facebook"


class TokenType(str, Enum):
    """Token types."""
    ACCESS = "access"
    REFRESH = "refresh"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"
    API_KEY = "api_key"


# SQLAlchemy Models
class UserModel(Base):
    """User database model."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Nullable for OAuth users
    full_name = Column(String(255), nullable=True)

    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    is_locked = Column(Boolean, default=False)

    # Roles and permissions
    roles = Column(JSON, default=lambda: ["user"])
    permissions = Column(JSON, default=list)

    # Multi-factor authentication
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(32), nullable=True)
    backup_codes = Column(JSON, nullable=True)

    # OAuth providers
    auth_provider = Column(String(20), default="local")
    provider_id = Column(String(255), nullable=True)

    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    last_failed_login = Column(DateTime, nullable=True)
    locked_until = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)
    last_password_change = Column(DateTime, nullable=True)

    # Profile
    avatar_url = Column(String(500), nullable=True)
    bio = Column(Text, nullable=True)
    metadata = Column(JSON, default=dict)

    # Relationships
    sessions = relationship("SessionModel", back_populates="user", cascade="all, delete-orphan")
    api_keys = relationship("APIKeyModel", back_populates="user", cascade="all, delete-orphan")


class SessionModel(Base):
    """User session model."""
    __tablename__ = "sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False, index=True)
    refresh_token_hash = Column(String(64), unique=True, nullable=True)

    # Session info
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(JSON, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    last_activity = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    # Relationship
    user = relationship("UserModel", back_populates="sessions")


class APIKeyModel(Base):
    """API key model."""
    __tablename__ = "api_keys"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False)
    key_hash = Column(String(64), unique=True, nullable=False, index=True)
    prefix = Column(String(10), nullable=False)  # For display: "sk_live_..."

    name = Column(String(100), nullable=False)
    description = Column(String(500), nullable=True)
    permissions = Column(JSON, default=list)

    # Usage tracking
    last_used = Column(DateTime, nullable=True)
    usage_count = Column(Integer, default=0)

    # Validity
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    user = relationship("UserModel", back_populates="api_keys")


# Pydantic Models
class UserRegister(BaseModel):
    """User registration schema."""
    username: str = Field(..., min_length=3, max_length=50, regex="^[a-zA-Z0-9_-]+$")
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: Optional[str] = Field(None, max_length=255)

    @validator("password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain at least one digit")
        if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in v):
            raise ValueError("Password must contain at least one special character")
        return v


class UserLogin(BaseModel):
    """User login schema."""
    username: str  # Can be username or email
    password: str
    remember_me: bool = False


class User(BaseModel):
    """User response schema."""
    id: str
    username: str
    email: str
    full_name: Optional[str]
    roles: List[str]
    permissions: List[str]
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    auth_provider: str
    created_at: datetime
    last_login: Optional[datetime]
    avatar_url: Optional[str]
    bio: Optional[str]

    class Config:
        orm_mode = True


class Token(BaseModel):
    """Token response schema."""
    access_token: str
    refresh_token: Optional[str]
    token_type: str = "bearer"
    expires_in: int
    user: Optional[User] = None


class PasswordReset(BaseModel):
    """Password reset request."""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation."""
    token: str
    new_password: str

    @validator("new_password")
    def validate_password(cls, v):
        """Validate password strength."""
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v


class MFASetup(BaseModel):
    """MFA setup response."""
    secret: str
    qr_code: str
    backup_codes: List[str]


class MFAVerify(BaseModel):
    """MFA verification request."""
    code: str


class APIKeyCreate(BaseModel):
    """API key creation request."""
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    permissions: List[str] = []
    expires_in_days: Optional[int] = Field(None, ge=1, le=365)


class APIKey(BaseModel):
    """API key response."""
    id: str
    prefix: str
    name: str
    description: Optional[str]
    permissions: List[str]
    created_at: datetime
    expires_at: Optional[datetime]
    last_used: Optional[datetime]
    usage_count: int

    class Config:
        orm_mode = True


# Service Classes
class PasswordHasher:
    """Password hashing utility."""

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

    @staticmethod
    def verify_password(password: str, hashed: str) -> bool:
        """Verify a password against its hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


class TokenManager:
    """JWT token management."""

    def __init__(self, secret_key: str, algorithm: str = "HS256"):
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.access_token_expire = timedelta(hours=1)
        self.refresh_token_expire = timedelta(days=7)

    def create_token(self, data: Dict[str, Any], token_type: TokenType, expires_delta: Optional[timedelta] = None) -> str:
        """Create a JWT token."""
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            if token_type == TokenType.ACCESS:
                expire = datetime.utcnow() + self.access_token_expire
            elif token_type == TokenType.REFRESH:
                expire = datetime.utcnow() + self.refresh_token_expire
            else:
                expire = datetime.utcnow() + timedelta(hours=1)

        to_encode.update({
            "exp": expire,
            "iat": datetime.utcnow(),
            "type": token_type.value,
            "jti": str(uuid.uuid4())  # JWT ID for token revocation
        })

        return jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)

    def decode_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Decode and validate a JWT token."""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            return None
        except jwt.JWTError as e:
            logger.warning(f"Invalid token: {e}")
            return None


class MFAManager:
    """Multi-factor authentication manager."""

    @staticmethod
    def generate_secret() -> str:
        """Generate a new TOTP secret."""
        return pyotp.random_base32()

    @staticmethod
    def generate_qr_code(username: str, secret: str, issuer: str = "Nexus") -> str:
        """Generate QR code for TOTP setup."""
        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name=issuer
        )

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(totp_uri)
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')

        # Convert to base64 for embedding in response
        return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

    @staticmethod
    def verify_code(secret: str, code: str) -> bool:
        """Verify a TOTP code."""
        totp = pyotp.TOTP(secret)
        return totp.verify(code, valid_window=1)  # Allow 30 second window

    @staticmethod
    def generate_backup_codes(count: int = 10) -> List[str]:
        """Generate backup codes."""
        return [secrets.token_hex(4).upper() for _ in range(count)]


# Main Plugin Class
class AuthAdvancedPlugin(BasePlugin):
    """
    Advanced Authentication Plugin for Nexus Framework.

    Provides comprehensive authentication and authorization including:
    - User registration and login
    - JWT token management
    - Role-based access control
    - Multi-factor authentication
    - OAuth2 integration
    - API key management
    - Session management
    - Account security features
    """

    def __init__(self):
        super().__init__()
        self.metadata = PluginMetadata(
            name="auth_advanced",
            version="2.0.0",
            description="Advanced authentication and authorization system",
            author="Nexus Team",
            category="security",
            tags=["auth", "security", "jwt", "oauth", "mfa"],
            dependencies=["database"],
            permissions=[
                "auth.register",
                "auth.login",
                "auth.admin",
                "user.read",
                "user.write",
                "user.delete"
            ],
            config_schema={
                "jwt_secret": {"type": "string", "required": True},
                "jwt_algorithm": {"type": "string", "default": "HS256"},
                "enable_registration": {"type": "boolean", "default": True},
                "enable_mfa": {"type": "boolean", "default": True},
                "enable_oauth": {"type": "boolean", "default": False},
                "max_login_attempts": {"type": "integer", "default": 5},
                "lockout_duration": {"type": "integer", "default": 900},
                "password_reset_expire": {"type": "integer", "default": 3600},
                "require_email_verification": {"type": "boolean", "default": True}
            }
        )

        self.db = None
        self.event_bus = None
        self.config = {}
        self.token_manager = None
        self.mfa_manager = MFAManager()
        self.password_hasher = PasswordHasher()

        # Cache for revoked tokens
        self.revoked_tokens: Set[str] = set()

    async def initialize(self, context) -> bool:
        """Initialize the plugin."""
        try:
            logger.info(f"Initializing {self.metadata.name} plugin v{self.metadata.version}")

            # Get dependencies
            self.db = context.get_service("database")
            self.event_bus = context.get_service("event_bus")

            if not self.db:
                logger.error("Database service not available")
                return False

            # Load configuration
            self.config = context.get_config(self.metadata.name, {})

            # Initialize token manager
            jwt_secret = self.config.get("jwt_secret", "change-me-in-production")
            jwt_algorithm = self.config.get("jwt_algorithm", "HS256")
            self.token_manager = TokenManager(jwt_secret, jwt_algorithm)

            # Create database tables
            await self._create_tables()

            # Create default admin user if needed
            await self._ensure_admin_user()

            # Register services
            context.register_service(f"{self.metadata.name}.token_manager", self.token_manager)
            context.register_service(f"{self.metadata.name}.mfa_manager", self.mfa_manager)

            logger.info(f"{self.metadata.name} plugin initialized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize {self.metadata.name}: {e}", exc_info=True)
            return False

    async def _create_tables(self):
        """Create database tables."""
        # This would use the database adapter to create tables
        # Base.metadata.create_all(bind=self.db.engine)
        pass

    async def _ensure_admin_user(self):
        """Ensure default admin user exists."""
        # Check if any admin exists
        # If not, create default admin with temporary password
        pass

    def get_api_routes(self) -> List[APIRouter]:
        """Define API routes for the plugin."""
        router = APIRouter(prefix="/api/auth", tags=["Authentication"])

        # Dependency functions
        async def get_current_user(
            token: str = Depends(oauth2_scheme),
            db: Session = Depends(get_db)
        ) -> UserModel:
            """Get current authenticated user."""
            payload = self.token_manager.decode_token(token)
            if not payload:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired token",
                    headers={"WWW-Authenticate": "Bearer"}
                )

            # Check if token is revoked
            jti = payload.get("jti")
            if jti in self.revoked_tokens:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked"
                )

            user_id = payload.get("sub")
            user = db.query(UserModel).filter(UserModel.id == user_id).first()

            if not user or not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found or inactive"
                )

            return user

        async def require_role(role: UserRole):
            """Require specific role."""
            async def role_checker(user: UserModel = Depends(get_current_user)):
                if role.value not in user.roles:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Role {role.value} required"
                    )
                return user
            return role_checker

        # Routes
        @router.post("/register", response_model=User, status_code=status.HTTP_201_CREATED)
        async def register(
            user_data: UserRegister,
            request: Request,
            db: Session = Depends(get_db)
        ):
            """Register a new user."""
            if not self.config.get("enable_registration", True):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Registration is disabled"
                )

            # Check if user exists
            existing = db.query(UserModel).filter(
                (UserModel.username == user_data.username) |
                (UserModel.email == user_data.email)
            ).first()

            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username or email already registered"
                )

            # Create user
            user = UserModel(
                username=user_data.username,
                email=user_data.email,
                password_hash=self.password_hasher.hash_password(user_data.password),
                full_name=user_data.full_name,
                is_verified=not self.config.get("require_email_verification", True)
            )

            db.add(user)
            db.commit()
            db.refresh(user)

            # Send verification email if required
            if self.config.get("require_email_verification", True):
                await self._send_verification_email(user)

            # Publish event
            await self.event_bus.publish(Event(
                type="user.registered",
                data={
                    "user_id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            ))

            logger.info(f"User registered: {user.username}")
            return User.from_orm(user)

        @router.post("/login", response_model=Token)
        async def login(
            form_data: OAuth2PasswordRequestForm = Depends(),
            request: Request = None,
            db: Session = Depends(get_db)
        ):
            """Login and get access token."""
            # Find user by username or email
            user = db.query(UserModel).filter(
                (UserModel.username == form_data.username) |
                (UserModel.email == form_data.username)
            ).first()

            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Check if account is locked
            if user.is_locked and user.locked_until:
                if user.locked_until > datetime.utcnow():
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Account locked until {user.locked_until}"
                    )
                else:
                    # Unlock account
                    user.is_locked = False
                    user.locked_until = None
                    user.failed_login_attempts = 0

            # Verify password
            if not self.password_hasher.verify_password(form_data.password, user.password_hash):
                # Track failed attempt
                user.failed_login_attempts += 1
                user.last_failed_login = datetime.utcnow()

                # Lock account if too many attempts
                max_attempts = self.config.get("max_login_attempts", 5)
                if user.failed_login_attempts >= max_attempts:
                    lockout_duration = self.config.get("lockout_duration", 900)
                    user.is_locked = True
                    user.locked_until = datetime.utcnow() + timedelta(seconds=lockout_duration)
                    logger.warning(f"Account locked for user {user.username}")

                db.commit()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials"
                )

            # Check if email verification required
            if self.config.get("require_email_verification", True) and not user.is_verified:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Email verification required"
                )

            # Reset failed attempts
            user.failed_login_attempts = 0
            user.last_login = datetime.utcnow()

            # Create tokens
            access_token = self.token_manager.create_token(
                {"sub": user.id, "username": user.username},
                TokenType.ACCESS
            )
            refresh_token = self.token_manager.create_token(
                {"sub": user.id},
                TokenType.REFRESH
            )

            # Create session
            session = SessionModel(
                user_id=user.id,
                token_hash=hashlib.sha256(access_token.encode()).hexdigest(),
                refresh_token_hash=hashlib.sha256(refresh_token.encode()).hexdigest(),
                ip_address=request.client.host if request else None,
                user_agent=request.headers.get("User-Agent") if request else None,
                expires_at=datetime.utcnow() + self.token_manager.access_token_expire
            )
            db.add(session)
            db.commit()

            logger.info(f"User logged in: {user.username}")

            return Token(
                access_token=access_token,
                refresh_token=refresh_token,
                expires_in=3600,
                user=User.from_orm(user)
            )

        @router.post("/logout")
        async def logout(
            user: UserModel = Depends(get_current_user),
            token: str = Depends(oauth2_scheme),
            db: Session = Depends(get_db)
        ):
            """Logout and revoke token."""
            # Revoke token
            payload = self.token_manager.decode_token(token)
            if payload:
                jti = payload.get("jti")
                if jti:
                    self.revoked_tokens.add(jti)

            # Delete session
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            session = db.query(SessionModel).filter(
                SessionModel.token_hash == token_hash
            ).first()
            if session:
                db.delete(session)
                db.commit()

            logger.info(f"User logged out: {user.username}")
            return {"message": "Successfully logged out"}

        @router.get("/me", response_model=User)
        async def get_current_user_info(user: UserModel = Depends(get_current_user)):
            """Get current user information."""
            return User.from_orm(user)

        @router.put("/me", response_model=User)
        async def update_profile(
            updates: Dict[str, Any],
            user: UserModel = Depends(get_current_user),
            db: Session = Depends(get_db)
        ):
            """Update user profile."""
            allowed_fields = ["full_name", "bio", "avatar_url"]

            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(user, field, value)

            user.updated_at = datetime.utcnow()
            db.commit()
            db.refresh(user)

            return User.from_orm(user)

        return [router]

    async def _send_verification_email(self, user: UserModel):
        """Send email verification."""
        token = self.token_manager.create_token(
            {"sub": user.id, "email": user.email},
            TokenType.EMAIL_VERIFICATION,
            expires_delta=timedelta(hours=24)
        )

        await self.event_bus.publish(Event(
            type="email.send",
            data={
                "to": user.email,
                "subject": "Verify your email",
                "template": "email_verification",
                "context": {
                    "username": user.username,
                    "verification_link": f"https://example.com/verify?token={token}"
                }
            }
        ))
