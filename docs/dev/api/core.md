# Core API

Core platform functionality and system operations.

## 🎯 Overview

The Core API provides essential functionality for interacting with the Nexus platform, including system status, health checks, configuration management, and core service operations.

## 🏗️ Base URL

All Core API endpoints are available under:

```
/api/v1/core
```

## 📊 System Status

### Get System Status

Get current system status and health information.

```http
GET /api/v1/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "1.0.0",
    "environment": "production",
    "uptime": 86400,
    "components": {
      "database": {
        "status": "healthy",
        "response_time_ms": 12,
        "connection_pool": {
          "active": 5,
          "idle": 15,
          "total": 20
        }
      },
      "event_bus": {
        "status": "healthy",
        "queue_size": 42,
        "processed_events": 15420
      },
      "plugins": {
        "status": "healthy",
        "loaded": 8,
        "active": 7,
        "failed": 1
      },
      "cache": {
        "status": "healthy",
        "hit_rate": 0.89,
        "memory_usage": "245MB"
      }
    }
  }
}
```

### Health Check

Simple health check endpoint for load balancers.

```http
GET /api/v1/health
```

**Response:**
```json
{
  "status": "ok",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

## ⚙️ Configuration Management

### Get Configuration

Retrieve current system configuration.

```http
GET /api/v1/config
```

**Query Parameters:**
- `section` (optional): Specific configuration section
- `mask_secrets` (optional): Whether to mask secret values (default: true)

**Response:**
```json
{
  "success": true,
  "data": {
    "database": {
      "host": "localhost",
      "port": 5432,
      "database": "nexus",
      "password": "***masked***"
    },
    "server": {
      "host": "0.0.0.0",
      "port": 8000,
      "workers": 4
    },
    "plugins": {
      "auto_load": true,
      "plugin_directory": "./plugins"
    }
  }
}
```

### Update Configuration

Update system configuration (requires admin privileges).

```http
PUT /api/v1/config
```

**Request Body:**
```json
{
  "server": {
    "workers": 8
  },
  "plugins": {
    "auto_load": false
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "updated_keys": ["server.workers", "plugins.auto_load"],
    "restart_required": false
  }
}
```

## 📈 Metrics & Analytics

### Get System Metrics

Retrieve system performance metrics.

```http
GET /api/v1/metrics
```

**Query Parameters:**
- `start_time` (optional): Start time for metrics (ISO 8601)
- `end_time` (optional): End time for metrics (ISO 8601)
- `resolution` (optional): Time resolution (1m, 5m, 15m, 1h, 1d)

**Response:**
```json
{
  "success": true,
  "data": {
    "time_range": {
      "start": "2024-01-01T11:00:00Z",
      "end": "2024-01-01T12:00:00Z"
    },
    "metrics": {
      "requests_per_second": [
        {"timestamp": "2024-01-01T11:00:00Z", "value": 45.2},
        {"timestamp": "2024-01-01T11:01:00Z", "value": 52.1}
      ],
      "response_time_ms": [
        {"timestamp": "2024-01-01T11:00:00Z", "value": 125},
        {"timestamp": "2024-01-01T11:01:00Z", "value": 98}
      ],
      "memory_usage_mb": [
        {"timestamp": "2024-01-01T11:00:00Z", "value": 512},
        {"timestamp": "2024-01-01T11:01:00Z", "value": 524}
      ],
      "cpu_usage_percent": [
        {"timestamp": "2024-01-01T11:00:00Z", "value": 35.5},
        {"timestamp": "2024-01-01T11:01:00Z", "value": 42.1}
      ]
    }
  }
}
```

### Get Performance Summary

Get aggregated performance statistics.

```http
GET /api/v1/metrics/summary
```

**Response:**
```json
{
  "success": true,
  "data": {
    "requests": {
      "total": 125420,
      "success_rate": 0.998,
      "avg_response_time_ms": 145,
      "p95_response_time_ms": 285,
      "p99_response_time_ms": 425
    },
    "errors": {
      "total": 251,
      "rate": 0.002,
      "by_status": {
        "400": 45,
        "401": 12,
        "403": 8,
        "404": 89,
        "500": 97
      }
    },
    "resources": {
      "avg_cpu_percent": 38.5,
      "avg_memory_mb": 518,
      "peak_memory_mb": 742,
      "disk_usage_gb": 2.8
    }
  }
}
```

## 🔧 Service Management

### List Services

Get list of all registered services.

```http
GET /api/v1/services
```

**Response:**
```json
{
  "success": true,
  "data": {
    "services": [
      {
        "name": "database_adapter",
        "type": "DatabaseAdapter",
        "status": "running",
        "health": "healthy",
        "version": "1.0.0",
        "dependencies": ["connection_pool"],
        "metrics": {
          "uptime": 86400,
          "requests_handled": 15420
        }
      },
      {
        "name": "event_bus",
        "type": "EventBus",
        "status": "running",
        "health": "healthy",
        "version": "1.0.0",
        "dependencies": [],
        "metrics": {
          "uptime": 86400,
          "events_processed": 8540
        }
      }
    ]
  }
}
```

### Get Service Details

Get detailed information about a specific service.

```http
GET /api/v1/services/{service_name}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "name": "database_adapter",
    "type": "DatabaseAdapter",
    "status": "running",
    "health": "healthy",
    "version": "1.0.0",
    "config": {
      "pool_size": 20,
      "timeout": 30,
      "retry_attempts": 3
    },
    "dependencies": ["connection_pool"],
    "dependents": ["user_service", "plugin_manager"],
    "metrics": {
      "uptime": 86400,
      "requests_handled": 15420,
      "avg_response_time_ms": 12,
      "error_rate": 0.001
    },
    "recent_errors": [
      {
        "timestamp": "2024-01-01T11:30:00Z",
        "error": "Connection timeout",
        "count": 1
      }
    ]
  }
}
```

### Restart Service

Restart a specific service (requires admin privileges).

```http
POST /api/v1/services/{service_name}/restart
```

**Response:**
```json
{
  "success": true,
  "data": {
    "service": "database_adapter",
    "action": "restart",
    "status": "completed",
    "duration_ms": 2500
  }
}
```

## 📊 Component Status

### Get Component Health

Check health of all system components.

```http
GET /api/v1/components/health
```

**Response:**
```json
{
  "success": true,
  "data": {
    "overall_status": "healthy",
    "components": [
      {
        "name": "database",
        "status": "healthy",
        "checks": [
          {
            "name": "connection",
            "status": "pass",
            "response_time_ms": 12
          },
          {
            "name": "query_performance",
            "status": "pass",
            "avg_query_time_ms": 45
          }
        ]
      },
      {
        "name": "cache",
        "status": "healthy",
        "checks": [
          {
            "name": "connectivity",
            "status": "pass",
            "response_time_ms": 3
          },
          {
            "name": "memory_usage",
            "status": "warning",
            "current_mb": 245,
            "limit_mb": 512
          }
        ]
      }
    ]
  }
}
```

### Run Component Diagnostics

Run diagnostic tests on system components.

```http
POST /api/v1/components/diagnostics
```

**Request Body:**
```json
{
  "components": ["database", "cache", "event_bus"],
  "tests": ["connectivity", "performance", "stress"]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "test_run_id": "diag_123456",
    "status": "completed",
    "duration_ms": 15000,
    "results": [
      {
        "component": "database",
        "tests": [
          {
            "name": "connectivity",
            "status": "pass",
            "duration_ms": 50,
            "details": "Connection established successfully"
          },
          {
            "name": "performance",
            "status": "pass",
            "duration_ms": 5000,
            "details": {
              "avg_query_time_ms": 45,
              "queries_per_second": 2500
            }
          }
        ]
      }
    ]
  }
}
```

## 🗄️ Cache Management

### Get Cache Status

Get cache system status and statistics.

```http
GET /api/v1/cache/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "memory_usage": {
      "used_mb": 245,
      "available_mb": 267,
      "total_mb": 512
    },
    "statistics": {
      "hit_rate": 0.89,
      "miss_rate": 0.11,
      "total_hits": 45200,
      "total_misses": 5580,
      "evictions": 120
    },
    "cache_levels": [
      {
        "level": "L1",
        "type": "memory",
        "size_mb": 128,
        "hit_rate": 0.95
      },
      {
        "level": "L2",
        "type": "redis",
        "size_mb": 384,
        "hit_rate": 0.82
      }
    ]
  }
}
```

### Clear Cache

Clear cache entries by pattern or clear all.

```http
DELETE /api/v1/cache
```

**Query Parameters:**
- `pattern` (optional): Cache key pattern to clear
- `level` (optional): Cache level to clear (L1, L2, all)

**Request Body:**
```json
{
  "pattern": "user:*",
  "level": "all"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "cleared_keys": 1250,
    "pattern": "user:*",
    "levels": ["L1", "L2"]
  }
}
```

## 🔄 Task Management

### List Background Tasks

Get list of running background tasks.

```http
GET /api/v1/tasks
```

**Query Parameters:**
- `status` (optional): Filter by status (running, completed, failed)
- `type` (optional): Filter by task type

**Response:**
```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": "task_123456",
        "type": "plugin_update",
        "status": "running",
        "progress": 0.75,
        "created_at": "2024-01-01T11:00:00Z",
        "started_at": "2024-01-01T11:00:05Z",
        "estimated_completion": "2024-01-01T11:05:00Z",
        "details": {
          "plugin_id": "example_plugin",
          "version": "2.0.0"
        }
      },
      {
        "id": "task_789012",
        "type": "database_cleanup",
        "status": "completed",
        "progress": 1.0,
        "created_at": "2024-01-01T10:00:00Z",
        "started_at": "2024-01-01T10:00:01Z",
        "completed_at": "2024-01-01T10:15:30Z",
        "result": {
          "records_cleaned": 15420,
          "space_freed_mb": 245
        }
      }
    ]
  }
}
```

### Get Task Status

Get detailed status of a specific task.

```http
GET /api/v1/tasks/{task_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "task_123456",
    "type": "plugin_update",
    "status": "running",
    "progress": 0.75,
    "created_at": "2024-01-01T11:00:00Z",
    "started_at": "2024-01-01T11:00:05Z",
    "estimated_completion": "2024-01-01T11:05:00Z",
    "details": {
      "plugin_id": "example_plugin",
      "current_version": "1.5.0",
      "target_version": "2.0.0",
      "steps": [
        {"name": "download", "status": "completed"},
        {"name": "validate", "status": "completed"},
        {"name": "backup", "status": "completed"},
        {"name": "install", "status": "running", "progress": 0.5},
        {"name": "test", "status": "pending"},
        {"name": "activate", "status": "pending"}
      ]
    },
    "logs": [
      {
        "timestamp": "2024-01-01T11:00:10Z",
        "level": "INFO",
        "message": "Starting plugin update process"
      },
      {
        "timestamp": "2024-01-01T11:02:30Z",
        "level": "INFO",
        "message": "Download completed successfully"
      }
    ]
  }
}
```

### Cancel Task

Cancel a running task.

```http
DELETE /api/v1/tasks/{task_id}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "task_123456",
    "status": "cancelled",
    "cancelled_at": "2024-01-01T11:03:45Z"
  }
}
```

## 🔐 Security Operations

### Get Security Status

Get current security status and alerts.

```http
GET /api/v1/security/status
```

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "secure",
    "last_scan": "2024-01-01T10:00:00Z",
    "alerts": [
      {
        "id": "alert_001",
        "severity": "medium",
        "type": "suspicious_activity",
        "message": "Multiple failed login attempts detected",
        "timestamp": "2024-01-01T11:30:00Z",
        "details": {
          "ip_address": "192.168.1.100",
          "attempts": 5,
          "user": "admin"
        }
      }
    ],
    "metrics": {
      "failed_logins_24h": 12,
      "blocked_ips": 3,
      "active_sessions": 45,
      "api_key_usage": 1250
    }
  }
}
```

