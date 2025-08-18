# Authentication API

Complete API reference for authentication and authorization in Nexus.

## 🎯 Overview

The Authentication API provides comprehensive user authentication, authorization, and session management capabilities. It supports multiple authentication methods including JWT tokens, API keys, and OAuth2 integrations.

## 🏗️ Authentication Flow

```mermaid
sequenceDiagram
    participant C as Client
    participant A as Auth API
    participant D as Database
    participant T as Token Service
    participant S as Session Store

    C->>A: POST /auth/login
    A->>D: Validate credentials
    D-->>A: User data
    A->>T: Generate JWT token
    T-->>A: JWT token
    A->>S: Create session
    S-->>A: Session ID
    A-->>C: Login response with token
```

## 🔐 Authentication Endpoints

### Login

Authenticate user with credentials and receive access token.

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "john_doe",
  "password": "secure_password",
  "remember_me": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "123",
      "username": "john_doe",
      "email": "john@example.com",
      "roles": ["user"],
      "permissions": ["read:own", "write:own"]
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 3600
    },
    "session": {
      "session_id": "sess_abc123",
      "expires_at": "2024-01-02T12:00:00Z"
    }
  }
}
```

**Error Response:**
```json
{
  "success": false,
  "error": {
    "code": "INVALID_CREDENTIALS",
    "message": "Invalid username or password",
    "details": {
      "field": "credentials",
      "attempts_remaining": 2
    }
  }
}
```

### Logout

Invalidate current session and tokens.

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Successfully logged out"
}
```

### Token Refresh

Refresh an expired access token using refresh token.

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "Bearer",
    "expires_in": 3600
  }
}
```

### Verify Token

Verify and decode an access token.

```http
GET /api/v1/auth/verify
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "valid": true,
    "user": {
      "id": "123",
      "username": "john_doe",
      "roles": ["user"],
      "permissions": ["read:own", "write:own"]
    },
    "token_info": {
      "issued_at": "2024-01-01T12:00:00Z",
      "expires_at": "2024-01-01T13:00:00Z",
      "remaining_seconds": 2400
    }
  }
}
```

## 👤 User Management

### Get Current User

Get current authenticated user information.

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "123",
      "username": "john_doe",
      "email": "john@example.com",
      "full_name": "John Doe",
      "roles": ["user"],
      "permissions": ["read:own", "write:own"],
      "profile": {
        "avatar_url": "https://example.com/avatars/john.jpg",
        "bio": "Software developer",
        "location": "San Francisco, CA"
      },
      "preferences": {
        "theme": "dark",
        "language": "en",
        "notifications": true
      },
      "metadata": {
        "last_login": "2024-01-01T12:00:00Z",
        "login_count": 42,
        "created_at": "2023-01-01T00:00:00Z",
        "updated_at": "2024-01-01T11:30:00Z"
      }
    }
  }
}
```

### Update Profile

Update current user's profile information.

```http
PUT /api/v1/auth/profile
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "full_name": "John Smith",
  "bio": "Senior Software Developer",
  "location": "New York, NY",
  "preferences": {
    "theme": "light",
    "notifications": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "123",
      "username": "john_doe",
      "email": "john@example.com",
      "full_name": "John Smith",
      "profile": {
        "bio": "Senior Software Developer",
        "location": "New York, NY"
      },
      "preferences": {
        "theme": "light",
        "language": "en",
        "notifications": false
      },
      "updated_at": "2024-01-01T12:30:00Z"
    }
  }
}
```

### Change Password

Change current user's password.

```http
PUT /api/v1/auth/password
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "current_password": "old_password",
  "new_password": "new_secure_password",
  "confirm_password": "new_secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password changed successfully"
}
```

## 🔑 API Key Management

### List API Keys

Get list of API keys for current user.

```http
GET /api/v1/auth/api-keys
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "api_keys": [
      {
        "id": "key_123",
        "name": "Production API Key",
        "key_preview": "nx_************************************abcd",
        "permissions": ["read:data", "write:data"],
        "last_used": "2024-01-01T11:30:00Z",
        "created_at": "2023-12-01T10:00:00Z",
        "expires_at": "2024-12-01T10:00:00Z",
        "is_active": true
      },
      {
        "id": "key_456",
        "name": "Development Key",
        "key_preview": "nx_************************************efgh",
        "permissions": ["read:data"],
        "last_used": "2023-12-15T14:20:00Z",
        "created_at": "2023-11-01T09:00:00Z",
        "expires_at": "2024-11-01T09:00:00Z",
        "is_active": true
      }
    ]
  }
}
```

