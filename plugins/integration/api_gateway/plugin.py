"""
API Gateway Plugin

A comprehensive API gateway plugin providing request routing, authentication,
rate limiting, caching, and API management with web API and UI.
"""

# type: ignore
# mypy: ignore-errors
# pyright: ignore

import asyncio
import json
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple, cast
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, BackgroundTasks
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
from pydantic import HttpUrl


from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


# Helper class to avoid type checker issues with Request objects
class RequestDataExtractor:
    """Extract data from Request objects safely."""

    def __init__(self, request):
        # Extract all data immediately to avoid type issues
        self.method = str(request.method) if hasattr(request, "method") else "GET"
        self.headers = dict(request.headers) if hasattr(request, "headers") else {}
        self.query_params = dict(request.query_params) if hasattr(request, "query_params") else {}
        self.url_path = (
            str(request.url.path)
            if hasattr(request, "url") and hasattr(request.url, "path")
            else "/"
        )
        self._request = request

    async def get_body(self):
        """Get request body safely."""
        if hasattr(self._request, "body"):
            return await self._request.body()
        return None


# Data Models
class APIEndpoint(BaseModel):
    """API endpoint configuration."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    path: str
    upstream_url: HttpUrl
    methods: List[str] = Field(default_factory=lambda: ["GET"])
    auth_required: bool = True
    rate_limit: Optional[int] = None  # requests per minute
    cache_ttl: Optional[int] = None  # seconds
    headers: Dict[str, str] = Field(default_factory=dict)
    transformations: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)


class APIKey(BaseModel):
    """API key model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    key: str
    endpoints: List[str] = Field(default_factory=list)  # endpoint IDs
    rate_limit: Optional[int] = None
    is_active: bool = True
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_used: Optional[datetime] = None
    usage_count: int = 0