### Run Security Scan

Initiate a security scan of the system.

```http
POST /api/v1/security/scan
```

**Request Body:**
```json
{
  "type": "full",
  "components": ["plugins", "configuration", "permissions"],
  "severity_threshold": "medium"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "scan_id": "scan_123456",
    "status": "started",
    "estimated_duration_ms": 300000,
    "components_to_scan": ["plugins", "configuration", "permissions"]
  }
}
```

## 💾 Backup & Recovery

### Create System Backup

Create a backup of system data and configuration.

```http
POST /api/v1/backup
```

**Request Body:**
```json
{
  "include": ["configuration", "database", "plugins"],
  "compression": true,
  "encryption": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "backup_id": "backup_123456",
    "status": "created",
    "size_mb": 125,
    "created_at": "2024-01-01T12:00:00Z",
    "includes": ["configuration", "database", "plugins"],
    "download_url": "/api/v1/backup/backup_123456/download"
  }
}
```

### List Backups

Get list of available backups.

```http
GET /api/v1/backup
```

**Response:**
```json
{
  "success": true,
  "data": {
    "backups": [
      {
        "id": "backup_123456",
        "created_at": "2024-01-01T12:00:00Z",
        "size_mb": 125,
        "type": "manual",
        "includes": ["configuration", "database", "plugins"],
        "status": "completed"
      },
      {
        "id": "backup_789012",
        "created_at": "2024-01-01T06:00:00Z",
        "size_mb": 118,
        "type": "scheduled",
        "includes": ["configuration", "database"],
        "status": "completed"
      }
    ]
  }
}
```

