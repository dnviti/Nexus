"""
Nexus Framework Middleware Module
Basic middleware components for request/response processing.
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import Response
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class ErrorHandlerMiddleware:
    """Middleware for handling errors and exceptions."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.error(f"Unhandled error: {exc}", exc_info=True)

            response = JSONResponse(
                status_code=500,
                content={
                    "success": False,
                    "error": "Internal Server Error",
                    "message": "An unexpected error occurred",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await response(scope, receive, send)


class LoggingMiddleware:
    """Middleware for request/response logging."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        # Log request
        method = scope.get("method", "")
        path = scope.get("path", "")
        client_ip = scope.get("client", ["unknown", 0])[0]

        logger.info(f"Request: {method} {path} from {client_ip}")

        async def send_wrapper(message: Any) -> None:
            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = time.time() - start_time
                logger.info(f"Response: {status_code} for {method} {path} in {process_time:.3f}s")
            await send(message)

        await self.app(scope, receive, send_wrapper)


class RateLimitMiddleware:
    """Basic rate limiting middleware."""

    def __init__(self, app: Any, requests_per_minute: int = 60) -> None:
        self.app = app
        self.requests_per_minute = requests_per_minute
        self.request_counts: Dict[str, List[float]] = {}

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        client_ip = scope.get("client", ["unknown", 0])[0]
        current_time = time.time()

        # Clean old requests
        if client_ip in self.request_counts:
            self.request_counts[client_ip] = [
                req_time
                for req_time in self.request_counts[client_ip]
                if current_time - req_time < 60  # Keep requests from last minute
            ]
        else:
            self.request_counts[client_ip] = []

        # Check rate limit
        if len(self.request_counts[client_ip]) >= self.requests_per_minute:
            response = JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "error": "Rate Limit Exceeded",
                    "message": f"Maximum {self.requests_per_minute} requests per minute",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )
            await response(scope, receive, send)
            return

        # Add current request
        self.request_counts[client_ip].append(current_time)

        await self.app(scope, receive, send)


class CORSMiddleware:
    """Basic CORS middleware."""

    def __init__(
        self,
        app: Any,
        allow_origins: Optional[List[str]] = None,
        allow_methods: Optional[List[str]] = None,
        allow_headers: Optional[List[str]] = None,
    ):
        self.app = app
        self.allow_origins = allow_origins or ["*"]
        self.allow_methods = allow_methods or ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
        self.allow_headers = allow_headers or ["*"]

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        method = scope.get("method", "")

        # Handle preflight requests
        if method == "OPTIONS":
            response = Response(status_code=200)
            response.headers["Access-Control-Allow-Origin"] = ", ".join(self.allow_origins)
            response.headers["Access-Control-Allow-Methods"] = ", ".join(self.allow_methods)
            response.headers["Access-Control-Allow-Headers"] = ", ".join(self.allow_headers)
            await response(scope, receive, send)
            return

        async def send_wrapper(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"access-control-allow-origin"] = ", ".join(self.allow_origins).encode()
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send)


class SecurityMiddleware:
    """Basic security headers middleware."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))

                # Add security headers
                headers[b"x-content-type-options"] = b"nosniff"
                headers[b"x-frame-options"] = b"DENY"
                headers[b"x-xss-protection"] = b"1; mode=block"
                headers[b"strict-transport-security"] = b"max-age=31536000; includeSubDomains"

                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send)


class TimingMiddleware:
    """Middleware for adding response timing headers."""

    def __init__(self, app: Any) -> None:
        self.app = app

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.time()

        async def send_wrapper(message: Any) -> None:
            if message["type"] == "http.response.start":
                process_time = time.time() - start_time
                headers = dict(message.get("headers", []))
                headers[b"x-process-time"] = f"{process_time:.6f}".encode()
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send)


class RequestIDMiddleware:
    """Middleware for adding unique request IDs."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.request_counter = 0

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Generate unique request ID
        self.request_counter += 1
        request_id = f"req_{int(time.time())}_{self.request_counter}"

        # Add to scope for access in handlers
        scope["request_id"] = request_id

        async def send_wrapper(message: Any) -> None:
            if message["type"] == "http.response.start":
                headers = dict(message.get("headers", []))
                headers[b"x-request-id"] = request_id.encode()
                message["headers"] = list(headers.items())
            await send(message)

        await self.app(scope, receive, send_wrapper)


__all__ = [
    "ErrorHandlerMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "CORSMiddleware",
    "SecurityMiddleware",
    "TimingMiddleware",
    "RequestIDMiddleware",
]
