# API Reference

Comprehensive API documentation for the Nexus platform.

## 🎯 Overview

The Nexus API provides a powerful interface for interacting with the platform, managing plugins, and building integrations. The API is built on FastAPI and follows REST principles with automatic OpenAPI documentation.

## 📚 API Documentation Structure

| Section | Description | Best For |
|---------|-------------|----------|
| **[Core API](core.md)** | Platform core functionality | Core system integration |
| **[Plugin API](plugins.md)** | Plugin management and lifecycle | Plugin developers |
| **[Events API](events.md)** | Event system operations | Event-driven integrations |
| **[Auth API](auth.md)** | Authentication and authorization | Security implementations |
| **[Admin API](admin.md)** | Administrative operations | System administrators |

## 🚀 Getting Started

### Base URL

```
https://your-nexus-instance.com/api/v1
```

### Authentication

All API requests require authentication. Nexus supports multiple authentication methods:

#### Bearer Token (JWT)
```bash
curl -H "Authorization: Bearer <your-jwt-token>" \
     https://your-nexus-instance.com/api/v1/status
```

#### API Key
```bash
curl -H "X-API-Key: <your-api-key>" \
     https://your-nexus-instance.com/api/v1/status
```

### Quick Start Example

```python
import aiohttp
import asyncio

async def get_system_status():
    headers = {"Authorization": "Bearer YOUR_JWT_TOKEN"}

    async with aiohttp.ClientSession() as session:
        async with session.get(
            "https://your-nexus-instance.com/api/v1/status",
            headers=headers
        ) as response:
            data = await response.json()
            print(f"System status: {data['status']}")

# Run the example
asyncio.run(get_system_status())
```

## 🏗️ API Architecture

### RESTful Design

The Nexus API follows REST principles:

- **Resources**: Nouns representing entities (users, plugins, events)
- **HTTP Methods**: Verbs for actions (GET, POST, PUT, DELETE)
- **Status Codes**: Standard HTTP status codes
- **JSON**: Consistent JSON request/response format

### API Versioning

APIs are versioned using URL paths:

```
/api/v1/...  # Current stable version
/api/v2/...  # Next version (when available)
```

### Response Format

All API responses follow a consistent format:

```json
{
  "success": true,
  "data": {
    // Response data here
  },
  "message": "Operation completed successfully",
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}
```

Error responses:

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "email",
      "reason": "Invalid email format"
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}
```

## 🔑 Core Endpoints

### System Information

```http
GET /api/v1/status
```

Get system status and health information.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "uptime": 3600,
    "components": {
      "database": "healthy",
      "event_bus": "healthy",
      "plugins": "healthy"
    }
  }
}
```

### Plugin Management

```http
GET /api/v1/plugins
POST /api/v1/plugins
GET /api/v1/plugins/{plugin_id}
PUT /api/v1/plugins/{plugin_id}
DELETE /api/v1/plugins/{plugin_id}
```

### Event Operations

```http
POST /api/v1/events
GET /api/v1/events
GET /api/v1/events/{event_id}
```

### User Management

```http
GET /api/v1/users
POST /api/v1/users
GET /api/v1/users/{user_id}
PUT /api/v1/users/{user_id}
DELETE /api/v1/users/{user_id}
```

## 📖 OpenAPI Documentation

Nexus automatically generates OpenAPI/Swagger documentation for all endpoints.

### Interactive Documentation

Access the interactive API documentation at:

```
https://your-nexus-instance.com/docs
```

### OpenAPI Specification

Download the OpenAPI specification:

```
https://your-nexus-instance.com/openapi.json
```

### ReDoc Documentation

Alternative documentation interface:

```
https://your-nexus-instance.com/redoc
```

## 🛠️ Client Libraries

### Python Client

```python
from nexus_client import NexusClient

# Initialize client
client = NexusClient(
    base_url="https://your-nexus-instance.com",
    api_key="your-api-key"
)

# Get system status
status = await client.get_status()
print(status.version)

# List plugins
plugins = await client.plugins.list()
for plugin in plugins:
    print(f"Plugin: {plugin.name} - {plugin.status}")

# Create a new user
user = await client.users.create({
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password"
})
```

### JavaScript/TypeScript Client

```typescript
import { NexusClient } from '@nexus/client';

// Initialize client
const client = new NexusClient({
  baseUrl: 'https://your-nexus-instance.com',
  apiKey: 'your-api-key'
});

// Get system status
const status = await client.getStatus();
console.log(`System version: ${status.version}`);

// List plugins
const plugins = await client.plugins.list();
plugins.forEach(plugin => {
  console.log(`Plugin: ${plugin.name} - ${plugin.status}`);
});

// Emit an event
await client.events.emit({
  type: 'user.created',
  data: { userId: '123', username: 'john_doe' }
});
```

### cURL Examples

#### Get System Status
```bash
curl -X GET \
  https://your-nexus-instance.com/api/v1/status \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

#### Create a Plugin
```bash
curl -X POST \
  https://your-nexus-instance.com/api/v1/plugins \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-plugin",
    "version": "1.0.0",
    "description": "A sample plugin"
  }'
```

#### Emit an Event
```bash
curl -X POST \
  https://your-nexus-instance.com/api/v1/events \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "type": "user.registered",
    "data": {
      "user_id": "user_123",
      "username": "new_user"
    }
  }'