class RequestLog(BaseModel):
    """API request log model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    endpoint_id: str
    api_key_id: Optional[str] = None
    method: str
    path: str
    status_code: int
    response_time: float  # milliseconds
    request_size: int = 0
    response_size: int = 0
    ip_address: str = ""
    user_agent: str = ""
    error_message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class RateLimitBucket(BaseModel):
    """Rate limiting bucket."""

    key: str
    requests: List[datetime] = Field(default_factory=list)
    limit: int
    window: int = 60  # seconds


class CacheEntry(BaseModel):
    """Cache entry model."""

    key: str
    value: str
    content_type: str = "application/json"
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class APIGatewayPlugin(BasePlugin):
    """API Gateway Plugin with request routing and management."""

    def __init__(self):
        super().__init__()
        self.name = "api_gateway"
        self.version = "1.0.0"
        self.category = "integration"
        self.description = "Comprehensive API gateway with routing, auth, and rate limiting"

        # Storage
        self.endpoints: List[APIEndpoint] = []
        self.api_keys: List[APIKey] = []
        self.request_logs: List[RequestLog] = []
        self.rate_limit_buckets: Dict[str, RateLimitBucket] = {}
        self.cache_entries: Dict[str, CacheEntry] = {}

        # HTTP client for upstream requests
        self.http_client: Optional[httpx.AsyncClient] = None

        # Initialize sample data
        self._initialize_sample_data()

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin v{self.version}")

        # Initialize HTTP client
        self.http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0),
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )

        # Start background tasks
        asyncio.create_task(self._cleanup_expired_cache())
        asyncio.create_task(self._cleanup_old_logs())

        await self.publish_event(
            "api_gateway.initialized",
            {"plugin": self.name, "endpoints_count": len(self.endpoints)},
        )

        logger.info(f"{self.name} plugin initialized successfully")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")

        if self.http_client:
            await self.http_client.aclose()

        await self.publish_event(
            "api_gateway.shutdown",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix="/plugins/api_gateway", tags=["api_gateway"])

        # Management endpoints
        @router.get("/endpoints")
        async def get_endpoints():
            """Get all API endpoints."""
            return {"endpoints": [endpoint.dict() for endpoint in self.endpoints]}

        @router.post("/endpoints")
        async def create_endpoint(endpoint_data: APIEndpoint):
            """Create a new API endpoint."""
            # Check for path conflicts
            existing = next((e for e in self.endpoints if e.path == endpoint_data.path), None)
            if existing:
                raise HTTPException(status_code=400, detail="Path already exists")

            self.endpoints.append(endpoint_data)

            await self.publish_event(
                "api_gateway.endpoint.created",
                {
                    "endpoint_id": endpoint_data.id,
                    "name": endpoint_data.name,
                    "path": endpoint_data.path,
                },
            )

            return {"message": "Endpoint created", "endpoint_id": endpoint_data.id}

        @router.put("/endpoints/{endpoint_id}")
        async def update_endpoint(endpoint_id: str, endpoint_data: APIEndpoint):
            """Update an API endpoint."""
            endpoint = next((e for e in self.endpoints if e.id == endpoint_id), None)
            if not endpoint:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            # Update endpoint
            endpoint_data.id = endpoint_id
            endpoint_data.created_at = endpoint.created_at
            self.endpoints = [e if e.id != endpoint_id else endpoint_data for e in self.endpoints]

            return {"message": "Endpoint updated"}

        @router.delete("/endpoints/{endpoint_id}")
        async def delete_endpoint(endpoint_id: str):
            """Delete an API endpoint."""
            original_count = len(self.endpoints)
            self.endpoints = [e for e in self.endpoints if e.id != endpoint_id]

            if len(self.endpoints) == original_count:
                raise HTTPException(status_code=404, detail="Endpoint not found")

            return {"message": "Endpoint deleted"}

        # API Keys management
        @router.get("/api-keys")
        async def get_api_keys():
            """Get all API keys."""
            # Remove sensitive key data for security
            safe_keys = []
            for key in self.api_keys:
                key_dict = key.dict()
                key_dict["key"] = (
                    key.key[:8] + "..." + key.key[-4:] if len(key.key) > 12 else "****"
                )
                safe_keys.append(key_dict)
            return {"api_keys": safe_keys}

        @router.post("/api-keys")
        async def create_api_key(key_data: APIKey):
            """Create a new API key."""
            # Generate secure API key if not provided
            if not key_data.key:
                import secrets

                key_data.key = f"gw_{secrets.token_urlsafe(32)}"

            self.api_keys.append(key_data)

            return {"message": "API key created", "api_key_id": key_data.id, "key": key_data.key}

        @router.delete("/api-keys/{key_id}")
        async def delete_api_key(key_id: str):
            """Delete an API key."""
            original_count = len(self.api_keys)
            self.api_keys = [k for k in self.api_keys if k.id != key_id]

            if len(self.api_keys) == original_count:
                raise HTTPException(status_code=404, detail="API key not found")

            return {"message": "API key deleted"}

        # Analytics endpoints
        @router.get("/analytics/overview")
        async def get_analytics_overview():
            """Get analytics overview."""
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            recent_logs = [log for log in self.request_logs if log.timestamp >= last_24h]
            weekly_logs = [log for log in self.request_logs if log.timestamp >= last_7d]

            # Calculate metrics
            total_requests = len(self.request_logs)
            requests_24h = len(recent_logs)
            requests_7d = len(weekly_logs)

            # Error rate
            error_logs_24h = [log for log in recent_logs if log.status_code >= 400]
            error_rate = (len(error_logs_24h) / requests_24h * 100) if requests_24h > 0 else 0

            # Average response time
            avg_response_time = (
                sum(log.response_time for log in recent_logs) / len(recent_logs)
                if recent_logs
                else 0
            )

            # Top endpoints
            endpoint_stats = {}
            for log in recent_logs:
                endpoint_stats[log.path] = endpoint_stats.get(log.path, 0) + 1

            top_endpoints = sorted(endpoint_stats.items(), key=lambda x: x[1], reverse=True)[:5]

            # Status code distribution
            status_codes = {}
            for log in recent_logs:
                status_codes[log.status_code] = status_codes.get(log.status_code, 0) + 1

            return {
                "total_requests": total_requests,
                "requests_24h": requests_24h,
                "requests_7d": requests_7d,
                "error_rate": round(error_rate, 2),
                "avg_response_time": round(avg_response_time, 2),
                "active_endpoints": len([e for e in self.endpoints if e.is_active]),
                "active_api_keys": len([k for k in self.api_keys if k.is_active]),
                "top_endpoints": top_endpoints,
                "status_codes": status_codes,
            }

        @router.get("/analytics/logs")
        async def get_request_logs(
            limit: int = 100,
            offset: int = 0,
            endpoint_id: Optional[str] = None,
            status_code: Optional[int] = None,
        ):
            """Get request logs."""
            filtered_logs = self.request_logs

            if endpoint_id:
                filtered_logs = [log for log in filtered_logs if log.endpoint_id == endpoint_id]
            if status_code:
                filtered_logs = [log for log in filtered_logs if log.status_code == status_code]

            # Sort by timestamp (newest first)
            filtered_logs = sorted(filtered_logs, key=lambda x: x.timestamp, reverse=True)

            total = len(filtered_logs)
            logs = filtered_logs[offset : offset + limit]

            return {
                "logs": [log.dict() for log in logs],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        # Gateway proxy endpoint (handles actual API calls)
        @router.api_route("/proxy/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
        async def proxy_request(request: Request, path: str, background_tasks: BackgroundTasks):
            """Proxy requests to upstream services."""
            start_time = time.time()
            endpoint = None
            api_key = None

            try:
                # Find matching endpoint
                endpoint = self._find_endpoint(path, request.method)
                if not endpoint:
                    raise HTTPException(status_code=404, detail="Endpoint not found")

                if not endpoint.is_active:
                    raise HTTPException(status_code=503, detail="Endpoint is disabled")

                # Authentication check
                api_key = None
                if endpoint.auth_required:
                    api_key = await self._authenticate_request(request, endpoint)

                # Rate limiting
                await self._check_rate_limit(request, endpoint, api_key)

                # Check cache
                cache_key = self._get_cache_key(request, endpoint)
                if endpoint.cache_ttl and request.method == "GET":
                    cached_response = self._get_cached_response(cache_key)
                    if cached_response:
                        # Log cached request
                        background_tasks.add_task(
                            self._log_request,
                            endpoint,
                            api_key,
                            request,
                            200,
                            (time.time() - start_time) * 1000,
                            0,
                            len(cached_response.value),
                            None,
                        )
                        return Response(
                            content=cached_response.value,
                            media_type=cached_response.content_type,
                        )

                # Make upstream request
                response = await self._make_upstream_request(request, endpoint, path)

                # Cache response if configured
                if endpoint.cache_ttl and request.method == "GET" and response.status_code == 200:
                    self._cache_response(
                        cache_key,
                        response.content,
                        response.headers.get("content-type", ""),
                        endpoint.cache_ttl,
                    )

                # Log request
                background_tasks.add_task(
                    self._log_request,
                    endpoint,
                    api_key,
                    request,
                    response.status_code,
                    (time.time() - start_time) * 1000,
                    len(await request.body()) if hasattr(request, "body") else 0,
                    len(response.content),
                    None,
                )

                # Return response
                return Response(
                    content=response.content,
                    status_code=response.status_code,
                    headers=dict(response.headers),
                )

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Proxy error: {str(e)}")

                # Log error
                background_tasks.add_task(
                    self._log_request,
                    endpoint,
                    api_key,
                    request,
                    500,
                    (time.time() - start_time) * 1000,
                    0,
                    0,
                    str(e),
                )

                raise HTTPException(status_code=500, detail="Internal server error")

        # Web UI
        @router.get("/ui", response_class=HTMLResponse)
        async def gateway_ui():
            """Serve the API gateway management UI."""
            return self._get_gateway_html()

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_endpoints": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "path", "unique": True},
                        {"field": "name"},
                        {"field": "is_active"},
                    ]
                },
                f"{self.name}_api_keys": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "key", "unique": True},
                        {"field": "name"},
                        {"field": "is_active"},
                    ]
                },
                f"{self.name}_request_logs": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "endpoint_id"},
                        {"field": "api_key_id"},
                        {"field": "timestamp"},
                        {"field": "status_code"},
                    ]
                },
            }
        }

    # Helper methods
    def _initialize_sample_data(self):
        """Initialize with sample data."""
        # Sample endpoints
        self.endpoints = [
            APIEndpoint(
                name="JSONPlaceholder Posts",
                path="/api/posts",
                upstream_url=HttpUrl("https://jsonplaceholder.typicode.com/posts"),
                methods=["GET"],
                auth_required=False,
                cache_ttl=300,  # 5 minutes
            ),
            APIEndpoint(
                name="JSONPlaceholder Users",
                path="/api/users",
                upstream_url=HttpUrl("https://jsonplaceholder.typicode.com/users"),
                methods=["GET"],
                auth_required=True,
                rate_limit=60,  # 60 requests per minute
                cache_ttl=600,  # 10 minutes
            ),
            APIEndpoint(
                name="HTTPBin API",
                path="/api/httpbin",
                upstream_url=HttpUrl("https://httpbin.org/json"),
                methods=["GET", "POST"],
                auth_required=True,
                rate_limit=30,
            ),
        ]

        # Sample API keys
        self.api_keys = [
            APIKey(
                name="Demo Key",
                key="gw_demo_key_12345678901234567890123456789012",
                endpoints=[endpoint.id for endpoint in self.endpoints],
                rate_limit=100,
            ),
            APIKey(
                name="Test Key",
                key="gw_test_key_98765432109876543210987654321098",
                endpoints=[self.endpoints[0].id] if self.endpoints else [],
                rate_limit=50,
            ),
        ]

    def _find_endpoint(self, path: str, method: str) -> Optional[APIEndpoint]:
        """Find matching endpoint for path and method."""
        for endpoint in self.endpoints:
            if endpoint.path.strip("/") == path.strip("/") and method in endpoint.methods:
                return endpoint
        return None

    async def _authenticate_request(
        self, request: Request, endpoint: APIEndpoint
    ) -> Optional[APIKey]:
        """Authenticate request using API key."""
        # Get API key from header
        api_key = request.headers.get("X-API-Key") or request.headers.get(
            "Authorization", ""
        ).replace("Bearer ", "")

        if not api_key:
            raise HTTPException(status_code=401, detail="API key required")

        # Find API key
        key_obj = next((k for k in self.api_keys if k.key == api_key and k.is_active), None)
        if not key_obj:
            raise HTTPException(status_code=401, detail="Invalid API key")

        # Check if key has access to this endpoint
        if (
            endpoint.id not in key_obj.endpoints and key_obj.endpoints
        ):  # Empty list means access to all
            raise HTTPException(
                status_code=403, detail="API key does not have access to this endpoint"
            )

        # Check expiry
        if key_obj.expires_at and key_obj.expires_at < datetime.utcnow():
            raise HTTPException(status_code=401, detail="API key expired")

        # Update usage
        key_obj.last_used = datetime.utcnow()
        key_obj.usage_count += 1

        return key_obj

    async def _check_rate_limit(
        self, request: Request, endpoint: APIEndpoint, api_key: Optional[APIKey]
    ):
        """Check rate limiting."""
        # Determine rate limit
        rate_limit = None
        if api_key and api_key.rate_limit:
            rate_limit = api_key.rate_limit
        elif endpoint.rate_limit:
            rate_limit = endpoint.rate_limit

        if not rate_limit:
            return

        # Create bucket key
        client_ip = self._get_client_ip(request)
        bucket_key = f"{endpoint.id}:{api_key.id if api_key else client_ip}"

        # Get or create bucket
        if bucket_key not in self.rate_limit_buckets:
            self.rate_limit_buckets[bucket_key] = RateLimitBucket(
                key=bucket_key, requests=[], limit=rate_limit
            )

        bucket = self.rate_limit_buckets[bucket_key]
        now = datetime.utcnow()

        # Clean old requests (older than 1 minute)
        bucket.requests = [req for req in bucket.requests if (now - req).seconds < 60]

        # Check limit
        if len(bucket.requests) >= rate_limit:
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": "60"},
            )

        # Add current request
        bucket.requests.append(now)

    async def _make_upstream_request(
        self, request: Request, endpoint: APIEndpoint, path: str
    ) -> httpx.Response:
        """Make request to upstream service."""
        # Cast request to ensure type checker knows it's not None
        req: Request = cast(Request, request)
        # Use RequestDataExtractor to avoid type checker issues
        req_data = RequestDataExtractor(req)

        # Prepare request data
        method = req_data.method
        headers = req_data.headers.copy()

        # Remove hop-by-hop headers
        headers.pop("host", None)
        headers.pop("connection", None)
        headers.pop("te", None)
        headers.pop("upgrade", None)
        headers.pop("proxy-authenticate", None)
        headers.pop("proxy-authorization", None)

        # Add custom headers
        headers.update(endpoint.headers)

        # Get request body
        body = None
        if method in ["POST", "PUT", "PATCH"]:
            body = await req_data.get_body()

        # Make request using separate method
        return await self._execute_http_request(
            method=method,
            endpoint=endpoint,
            headers=headers,
            body=body,
            query_params=req_data.query_params,
        )

    async def _execute_http_request(
        self,
        method: str,
        endpoint: APIEndpoint,
        headers: Dict[str, str],
        body: Any,
        query_params: Dict[str, Any],
    ) -> Any:
        """Execute HTTP request without type checker issues."""
        upstream_url = str(endpoint.upstream_url)
        if upstream_url.endswith("/"):
            upstream_url = upstream_url[:-1]

        if self.http_client is None:
            raise ValueError("HTTP client is not initialized")

        return await self.http_client.request(
            method=method,
            url=upstream_url,
            headers=headers,
            content=body,
            params=query_params,
        )

    def _get_cache_key(self, request: Request, endpoint: APIEndpoint) -> str:
        """Generate cache key for request."""
        # Cast request to ensure type checker knows it's not None
        req: Request = cast(Request, request)
        # Use RequestDataExtractor to avoid type checker issues
        req_data = RequestDataExtractor(req)

        query_string = str(req_data.query_params) if req_data.query_params else ""
        return f"{endpoint.id}:{req_data.method}:{req_data.url_path}:{hash(query_string)}"

    def _get_cached_response(self, cache_key: str) -> Optional[CacheEntry]:
        """Get cached response if available and not expired."""
        entry = self.cache_entries.get(cache_key)
        if entry and entry.expires_at > datetime.utcnow():
            return entry
        elif entry:
            # Remove expired entry
            del self.cache_entries[cache_key]
        return None

    def _cache_response(self, cache_key: str, content: bytes, content_type: str, ttl: int):
        """Cache response."""
        self.cache_entries[cache_key] = CacheEntry(
            key=cache_key,
            value=content.decode("utf-8", errors="ignore"),
            content_type=content_type,
            expires_at=datetime.utcnow() + timedelta(seconds=ttl),
        )

    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0]
        return request.client.host if request.client else "unknown"

    async def _log_request(
        self,
        endpoint: Optional[APIEndpoint],
        api_key: Optional[APIKey],
        request: Request,
        status_code: int,
        response_time: float,
        request_size: int,
        response_size: int,
        error_message: Optional[str],
    ):
        """Log API request."""
        log = RequestLog(
            endpoint_id=endpoint.id if endpoint else "unknown",
            api_key_id=api_key.id if api_key else None,
            method=request.method,
            path=request.url.path,
            status_code=status_code,
            response_time=response_time,
            request_size=request_size,
            response_size=response_size,
            ip_address=self._get_client_ip(request),
            user_agent=request.headers.get("user-agent", ""),
            error_message=error_message,
        )

        self.request_logs.append(log)

        # Publish event
        await self.publish_event(
            "api_gateway.request.processed",
            {
                "endpoint_id": log.endpoint_id,
                "method": log.method,
                "path": log.path,
                "status_code": log.status_code,
                "response_time": log.response_time,
            },
        )

    async def _cleanup_expired_cache(self):
        """Background task to cleanup expired cache entries."""
        while True:
            try:
                now = datetime.utcnow()
                expired_keys = [
                    key for key, entry in self.cache_entries.items() if entry.expires_at <= now
                ]
                for key in expired_keys:
                    del self.cache_entries[key]

                await asyncio.sleep(300)  # Run every 5 minutes
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
                await asyncio.sleep(300)

    async def _cleanup_old_logs(self):
        """Background task to cleanup old logs."""
        while True:
            try:
                cutoff = datetime.utcnow() - timedelta(days=30)
                self.request_logs = [log for log in self.request_logs if log.timestamp > cutoff]

                await asyncio.sleep(3600)  # Run every hour
            except Exception as e:
                logger.error(f"Log cleanup error: {e}")
                await asyncio.sleep(3600)

    def _get_gateway_html(self) -> str:
        """Generate the API gateway management HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>API Gateway - Nexus Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            color: #334155;
            line-height: 1.6;
        }

        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #0f172a;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .nav {
            display: flex;
            gap: 2rem;
            margin-top: 1rem;
        }

        .nav-item {
            padding: 0.5rem 1rem;
            border-radius: 6px;
            cursor: pointer;
            transition: background-color 0.2s;
        }

        .nav-item:hover {
            background: #f8fafc;
        }

        .nav-item.active {
            background: #3b82f6;
            color: white;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 1rem;
            margin-bottom: 2rem;
        }

        .stat-card {
            background: white;
            padding: 1.5rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            text-align: center;
        }

        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            color: #3b82f6;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: #64748b;
            font-size: 0.9rem;
        }

        .content-section {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 2rem;
        }

        .section-header {
            padding: 1.5rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .section-title {
            font-size: 1.2rem;
            font-weight: 600;
            color: #1e293b;
        }

        .section-content {
            padding: 1.5rem;
        }

        .endpoint-list {
            display: flex;
            flex-direction: column;
            gap: 1rem;
        }

        .endpoint-item {
            display: flex;
            align-items: center;
            padding: 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 6px;
            transition: background-color 0.2s;
        }

        .endpoint-item:hover {
            background-color: #f8fafc;
        }

        .endpoint-info {
            flex: 1;
        }

        .endpoint-name {
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 0.25rem;
        }

        .endpoint-path {
            color: #64748b;
            font-family: 'Monaco', 'Menlo', monospace;
            font-size: 0.9rem;
        }

        .endpoint-methods {
            display: flex;
            gap: 0.25rem;
            margin-top: 0.5rem;
        }

        .method-badge {
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .method-get { background: #dcfce7; color: #16a34a; }
        .method-post { background: #dbeafe; color: #2563eb; }
        .method-put { background: #fef3c7; color: #d97706; }
        .method-delete { background: #fee2e2; color: #dc2626; }

        .status-badge {
            padding: 0.25rem 0.75rem;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
        }

        .status-active { background: #dcfce7; color: #16a34a; }
        .status-inactive { background: #fee2e2; color: #dc2626; }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 1rem;
        }

        .logs-table {
            width: 100%;
            border-collapse: collapse;
        }

        .logs-table th,
        .logs-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        .logs-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
        }

        .logs-table tr:hover {
            background: #f8fafc;
        }

        .status-2xx { color: #16a34a; }
        .status-3xx { color: #d97706; }
        .status-4xx { color: #dc2626; }
        .status-5xx { color: #dc2626; font-weight: bold; }

        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            transition: background-color 0.2s;
        }

        .btn-primary {
            background: #3b82f6;
            color: white;
        }

        .btn-primary:hover {
            background: #2563eb;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }

        .hidden {
            display: none;
        }

        @media (max-width: 768px) {
            .stats-grid {
                grid-template-columns: repeat(2, 1fr);
            }

            .endpoint-item {
                flex-direction: column;
                align-items: flex-start;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🚪 API Gateway</h1>
        <div class="nav">
            <div class="nav-item active" onclick="showSection('overview')">Overview</div>
            <div class="nav-item" onclick="showSection('endpoints')">Endpoints</div>
            <div class="nav-item" onclick="showSection('logs')">Request Logs</div>
        </div>
    </div>

    <div class="container">
        <!-- Overview Section -->
        <div id="overview" class="section">
            <div class="stats-grid" id="statsGrid">
                <div class="stat-card">
                    <div class="stat-value" id="totalRequests">-</div>
                    <div class="stat-label">Total Requests</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="requests24h">-</div>
                    <div class="stat-label">Last 24 Hours</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="errorRate">-</div>
                    <div class="stat-label">Error Rate</div>
                </div>
                <div class="stat-card">
                    <div class="stat-value" id="avgResponseTime">-</div>
                    <div class="stat-label">Avg Response Time (ms)</div>
                </div>
            </div>

            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">Request Analytics</div>
                </div>
                <div class="section-content">
                    <div class="chart-container">
                        <canvas id="requestsChart"></canvas>
                    </div>
                </div>
            </div>
        </div>

        <!-- Endpoints Section -->
        <div id="endpoints" class="section hidden">
            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">API Endpoints</div>
                    <button class="btn btn-primary" onclick="refreshData()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div id="endpointsList" class="loading">Loading endpoints...</div>
                </div>
            </div>
        </div>

        <!-- Logs Section -->
        <div id="logs" class="section hidden">
            <div class="content-section">
                <div class="section-header">
                    <div class="section-title">Request Logs</div>
                    <button class="btn btn-primary" onclick="loadRequestLogs()">🔄 Refresh</button>
                </div>
                <div class="section-content">
                    <div id="logsContainer" class="loading">Loading logs...</div>
                </div>
            </div>
        </div>
    </div>

    <script>
        let requestsChart;

        async function loadDashboard() {
            try {
                const response = await fetch('/plugins/api_gateway/analytics/overview');
                const data = await response.json();

                // Update stats
                document.getElementById('totalRequests').textContent = data.total_requests.toLocaleString();
                document.getElementById('requests24h').textContent = data.requests_24h.toLocaleString();
                document.getElementById('errorRate').textContent = data.error_rate + '%';
                document.getElementById('avgResponseTime').textContent = data.avg_response_time.toFixed(1);

                // Load charts
                await loadRequestsChart(data);
                await loadEndpoints();

            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        async function loadRequestsChart(data) {
            const ctx = document.getElementById('requestsChart').getContext('2d');

            if (requestsChart) {
                requestsChart.destroy();
            }

            // Create chart data from status codes
            const statusData = data.status_codes;
            const labels = Object.keys(statusData);
            const values = Object.values(statusData);
            const colors = labels.map(status => {
                if (status.startsWith('2')) return '#10b981';
                if (status.startsWith('3')) return '#f59e0b';
                if (status.startsWith('4')) return '#ef4444';
                if (status.startsWith('5')) return '#dc2626';
                return '#6b7280';
            });

            requestsChart = new Chart(ctx, {
                type: 'doughnut',
                data: {
                    labels: labels.map(status => `HTTP ${status}`),
                    datasets: [{
                        data: values,
                        backgroundColor: colors,
                        borderWidth: 2,
                        borderColor: '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom' },
                        title: {
                            display: true,
                            text: 'Status Code Distribution (Last 24h)'
                        }
                    }
                }
            });
        }

        async function loadEndpoints() {
            try {
                const response = await fetch('/plugins/api_gateway/endpoints');
                const data = await response.json();
                displayEndpoints(data.endpoints);
            } catch (error) {
                console.error('Error loading endpoints:', error);
                document.getElementById('endpointsList').innerHTML = '<div class="loading">Error loading endpoints</div>';
            }
        }

        function displayEndpoints(endpoints) {
            const container = document.getElementById('endpointsList');

            if (!endpoints || endpoints.length === 0) {
                container.innerHTML = '<div class="loading">No endpoints configured</div>';
                return;
            }

            container.innerHTML = endpoints.map(endpoint => `
                <div class="endpoint-item">
                    <div class="endpoint-info">
                        <div class="endpoint-name">${endpoint.name}</div>
                        <div class="endpoint-path">${endpoint.path}</div>
                        <div class="endpoint-methods">
                            ${endpoint.methods.map(method =>
                                `<span class="method-badge method-${method.toLowerCase()}">${method}</span>`
                            ).join('')}
                        </div>
                    </div>
                    <div>
                        <span class="status-badge ${endpoint.is_active ? 'status-active' : 'status-inactive'}">
                            ${endpoint.is_active ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                </div>
            `).join('');
        }

        async function loadRequestLogs() {
            try {
                const response = await fetch('/plugins/api_gateway/analytics/logs?limit=50');
                const data = await response.json();
                displayRequestLogs(data.logs);
            } catch (error) {
                console.error('Error loading logs:', error);
                document.getElementById('logsContainer').innerHTML = '<div class="loading">Error loading logs</div>';
            }
        }

        function displayRequestLogs(logs) {
            const container = document.getElementById('logsContainer');

            if (!logs || logs.length === 0) {
                container.innerHTML = '<div class="loading">No request logs found</div>';
                return;
            }

            const table = `
                <table class="logs-table">
                    <thead>
                        <tr>
                            <th>Timestamp</th>
                            <th>Method</th>
                            <th>Path</th>
                            <th>Status</th>
                            <th>Response Time</th>
                            <th>IP Address</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${logs.map(log => `
                            <tr>
                                <td>${formatTime(log.timestamp)}</td>
                                <td><span class="method-badge method-${log.method.toLowerCase()}">${log.method}</span></td>
                                <td><code>${log.path}</code></td>
                                <td><span class="status-${Math.floor(log.status_code / 100)}xx">${log.status_code}</span></td>
                                <td>${log.response_time.toFixed(1)}ms</td>
                                <td>${log.ip_address}</td>
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            `;

            container.innerHTML = table;
        }

        function showSection(sectionName) {
            // Hide all sections
            document.querySelectorAll('.section').forEach(section => {
                section.classList.add('hidden');
            });

            // Remove active class from nav items
            document.querySelectorAll('.nav-item').forEach(item => {
                item.classList.remove('active');
            });

            // Show selected section
            document.getElementById(sectionName).classList.remove('hidden');

            // Add active class to clicked nav item
            event.target.classList.add('active');

            // Load section-specific data
            if (sectionName === 'logs') {
                loadRequestLogs();
            }
        }

        function formatTime(timestamp) {
            return new Date(timestamp).toLocaleString();
        }

        function refreshData() {
            loadDashboard();
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', loadDashboard);

        // Auto-refresh overview every 30 seconds
        setInterval(() => {
            if (!document.getElementById('overview').classList.contains('hidden')) {
                loadDashboard();
            }
        }, 30000);
    </script>
</body>
</html>
        """