### Restore from Backup

Restore system from a backup.

```http
POST /api/v1/backup/{backup_id}/restore
```

**Request Body:**
```json
{
  "components": ["configuration", "database"],
  "confirm": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "restore_id": "restore_123456",
    "status": "started",
    "backup_id": "backup_123456",
    "estimated_duration_ms": 600000
  }
}
```

## 🎯 API Usage Examples

### Python Example

```python
import aiohttp
import asyncio

class NexusCoreAPI:
    def __init__(self, base_url: str, api_key: str):
        self.base_url = base_url
        self.headers = {"X-API-Key": api_key}

    async def get_system_status(self):
        """Get system status."""
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/v1/status",
                headers=self.headers
            ) as response:
                return await response.json()

    async def get_metrics(self, start_time=None, end_time=None):
        """Get system metrics."""
        params = {}
        if start_time:
            params['start_time'] = start_time
        if end_time:
            params['end_time'] = end_time

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/api/v1/metrics",
                headers=self.headers,
                params=params
            ) as response:
                return await response.json()

    async def clear_cache(self, pattern=None):
        """Clear cache entries."""
        data = {}
        if pattern:
            data['pattern'] = pattern

        async with aiohttp.ClientSession() as session:
            async with session.delete(
                f"{self.base_url}/api/v1/cache",
                headers=self.headers,
                json=data
            ) as response:
                return await response.json()

# Usage
async def main():
    api = NexusCoreAPI("https://your-nexus-instance.com", "your-api-key")

    # Get system status
    status = await api.get_system_status()
    print(f"System status: {status['data']['status']}")

    # Get metrics
    metrics = await api.get_metrics()
    print(f"Request rate: {metrics['data']['metrics']['requests_per_second']}")

    # Clear user cache
    result = await api.clear_cache("user:*")
    print(f"Cleared {result['data']['cleared_keys']} cache entries")

asyncio.run(main())
```

