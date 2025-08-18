# User Management API

This section covers the user management endpoints in the Nexus API.

## Overview

The User Management API provides endpoints for managing user accounts, authentication, and authorization within the Nexus platform. These endpoints allow administrators to create, read, update, and delete user accounts, as well as manage user roles and permissions.

## Authentication

All user management endpoints require administrative privileges. Ensure you have the proper authentication token with admin-level access.

## Endpoints

### List Users

```http
GET /api/users
```

Retrieves a list of all users in the system.

#### Parameters

- `page` (optional): Page number for pagination (default: 1)
- `limit` (optional): Number of users per page (default: 20)
- `search` (optional): Search term to filter users by name or email

#### Response

```json
{
  "users": [
    {
      "id": "user-123",
      "username": "johndoe",
      "email": "john@example.com",
      "role": "user",
      "created_at": "2024-01-15T10:30:00Z",
      "last_login": "2024-01-20T14:22:00Z",
      "active": true
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 1,
    "pages": 1
  }
}
```

### Get User

```http
GET /api/users/{user_id}
```

Retrieves detailed information about a specific user.

#### Parameters

- `user_id`: The unique identifier of the user

#### Response

```json
{
  "id": "user-123",
  "username": "johndoe",
  "email": "john@example.com",
  "role": "user",
  "permissions": ["read", "write"],
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-18T09:15:00Z",
  "last_login": "2024-01-20T14:22:00Z",
  "active": true,
  "profile": {
    "first_name": "John",
    "last_name": "Doe",
    "timezone": "UTC"
  }
}
```

### Create User

```http
POST /api/users
```

Creates a new user account.

#### Request Body

```json
{
  "username": "newuser",
  "email": "newuser@example.com",
  "password": "secure_password123",
  "role": "user",
  "profile": {
    "first_name": "New",
    "last_name": "User",
    "timezone": "UTC"
  }
}
```

#### Response

```json
{
  "id": "user-456",
  "username": "newuser",
  "email": "newuser@example.com",
  "role": "user",
  "created_at": "2024-01-21T16:45:00Z",
  "active": true
}
```

### Update User

```http
PUT /api/users/{user_id}
```

Updates an existing user account.

#### Parameters

- `user_id`: The unique identifier of the user

#### Request Body

```json
{
  "email": "updated@example.com",
  "role": "admin",
  "active": false,
  "profile": {
    "first_name": "Updated",
    "last_name": "Name"
  }
}
```

#### Response

```json
{
  "id": "user-123",
  "username": "johndoe",
  "email": "updated@example.com",
  "role": "admin",
  "updated_at": "2024-01-21T17:00:00Z",
  "active": false
}
```

### Delete User

```http
DELETE /api/users/{user_id}
```

Permanently deletes a user account.

#### Parameters

- `user_id`: The unique identifier of the user

#### Response

```json
{
  "message": "User deleted successfully",
  "deleted_at": "2024-01-21T17:30:00Z"
}
```

## User Roles

### Available Roles

- **admin**: Full system access with user management capabilities
- **moderator**: Limited administrative access for content moderation
- **user**: Standard user access with basic permissions
- **readonly**: View-only access to the system

### Role Management

#### Assign Role

```http
POST /api/users/{user_id}/roles
```

Assigns a role to a user.

#### Request Body

```json
{
  "role": "moderator"
}
```

## Permissions

### List User Permissions

```http
GET /api/users/{user_id}/permissions
```

Retrieves the permissions assigned to a specific user.

#### Response

```json
{
  "permissions": [
    "read",
    "write",
    "delete_own",
    "moderate_content"
  ]
}
```

### Update User Permissions

```http
PUT /api/users/{user_id}/permissions
```

Updates the permissions for a specific user.

#### Request Body

```json
{
  "permissions": [
    "read",
    "write",
    "admin_panel"
  ]
}
```

## Error Handling

### Common Error Responses

#### 400 Bad Request

```json
{
  "error": "validation_error",
  "message": "Invalid email format",
  "details": {
    "field": "email",
    "code": "invalid_format"
  }
}
```

#### 401 Unauthorized

```json
{
  "error": "unauthorized",
  "message": "Admin privileges required"
}
```

#### 404 Not Found

```json
{
  "error": "not_found",
  "message": "User not found"
}
```

#### 409 Conflict

```json
{
  "error": "conflict",
  "message": "Username already exists"
}
```

## Rate Limiting

User management endpoints are subject to rate limiting:

- **List users**: 100 requests per minute
- **Create user**: 10 requests per minute
- **Update/Delete user**: 50 requests per minute

## Security Considerations

- All user management operations are logged for audit purposes
- Password changes require additional confirmation
- Account deletions can be configured to be soft deletes for data retention
- Multi-factor authentication settings can be managed through dedicated endpoints

## See Also

- [Authentication API](auth.md)
- [Admin API](admin.md)
- [Core API](core.md)