### Create API Key

Create a new API key.

```http
POST /api/v1/auth/api-keys
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "New API Key",
  "permissions": ["read:data", "write:data"],
  "expires_in_days": 365,
  "description": "API key for production integration"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "api_key": {
      "id": "key_789",
      "name": "New API Key",
      "key": "nx_1234567890abcdef1234567890abcdef12345678",
      "permissions": ["read:data", "write:data"],
      "created_at": "2024-01-01T12:00:00Z",
      "expires_at": "2025-01-01T12:00:00Z",
      "is_active": true
    },
    "warning": "This is the only time you'll see the full API key. Store it securely."
  }
}
```

### Revoke API Key

Revoke an existing API key.

```http
DELETE /api/v1/auth/api-keys/{key_id}
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "API key revoked successfully"
}
```

## 🔐 OAuth2 Integration

### OAuth2 Authorization

Initiate OAuth2 authorization flow.

```http
GET /api/v1/auth/oauth2/{provider}/authorize?redirect_uri={redirect_uri}&state={state}
```

**Supported Providers:**
- `google`
- `github`
- `microsoft`
- `linkedin`

**Response:**
Redirects to OAuth2 provider authorization URL.

### OAuth2 Callback

Handle OAuth2 callback and exchange code for tokens.

```http
POST /api/v1/auth/oauth2/{provider}/callback
Content-Type: application/json

{
  "code": "authorization_code",
  "state": "csrf_token",
  "redirect_uri": "https://yourdomain.com/callback"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "456",
      "username": "jane_doe",
      "email": "jane@example.com",
      "provider": "google",
      "provider_id": "google_123456789"
    },
    "tokens": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "Bearer",
      "expires_in": 3600
    },
    "is_new_user": false
  }
}
```

## 👥 User Registration

### Register User

Register a new user account.

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "username": "new_user",
  "email": "newuser@example.com",
  "password": "secure_password",
  "full_name": "New User",
  "terms_accepted": true,
  "newsletter_opt_in": false
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "user": {
      "id": "789",
      "username": "new_user",
      "email": "newuser@example.com",
      "full_name": "New User",
      "roles": ["user"],
      "email_verified": false,
      "created_at": "2024-01-01T12:00:00Z"
    },
    "message": "Registration successful. Please check your email for verification."
  }
}
```

### Verify Email

Verify user email address.

```http
POST /api/v1/auth/verify-email
Content-Type: application/json

{
  "token": "email_verification_token"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Email verified successfully"
}
```

### Resend Verification

Resend email verification token.

```http
POST /api/v1/auth/resend-verification
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Verification email sent"
}
```

## 🔄 Password Reset

### Request Password Reset

Request password reset email.

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "user@example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "If the email exists, a password reset link has been sent"
}
```

### Reset Password

Reset password using reset token.

```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "password_reset_token",
  "new_password": "new_secure_password",
  "confirm_password": "new_secure_password"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Password reset successfully"
}
```

## 🛡️ Two-Factor Authentication

### Enable 2FA

Enable two-factor authentication.

```http
POST /api/v1/auth/2fa/enable
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
    "secret": "JBSWY3DPEHPK3PXP",
    "backup_codes": [
      "12345678",
      "23456789",
      "34567890",
      "45678901",
      "56789012"
    ]
  }
}
```

### Verify 2FA Setup

Verify 2FA setup with TOTP code.

```http
POST /api/v1/auth/2fa/verify
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "2FA enabled successfully"
}
```

### Disable 2FA

Disable two-factor authentication.

```http
DELETE /api/v1/auth/2fa
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "password": "current_password",
  "totp_code": "123456"
}
```

**Response:**
```json
{
  "success": true,
  "message": "2FA disabled successfully"
}
```

## 📱 Session Management

### List Active Sessions

Get list of active user sessions.

```http
GET /api/v1/auth/sessions
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "sess_123",
        "device": "Chrome on Windows",
        "ip_address": "192.168.1.100",
        "location": "San Francisco, CA",
        "last_activity": "2024-01-01T12:00:00Z",
        "created_at": "2024-01-01T10:00:00Z",
        "is_current": true
      },
      {
        "id": "sess_456",
        "device": "Safari on iPhone",
        "ip_address": "192.168.1.101",
        "location": "San Francisco, CA",
        "last_activity": "2024-01-01T11:30:00Z",
        "created_at": "2024-01-01T09:00:00Z",
        "is_current": false
      }
    ]
  }
}
```

### Revoke Session

Revoke a specific session.

```http
DELETE /api/v1/auth/sessions/{session_id}
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "Session revoked successfully"
}
```

