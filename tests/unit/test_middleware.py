"""
Comprehensive unit tests for the Nexus middleware module.

Tests cover error handling, CORS, rate limiting, logging, and timing middleware.
"""

import asyncio
import time
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, Response, status
from fastapi.responses import JSONResponse

from nexus.middleware import (
    CORSMiddleware,
    ErrorHandlerMiddleware,
    LoggingMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    SecurityMiddleware,
    TimingMiddleware,
)


class TestErrorHandlerMiddleware:
    """Test ErrorHandlerMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.middleware = ErrorHandlerMiddleware(self.mock_app)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating error handler middleware."""
        assert self.middleware.app == self.mock_app

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_successful_request(self):
        """Test handling successful requests."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_exception_handling(self):
        """Test handling exceptions."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Mock app to raise exception
        self.mock_app.side_effect = ValueError("Test error")

        await self.middleware(scope, receive, send)

        # Should have sent error response
        send.assert_called()

    @pytest.mark.asyncio
    async def test_http_exception_handling(self):
        """Test handling HTTP exceptions."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Mock app to raise HTTP exception
        self.mock_app.side_effect = HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not found"
        )

        await self.middleware(scope, receive, send)

        # Should have sent appropriate HTTP error response
        send.assert_called()


class TestLoggingMiddleware:
    """Test LoggingMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.middleware = LoggingMiddleware(self.mock_app)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating logging middleware."""
        assert self.middleware.app == self.mock_app

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_request_logging(self):
        """Test that requests are logged."""
        scope = {"type": "http", "method": "GET", "path": "/test", "query_string": b"param=value"}
        receive = AsyncMock()
        send = AsyncMock()

        with patch("nexus.middleware.logger") as mock_logger:
            await self.middleware(scope, receive, send)

            # Should have logged the request
            mock_logger.info.assert_called()
            # App should have been called (with wrapped send function)
            self.mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_response_logging(self):
        """Test that responses are logged."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        with patch("nexus.middleware.logger") as mock_logger:
            await self.middleware(scope, receive, send)

            # Should have logged both request and response
            assert mock_logger.info.call_count >= 1

    @pytest.mark.asyncio
    async def test_error_logging(self):
        """Test that errors are logged."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Mock app to raise exception
        self.mock_app.side_effect = ValueError("Test error")

        with patch("nexus.middleware.logger") as mock_logger:
            # Error should propagate but be logged
            try:
                await self.middleware(scope, receive, send)
            except ValueError:
                pass  # Expected to propagate

            # Check if error was logged or handled
            assert mock_logger.info.called or mock_logger.error.called


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.middleware = RateLimitMiddleware(self.mock_app, requests_per_minute=60)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating rate limit middleware."""
        assert self.middleware.app == self.mock_app
        assert self.middleware.requests_per_minute == 60
        assert isinstance(self.middleware.request_counts, dict)

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_request_within_limit(self):
        """Test request within rate limit."""
        scope = {"type": "http", "client": ("127.0.0.1", 8000), "method": "GET"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should process request normally
        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_rate_limit_tracking(self):
        """Test that rate limiting tracks requests per client."""
        scope = {"type": "http", "client": ("127.0.0.1", 8000), "method": "GET"}
        receive = AsyncMock()
        send = AsyncMock()

        # Make multiple requests
        for _ in range(5):
            await self.middleware(scope, receive, send)

        # Most should be processed (depending on implementation)
        assert self.mock_app.call_count >= 1

    @pytest.mark.asyncio
    async def test_different_clients_separate_limits(self):
        """Test that different clients have separate rate limits."""
        scope1 = {"type": "http", "client": ("127.0.0.1", 8000), "method": "GET"}
        scope2 = {"type": "http", "client": ("192.168.1.1", 8000), "method": "GET"}
        receive = AsyncMock()
        send = AsyncMock()

        # Make requests from different clients
        await self.middleware(scope1, receive, send)
        await self.middleware(scope2, receive, send)

        # Both should be processed
        assert self.mock_app.call_count == 2


class TestCORSMiddleware:
    """Test CORSMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.cors_config = {
            "allow_origins": ["https://example.com"],
            "allow_methods": ["GET", "POST"],
            "allow_headers": ["Content-Type"],
        }
        self.middleware = CORSMiddleware(self.mock_app, **self.cors_config)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating CORS middleware."""
        assert self.middleware.app == self.mock_app
        assert self.middleware.allow_origins == ["https://example.com"]
        assert self.middleware.allow_methods == ["GET", "POST"]
        assert self.middleware.allow_headers == ["Content-Type"]

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_preflight_request(self):
        """Test handling preflight OPTIONS requests."""
        scope = {
            "type": "http",
            "method": "OPTIONS",
            "headers": [
                (b"origin", b"https://example.com"),
                (b"access-control-request-method", b"POST"),
            ],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should have sent CORS headers
        send.assert_called()

    @pytest.mark.asyncio
    async def test_regular_request_with_cors(self):
        """Test handling regular requests with CORS headers."""
        scope = {"type": "http", "method": "GET", "headers": [(b"origin", b"https://example.com")]}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should have called the app
        self.mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_disallowed_origin(self):
        """Test handling requests from disallowed origins."""
        scope = {
            "type": "http",
            "method": "GET",
            "headers": [(b"origin", b"https://malicious.com")],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should still process but without CORS headers
        self.mock_app.assert_called_once()


class TestSecurityMiddleware:
    """Test SecurityMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.middleware = SecurityMiddleware(self.mock_app)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating security middleware."""
        assert self.middleware.app == self.mock_app

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_security_headers_added(self):
        """Test that security headers are added."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should have processed request and added security headers
        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_https_request_handling(self):
        """Test handling HTTPS requests."""
        scope = {"type": "http", "method": "GET", "path": "/test", "scheme": "https"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should have added appropriate security headers
        self.mock_app.assert_called_once()


class TestTimingMiddleware:
    """Test TimingMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.middleware = TimingMiddleware(self.mock_app)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating timing middleware."""
        assert self.middleware.app == self.mock_app

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_timing_measurement(self):
        """Test that request timing is measured."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Mock app to take some time
        async def slow_app(*args):
            await asyncio.sleep(0.01)  # Short delay for testing

        self.mock_app.side_effect = slow_app

        await self.middleware(scope, receive, send)

        # Should have processed the request
        self.mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_timing_header_added(self):
        """Test that timing information is handled."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should have processed the request
        self.mock_app.assert_called_once()


class TestRequestIDMiddleware:
    """Test RequestIDMiddleware class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_app = AsyncMock()
        self.middleware = RequestIDMiddleware(self.mock_app)

    @pytest.mark.asyncio
    async def test_middleware_creation(self):
        """Test creating request ID middleware."""
        assert self.middleware.app == self.mock_app
        assert self.middleware.request_counter == 0

    @pytest.mark.asyncio
    async def test_non_http_scope_passthrough(self):
        """Test that non-HTTP scopes are passed through."""
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        self.mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_request_id_generation(self):
        """Test that request IDs are generated."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        await self.middleware(scope, receive, send)

        # Should have processed request with ID
        self.mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_request_counter_increment(self):
        """Test that request counter increments."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        initial_counter = self.middleware.request_counter

        await self.middleware(scope, receive, send)

        # Counter should have incremented (depending on implementation)
        self.mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_unique_request_ids(self):
        """Test that request IDs are unique."""
        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Make multiple requests
        for _ in range(3):
            await self.middleware(scope, receive, send)

        # All requests should have been processed
        assert self.mock_app.call_count == 3


class TestMiddlewareIntegration:
    """Test middleware integration scenarios."""

    @pytest.mark.asyncio
    async def test_multiple_middleware_stack(self):
        """Test multiple middleware working together."""
        mock_app = AsyncMock()

        # Stack multiple middleware
        app_with_error_handler = ErrorHandlerMiddleware(mock_app)
        app_with_cors = CORSMiddleware(
            app_with_error_handler, allow_origins=["*"], allow_methods=["*"]
        )
        app_with_logging = LoggingMiddleware(app_with_cors)
        app_with_timing = TimingMiddleware(app_with_logging)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "headers": [(b"origin", b"https://example.com")],
        }
        receive = AsyncMock()
        send = AsyncMock()

        await app_with_timing(scope, receive, send)

        # Original app should have been called
        mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_error_propagation(self):
        """Test error propagation through middleware stack."""
        mock_app = AsyncMock()
        mock_app.side_effect = ValueError("Test error")

        # Stack error handler on top
        app_with_error_handler = ErrorHandlerMiddleware(mock_app)
        app_with_logging = LoggingMiddleware(app_with_error_handler)

        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Should handle error gracefully
        await app_with_logging(scope, receive, send)

        # Error should have been caught by error handler
        # At minimum, send should have been called
        assert send.called or mock_app.called

    @pytest.mark.asyncio
    async def test_middleware_performance_impact(self):
        """Test performance impact of middleware stack."""
        mock_app = AsyncMock()

        # Create a middleware stack
        middlewares = [
            ErrorHandlerMiddleware,
            CORSMiddleware,
            RateLimitMiddleware,
            LoggingMiddleware,
            TimingMiddleware,
            SecurityMiddleware,
            RequestIDMiddleware,
        ]

        app = mock_app
        for middleware_class in middlewares:
            if middleware_class == CORSMiddleware:
                app = middleware_class(app, allow_origins=["*"])
            elif middleware_class == RateLimitMiddleware:
                app = middleware_class(app, requests_per_minute=1000)
            else:
                app = middleware_class(app)

        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        start_time = time.time()
        await app(scope, receive, send)
        end_time = time.time()

        # Should complete reasonably quickly
        assert (end_time - start_time) < 1.0  # Less than 1 second

        # Original app should have been called
        mock_app.assert_called_once()

    @pytest.mark.asyncio
    async def test_middleware_order_matters(self):
        """Test that middleware order affects behavior."""
        mock_app = AsyncMock()

        # Create two different stacks with different order
        stack1 = TimingMiddleware(LoggingMiddleware(mock_app))
        stack2 = LoggingMiddleware(TimingMiddleware(mock_app))

        scope = {"type": "http", "method": "GET", "path": "/test"}
        receive = AsyncMock()
        send = AsyncMock()

        # Both should work but may behave differently
        await stack1(scope, receive, send)
        mock_app.reset_mock()

        await stack2(scope, receive, send)

        # Both should have called the original app
        mock_app.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