```

## 🔒 Authentication & Authorization

### JWT Token Authentication

1. **Login** to get a JWT token:
```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "username": "your_username",
  "password": "your_password"
}
```

2. **Use the token** in subsequent requests:
```http
Authorization: Bearer <jwt_token>
```

### API Key Authentication

1. **Generate API key** (via admin panel or API)
2. **Use the key** in requests:
```http
X-API-Key: <your_api_key>
```

### Scoped Permissions

API keys and JWT tokens can have scoped permissions:

- `read:plugins` - Read plugin information
- `write:plugins` - Create and modify plugins
- `admin:system` - Administrative operations
- `events:emit` - Emit events
- `events:subscribe` - Subscribe to events

## 📊 Rate Limiting

The API implements rate limiting to ensure fair usage:

### Default Limits

- **Authenticated requests**: 1000 requests/hour
- **Unauthenticated requests**: 100 requests/hour
- **Authentication endpoints**: 10 requests/10 minutes

### Rate Limit Headers

Responses include rate limit information:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1640995200
X-RateLimit-Window: 3600
```

### Handling Rate Limits

When rate limited, you'll receive a `429 Too Many Requests` response:

```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded. Try again later.",
    "retry_after": 3600
  }
}
```

## 🚨 Error Handling

### HTTP Status Codes

| Status | Meaning | Description |
|--------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Resource already exists |
| 422 | Unprocessable Entity | Validation error |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error |

### Error Response Format

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human readable error message",
    "details": {
      // Additional error details
    }
  },
  "timestamp": "2024-01-01T12:00:00Z",
  "request_id": "req_123456789"
}
```

### Common Error Codes

- `VALIDATION_ERROR` - Input validation failed
- `AUTHENTICATION_FAILED` - Invalid credentials
- `AUTHORIZATION_DENIED` - Insufficient permissions
- `RESOURCE_NOT_FOUND` - Requested resource doesn't exist
- `RESOURCE_CONFLICT` - Resource already exists
- `RATE_LIMIT_EXCEEDED` - Too many requests
- `INTERNAL_ERROR` - Server-side error

## 🧪 Testing

### Test Environment

Nexus provides a test environment for API development:

```
https://test.your-nexus-instance.com/api/v1
```

### Postman Collection

Download the Postman collection for easy API testing:

```
https://your-nexus-instance.com/api/postman-collection.json
```

### Mock Server

For development and testing, use the mock server:

```bash
# Start mock server
npx @nexus/mock-server --port 3000

# API available at http://localhost:3000/api/v1
```

## 📈 Monitoring & Analytics

### Request Metrics

Monitor API usage through the admin dashboard:

- Request count by endpoint
- Response time percentiles
- Error rate by status code
- Rate limit violations

### Custom Metrics

Track custom metrics in your integrations:

```python
from nexus_client import NexusClient

client = NexusClient(api_key="your-key")

# Track custom metric
await client.metrics.increment("api.custom_action", 1, {
    "user_id": "123",
    "action": "file_upload"
})
```

## 🔄 Webhooks

### Event Webhooks

Subscribe to events via webhooks:

```http
POST /api/v1/webhooks
{
  "url": "https://your-app.com/webhook",
  "events": ["user.created", "plugin.loaded"],
  "secret": "webhook_secret"
}
```

### Webhook Verification

Verify webhook authenticity:

```python
import hmac
import hashlib

def verify_webhook(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(f"sha256={expected}", signature)
```

## 🎯 Best Practices

### 1. Use Appropriate HTTP Methods

- **GET** - Retrieve data (idempotent)
- **POST** - Create resources
- **PUT** - Update entire resources (idempotent)
- **PATCH** - Partial updates
- **DELETE** - Remove resources (idempotent)

### 2. Handle Errors Gracefully

```python
async def api_call_with_retry():
    for attempt in range(3):
        try:
            response = await client.get("/endpoint")
            return response
        except RateLimitError:
            await asyncio.sleep(2 ** attempt)  # Exponential backoff
        except AuthenticationError:
            await refresh_token()
        except Exception as e:
            if attempt == 2:  # Last attempt
                raise
            continue
```

### 3. Use Pagination

For large datasets, use pagination:

```http
GET /api/v1/plugins?page=2&per_page=20
```

### 4. Leverage Caching

Use ETags and caching headers:

```http
GET /api/v1/plugins
If-None-Match: "abc123"
```

### 5. Monitor API Usage

Track and monitor your API usage:

- Response times
- Error rates
- Rate limit usage
- Authentication failures

## 📚 Additional Resources

- **[Plugin Development Guide](../plugins/basics.md)** - Build plugins using the API
- **[Event System](../architecture/events.md)** - Understand the event architecture
- **[Security Guide](../architecture/security.md)** - API security best practices
- **[Configuration](../getting-started/configuration.md)** - Configure API settings

## 🆘 Support

### Getting Help

- **Documentation**: Check this documentation first
- **Community Forum**: Join our community discussions
- **GitHub Issues**: Report bugs and feature requests
- **Email Support**: contact@nexus-platform.dev

### API Status

Check API status and uptime:

```
https://status.nexus-platform.dev
```

---

**The Nexus API is your gateway to building powerful integrations.** Start with the [Core API](core.md) to understand the fundamentals, then explore specific APIs based on your use case.