### cURL Examples

```bash
# Get system status
curl -H "X-API-Key: your-api-key" \
     https://your-nexus-instance.com/api/v1/status

# Get metrics for last hour
curl -H "X-API-Key: your-api-key" \
     "https://your-nexus-instance.com/api/v1/metrics?start_time=2024-01-01T11:00:00Z&end_time=2024-01-01T12:00:00Z"

# Clear cache
curl -X DELETE \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"pattern": "user:*"}' \
     https://your-nexus-instance.com/api/v1/cache

# Create backup
curl -X POST \
     -H "X-API-Key: your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"include": ["configuration", "database"], "compression": true}' \
     https://your-nexus-instance.com/api/v1/backup
```

## 🔒 Required Permissions

Different endpoints require different permission levels:

| Endpoint | Permission Required |
|----------|-------------------|
| GET /status | `read:system` |
| GET /metrics | `read:metrics` |
| PUT /config | `admin:config` |
| POST /services/{service}/restart | `admin:services` |
| DELETE /cache | `write:cache` |
| POST /backup | `admin:backup` |
| POST /security/scan | `admin:security` |

## 📚 Related Documentation

- **[Authentication API](auth.md)** - User authentication and authorization
- **[Plugin API](plugins.md)** - Plugin management operations
- **[Events API](events.md)** - Event system operations
- **[Admin API](admin.md)** - Administrative functions

---

**The Core API provides the foundation for all Nexus operations.** Use these endpoints to monitor, configure, and manage your Nexus instance effectively.
