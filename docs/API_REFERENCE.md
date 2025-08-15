# Nexus Framework API Reference

## Table of Contents
- [Overview](#overview)
- [Authentication](#authentication)
- [Core Endpoints](#core-endpoints)
- [Plugin Management](#plugin-management)
- [User Management](#user-management)
- [Database Operations](#database-operations)
- [WebSocket API](#websocket-api)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [API Versioning](#api-versioning)

## Overview

The Nexus Framework provides a comprehensive RESTful API with automatic documentation generation via OpenAPI/Swagger. All API endpoints are automatically discovered from loaded plugins and exposed through a unified gateway.

### Base URL
```
http://localhost:8000/api
```

### Content Type
All requests and responses use JSON:
```
Content-Type: application/json
```

### API Documentation
Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Schema: `http://localhost:8000/openapi.json`

## Authentication

### JWT Authentication

#### Login
```http
POST /api/auth/login
```

**Request Body:**
```json
{
  "username": "user@example.com",
  "password": "secure_password"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "user@example.com",
    "roles": ["user", "admin"]
  }
}
```

#### Refresh Token
```http
POST /api/auth/refresh
```

**Request Body:**
```json
{
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "token_type": "bearer",
  "expires_in": 3600
}
```

#### Logout
```http
POST /api/auth/logout
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

### API Key Authentication

#### Create API Key
```http
POST /api/auth/api-keys
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "Production API Key",
  "expires_at": "2024-12-31T23:59:59Z",
  "scopes": ["read", "write"]
}
```

**Response:**
```json
{
  "id": "ak_live_xxxxxxxxxxx",
  "key": "sk_live_xxxxxxxxxxx",
  "name": "Production API Key",
  "created_at": "2024-01-01T00:00:00Z",
  "expires_at": "2024-12-31T23:59:59Z",
  "scopes": ["read", "write"]
}
```

**Using API Key:**
```http
GET /api/resource
X-API-Key: sk_live_xxxxxxxxxxx
```

## Core Endpoints

### Health Check
```http
GET /api/health
```

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z",
  "services": {
    "database": "connected",
    "cache": "connected",
    "plugins": "loaded"
  }
}
```

### System Information
```http
GET /api/system/info
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "framework_version": "2.0.0",
  "python_version": "3.11.0",
  "platform": "linux",
  "loaded_plugins": 12,
  "active_sessions": 45,
  "uptime_seconds": 3600,
  "memory_usage_mb": 256,
  "cpu_usage_percent": 15.5
}
```

### Configuration
```http
GET /api/system/config
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "app_name": "My Nexus App",
  "environment": "production",
  "debug": false,
  "database": {
    "type": "postgresql",
    "host": "localhost",
    "port": 5432
  },
  "cache": {
    "type": "redis",
    "host": "localhost",
    "port": 6379
  }
}
```

## Plugin Management

### List Plugins
```http
GET /api/plugins
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `category` (string): Filter by category
- `status` (string): Filter by status (active, inactive, error)
- `page` (integer): Page number (default: 1)
- `limit` (integer): Items per page (default: 20)

**Response:**
```json
{
  "total": 25,
  "page": 1,
  "limit": 20,
  "plugins": [
    {
      "id": "auth_advanced",
      "name": "Advanced Authentication",
      "category": "security",
      "version": "1.2.0",
      "status": "active",
      "description": "Advanced authentication features",
      "author": "Nexus Team",
      "dependencies": ["core_auth"],
      "api_endpoints": [
        "/api/auth/mfa",
        "/api/auth/oauth"
      ],
      "enabled": true,
      "config": {
        "mfa_enabled": true,
        "oauth_providers": ["google", "github"]
      }
    }
  ]
}
```

### Get Plugin Details
```http
GET /api/plugins/{plugin_id}
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "auth_advanced",
  "name": "Advanced Authentication",
  "category": "security",
  "version": "1.2.0",
  "status": "active",
  "description": "Advanced authentication features including MFA and OAuth",
  "author": "Nexus Team",
  "license": "MIT",
  "repository": "https://github.com/nexus/auth-advanced",
  "dependencies": {
    "core_auth": ">=1.0.0",
    "crypto_utils": ">=2.0.0"
  },
  "permissions": ["user.read", "user.write", "auth.admin"],
  "api_endpoints": [
    {
      "path": "/api/auth/mfa/enable",
      "method": "POST",
      "description": "Enable MFA for user"
    },
    {
      "path": "/api/auth/oauth/{provider}",
      "method": "GET",
      "description": "OAuth authentication"
    }
  ],
  "configuration": {
    "mfa_enabled": true,
    "oauth_providers": ["google", "github"],
    "session_timeout": 3600
  },
  "metrics": {
    "total_requests": 15234,
    "average_response_time_ms": 45,
    "error_rate": 0.02
  }
}
```

### Install Plugin
```http
POST /api/plugins/install
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "source": "registry",
  "package": "nexus-plugin-analytics",
  "version": "2.1.0"
}
```

**Alternative for file upload:**
```http
POST /api/plugins/install
Authorization: Bearer {access_token}
Content-Type: multipart/form-data
```

**Response:**
```json
{
  "status": "success",
  "plugin": {
    "id": "analytics_dashboard",
    "name": "Analytics Dashboard",
    "version": "2.1.0",
    "status": "active"
  },
  "message": "Plugin installed successfully"
}
```

### Enable/Disable Plugin
```http
PUT /api/plugins/{plugin_id}/status
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "enabled": false,
  "reason": "Maintenance"
}
```

**Response:**
```json
{
  "plugin_id": "analytics_dashboard",
  "enabled": false,
  "status": "inactive",
  "message": "Plugin disabled successfully"
}
```

### Update Plugin Configuration
```http
PUT /api/plugins/{plugin_id}/config
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "config": {
    "api_rate_limit": 1000,
    "cache_ttl": 3600,
    "features": {
      "real_time": true,
      "export": true
    }
  }
}
```

**Response:**
```json
{
  "plugin_id": "analytics_dashboard",
  "config": {
    "api_rate_limit": 1000,
    "cache_ttl": 3600,
    "features": {
      "real_time": true,
      "export": true
    }
  },
  "message": "Configuration updated successfully"
}
```

### Uninstall Plugin
```http
DELETE /api/plugins/{plugin_id}
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "plugin_id": "analytics_dashboard",
  "status": "uninstalled",
  "message": "Plugin uninstalled successfully"
}
```

## User Management

### List Users
```http
GET /api/users
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `role` (string): Filter by role
- `status` (string): Filter by status (active, inactive, suspended)
- `search` (string): Search in username and email
- `page` (integer): Page number
- `limit` (integer): Items per page

**Response:**
```json
{
  "total": 150,
  "page": 1,
  "limit": 20,
  "users": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "john.doe",
      "email": "john.doe@example.com",
      "full_name": "John Doe",
      "roles": ["user", "editor"],
      "status": "active",
      "created_at": "2024-01-01T00:00:00Z",
      "last_login": "2024-01-15T10:30:00Z"
    }
  ]
}
```

### Get User
```http
GET /api/users/{user_id}
Authorization: Bearer {access_token}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "username": "john.doe",
  "email": "john.doe@example.com",
  "full_name": "John Doe",
  "roles": ["user", "editor"],
  "permissions": [
    "content.read",
    "content.write",
    "content.publish"
  ],
  "status": "active",
  "metadata": {
    "department": "Engineering",
    "location": "New York"
  },
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-10T15:00:00Z",
  "last_login": "2024-01-15T10:30:00Z"
}
```

### Create User
```http
POST /api/users
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "username": "jane.smith",
  "email": "jane.smith@example.com",
  "password": "SecurePassword123!",
  "full_name": "Jane Smith",
  "roles": ["user"],
  "metadata": {
    "department": "Marketing",
    "location": "London"
  }
}
```

**Response:**
```json
{
  "id": "660e8400-e29b-41d4-a716-446655440001",
  "username": "jane.smith",
  "email": "jane.smith@example.com",
  "full_name": "Jane Smith",
  "roles": ["user"],
  "status": "active",
  "created_at": "2024-01-20T00:00:00Z"
}
```

### Update User
```http
PUT /api/users/{user_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "full_name": "Jane Smith-Johnson",
  "email": "jane.johnson@example.com",
  "roles": ["user", "admin"],
  "metadata": {
    "department": "Executive",
    "location": "London"
  }
}
```

### Delete User
```http
DELETE /api/users/{user_id}
Authorization: Bearer {access_token}
```

## Database Operations

### Query Execution
```http
POST /api/database/query
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "collection": "products",
  "operation": "find",
  "filter": {
    "category": "electronics",
    "price": {"$gte": 100, "$lte": 500}
  },
  "projection": ["name", "price", "description"],
  "sort": {"price": -1},
  "limit": 10
}
```

**Response:**
```json
{
  "count": 10,
  "data": [
    {
      "name": "Laptop Pro",
      "price": 499.99,
      "description": "High-performance laptop"
    }
  ],
  "execution_time_ms": 15
}
```

### Bulk Operations
```http
POST /api/database/bulk
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "collection": "products",
  "operations": [
    {
      "type": "insert",
      "document": {
        "name": "New Product",
        "price": 299.99
      }
    },
    {
      "type": "update",
      "filter": {"_id": "507f1f77bcf86cd799439011"},
      "update": {"$set": {"price": 249.99}}
    },
    {
      "type": "delete",
      "filter": {"_id": "507f1f77bcf86cd799439012"}
    }
  ]
}
```

**Response:**
```json
{
  "success": true,
  "results": {
    "inserted": 1,
    "updated": 1,
    "deleted": 1
  },
  "errors": []
}
```

## WebSocket API

### Connection
```javascript
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onopen = () => {
  // Authenticate
  ws.send(JSON.stringify({
    type: 'auth',
    token: 'your_jwt_token'
  }));
};
```

### Subscribe to Events
```javascript
// Subscribe to plugin events
ws.send(JSON.stringify({
  type: 'subscribe',
  channel: 'plugin_events',
  filters: {
    plugin_id: 'analytics_dashboard',
    event_types: ['data_update', 'alert']
  }
}));
```

### Receive Events
```javascript
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Received:', data);
  // {
  //   "type": "event",
  //   "channel": "plugin_events",
  //   "data": {
  //     "plugin_id": "analytics_dashboard",
  //     "event_type": "data_update",
  //     "payload": {...}
  //   },
  //   "timestamp": "2024-01-20T15:30:00Z"
  // }
};
```

### RPC Calls
```javascript
// Make RPC call through WebSocket
ws.send(JSON.stringify({
  type: 'rpc',
  id: 'req_123',
  method: 'plugin.analytics.getStats',
  params: {
    start_date: '2024-01-01',
    end_date: '2024-01-31'
  }
}));

// Receive RPC response
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  if (data.type === 'rpc_response' && data.id === 'req_123') {
    console.log('Stats:', data.result);
  }
};
```

## Error Handling

### Error Response Format
All API errors follow a consistent format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request parameters",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ],
    "request_id": "req_xyz123",
    "timestamp": "2024-01-20T15:30:00Z"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `AUTHENTICATION_REQUIRED` | 401 | No valid authentication provided |
| `INVALID_CREDENTIALS` | 401 | Invalid username or password |
| `TOKEN_EXPIRED` | 401 | JWT token has expired |
| `PERMISSION_DENIED` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource not found |
| `VALIDATION_ERROR` | 400 | Request validation failed |
| `CONFLICT` | 409 | Resource conflict (e.g., duplicate) |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

### Error Examples

#### Authentication Error
```http
HTTP/1.1 401 Unauthorized
```
```json
{
  "error": {
    "code": "TOKEN_EXPIRED",
    "message": "Your session has expired. Please login again.",
    "request_id": "req_abc789",
    "timestamp": "2024-01-20T15:30:00Z"
  }
}
```

#### Validation Error
```http
HTTP/1.1 400 Bad Request
```
```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Request validation failed",
    "details": [
      {
        "field": "email",
        "message": "Email is required"
      },
      {
        "field": "age",
        "message": "Age must be between 18 and 120"
      }
    ],
    "request_id": "req_def456",
    "timestamp": "2024-01-20T15:30:00Z"
  }
}
```

## Rate Limiting

### Headers
Rate limit information is included in response headers:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 999
X-RateLimit-Reset: 1642694400
X-RateLimit-Reset-After: 3600
```

### Rate Limit Exceeded Response
```http
HTTP/1.1 429 Too Many Requests
Retry-After: 3600
```
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Please retry after 3600 seconds.",
    "retry_after": 3600,
    "limit": 1000,
    "window": "1h",
    "request_id": "req_ghi789",
    "timestamp": "2024-01-20T15:30:00Z"
  }
}
```

## API Versioning

### Version in URL
```http
GET /api/v2/users
```

### Version in Header
```http
GET /api/users
X-API-Version: 2.0
```

### Version Negotiation
```http
GET /api/users
Accept: application/vnd.nexus.v2+json
```

### Version Information
```http
GET /api/versions
```

**Response:**
```json
{
  "current": "2.0",
  "supported": ["1.0", "1.1", "2.0"],
  "deprecated": ["0.9"],
  "sunset_dates": {
    "1.0": "2024-12-31",
    "1.1": "2025-06-30"
  }
}
```

## Pagination

### Offset-based Pagination
```http
GET /api/users?page=2&limit=20
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "page": 2,
    "limit": 20,
    "total": 500,
    "total_pages": 25,
    "has_next": true,
    "has_prev": true
  }
}
```

### Cursor-based Pagination
```http
GET /api/events?cursor=eyJpZCI6MTAwfQ&limit=20
```

**Response:**
```json
{
  "data": [...],
  "pagination": {
    "cursor": "eyJpZCI6MTIwfQ",
    "next_cursor": "eyJpZCI6MTQwfQ",
    "prev_cursor": "eyJpZCI6MTAwfQ",
    "has_more": true
  }
}
```

## Filtering and Sorting

### Filtering
```http
GET /api/products?filter[category]=electronics&filter[price][$gte]=100&filter[price][$lte]=500
```

### Sorting
```http
GET /api/products?sort=-price,name
```
- Use `-` prefix for descending order
- Multiple fields separated by comma

### Field Selection
```http
GET /api/products?fields=id,name,price,category
```

## Batch Requests

### Batch API Calls
```http
POST /api/batch
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "requests": [
    {
      "id": "req1",
      "method": "GET",
      "url": "/api/users/123"
    },
    {
      "id": "req2",
      "method": "POST",
      "url": "/api/products",
      "body": {
        "name": "New Product",
        "price": 99.99
      }
    },
    {
      "id": "req3",
      "method": "DELETE",
      "url": "/api/orders/456"
    }
  ]
}
```

**Response:**
```json
{
  "responses": [
    {
      "id": "req1",
      "status": 200,
      "body": {
        "id": "123",
        "username": "john.doe"
      }
    },
    {
      "id": "req2",
      "status": 201,
      "body": {
        "id": "789",
        "name": "New Product"
      }
    },
    {
      "id": "req3",
      "status": 204,
      "body": null
    }
  ]
}
```

## Webhooks

### Register Webhook
```http
POST /api/webhooks
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "url": "https://example.com/webhook",
  "events": ["plugin.installed", "plugin.updated", "user.created"],
  "secret": "webhook_secret_key",
  "active": true
}
```

**Response:**
```json
{
  "id": "wh_123456",
  "url": "https://example.com/webhook",
  "events": ["plugin.installed", "plugin.updated", "user.created"],
  "created_at": "2024-01-20T15:30:00Z",
  "active": true
}
```

### Webhook Payload Format
```json
{
  "id": "evt_789012",
  "type": "plugin.installed",
  "data": {
    "plugin_id": "analytics_dashboard",
    "version": "2.1.0"
  },
  "timestamp": "2024-01-20T15:30:00Z",
  "signature": "sha256=..."
}
```

## SDK Examples

### Python SDK
```python
from nexus_sdk import NexusClient

# Initialize client
client = NexusClient(
    base_url="http://localhost:8000",
    api_key="sk_live_xxxxxxxxxxx"
)

# List plugins
plugins = client.plugins.list(category="analytics")

# Create user
user = client.users.create(
    username="new.user",
    email="new.user@example.com",
    password="SecurePass123!"
)

# Query database
results = client.database.query(
    collection="products",
    filter={"category": "electronics"},
    limit=10
)
```

### JavaScript SDK
```javascript
import { NexusClient } from '@nexus/sdk';

// Initialize client
const client = new NexusClient({
  baseUrl: 'http://localhost:8000',
  apiKey: 'sk_live_xxxxxxxxxxx'
});

// List plugins
const plugins = await client.plugins.list({ category: 'analytics' });

// Create user
const user = await client.users.create({
  username: 'new.user',
  email: 'new.user@example.com',
  password: 'SecurePass123!'
});

// Query database
const results = await client.database.query({
  collection: 'products',
  filter: { category: 'electronics' },
  limit: 10
});
```

## Testing API Endpoints

### Using cURL
```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin123"}'

# Get plugins with authentication
curl -X GET http://localhost:8000/api/plugins \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Create a user
curl -X POST http://localhost:8000/api/users \
  -H "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  -H "Content-Type: application/json" \
  -d '{"username":"newuser","email":"user@example.com","password":"Pass123!"}'
```

### Using HTTPie
```bash
# Login
http POST localhost:8000/api/auth/login username=admin password=admin123

# Get plugins
http GET localhost:8000/api/plugins "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..."

# Create user
http POST localhost:8000/api/users \
  "Authorization: Bearer eyJ0eXAiOiJKV1QiLCJhbGc..." \
  username=newuser email=user@example.com password=Pass123!
```

### Using Postman
1. Import the OpenAPI schema from `http://localhost:8000/openapi.json`
2. Set up environment variables for `base_url` and `access_token`
3. Use the auto-generated collection to test endpoints

## Performance Tips

1. **Use field selection** to reduce payload size
2. **Implement caching** for frequently accessed data
3. **Use cursor-based pagination** for large datasets
4. **Batch API calls** when making multiple requests
5. **Enable compression** in HTTP headers
6. **Use WebSocket** for real-time updates instead of polling
7. **Implement proper error retry logic** with exponential backoff

## Security Best Practices

1. **Always use HTTPS** in production
2. **Rotate API keys** regularly
3. **Implement rate limiting** per user/IP
4. **Use short-lived JWT tokens** with refresh tokens
5. **Validate all input** on the server side
6. **Implement CORS** properly
7. **Log all API access** for auditing
8. **Use webhook signatures** to verify authenticity
9. **Implement field-level permissions** for sensitive data
10. **Regular security audits** of API endpoints

---

For more information, see:
- [Plugin Development Guide](./PLUGIN_DEVELOPMENT.md)
- [Authentication Guide](./AUTHENTICATION.md)
- [WebSocket Guide](./WEBSOCKET.md)
- [SDK Documentation](./SDK.md)