### Revoke All Sessions

Revoke all sessions except current.

```http
DELETE /api/v1/auth/sessions
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "message": "All other sessions revoked successfully"
}
```

## 🔍 Authorization

### Check Permissions

Check if current user has specific permissions.

```http
POST /api/v1/auth/check-permissions
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "permissions": ["read:users", "write:posts", "admin:system"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "permissions": {
      "read:users": true,
      "write:posts": true,
      "admin:system": false
    },
    "has_all": false
  }
}
```

### Get User Roles

Get current user's roles and permissions.

```http
GET /api/v1/auth/roles
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "success": true,
  "data": {
    "roles": [
      {
        "name": "user",
        "description": "Standard user role",
        "permissions": ["read:own", "write:own"]
      },
      {
        "name": "moderator",
        "description": "Content moderator role",
        "permissions": ["read:all", "write:all", "moderate:content"]
      }
    ],
    "all_permissions": [
      "read:own",
      "write:own",
      "read:all",
      "write:all",
      "moderate:content"
    ]
  }
}
```

## 🚨 Error Codes

### Authentication Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | Invalid username or password |
| `ACCOUNT_LOCKED` | 423 | Account is locked due to too many failed attempts |
| `ACCOUNT_DISABLED` | 403 | Account has been disabled |
| `EMAIL_NOT_VERIFIED` | 403 | Email address not verified |
| `TOKEN_EXPIRED` | 401 | Access token has expired |
| `TOKEN_INVALID` | 401 | Invalid or malformed token |
| `REFRESH_TOKEN_EXPIRED` | 401 | Refresh token has expired |
| `SESSION_EXPIRED` | 401 | Session has expired |
| `TWO_FACTOR_REQUIRED` | 401 | Two-factor authentication required |
| `INVALID_2FA_CODE` | 401 | Invalid 2FA code |

### Registration Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `USERNAME_TAKEN` | 409 | Username already exists |
| `EMAIL_TAKEN` | 409 | Email already registered |
| `WEAK_PASSWORD` | 400 | Password doesn't meet requirements |
| `INVALID_EMAIL` | 400 | Invalid email format |
| `TERMS_NOT_ACCEPTED` | 400 | Terms and conditions not accepted |

### Authorization Errors

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `ROLE_NOT_FOUND` | 404 | Specified role does not exist |
| `PERMISSION_DENIED` | 403 | Access denied for this resource |

## 📝 Request/Response Examples

### Complete Login Flow

```bash
# 1. Login
curl -X POST "https://api.nexus.dev/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "password": "secure_password"
  }'

# Response includes access_token and refresh_token

# 2. Use access token for API calls
curl -X GET "https://api.nexus.dev/v1/auth/me" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."

# 3. Refresh token when expired
curl -X POST "https://api.nexus.dev/v1/auth/refresh" \
  -H "Content-Type: application/json" \
  -d '{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }'

# 4. Logout
curl -X POST "https://api.nexus.dev/v1/auth/logout" \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### OAuth2 Flow

```bash
# 1. Get authorization URL
curl -X GET "https://api.nexus.dev/v1/auth/oauth2/google/authorize?redirect_uri=https://yourdomain.com/callback&state=random_state"

# 2. User authorizes on Google and returns with code

# 3. Exchange code for tokens
curl -X POST "https://api.nexus.dev/v1/auth/oauth2/google/callback" \
  -H "Content-Type: application/json" \
  -d '{
    "code": "authorization_code_from_google",
    "state": "random_state",
    "redirect_uri": "https://yourdomain.com/callback"
  }'
```

## 🎯 Best Practices

### Security Guidelines

1. **Always use HTTPS** in production
2. **Store tokens securely** (httpOnly cookies or secure storage)
3. **Implement token refresh** before expiration
4. **Use appropriate token lifetimes** (short access tokens, longer refresh tokens)
5. **Validate tokens on every request**
6. **Implement rate limiting** on authentication endpoints
7. **Use strong password policies**
8. **Enable 2FA for sensitive accounts**

### Error Handling

1. **Don't expose sensitive information** in error messages
2. **Use consistent error formats**
3. **Log authentication events** for security monitoring
4. **Implement account lockout** after failed attempts
5. **Provide clear user feedback** for authentication issues

## 🔗 Related APIs

- **[User Management API](users.md)** - User CRUD operations
- **[Admin API](admin.md)** - Administrative functions
- **[Core API](core.md)** - System information and health checks

---

**The Authentication API is the foundation of secure access to Nexus.** Implement proper authentication flows and security measures to protect your application and users.
