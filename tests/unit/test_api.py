"""
Unit tests for the Nexus API module.

Tests cover existing API response models and router functionality.
"""

from datetime import datetime

import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from nexus.api import APIResponse, ErrorResponse, HealthResponse, create_api_router


class TestAPIResponse:
    """Test APIResponse model."""

    def test_api_response_default(self):
        """Test APIResponse with default values."""
        response = APIResponse()
        assert response.success == True
        assert response.message == "OK"
        assert response.data is None
        assert isinstance(response.timestamp, datetime)

    def test_api_response_custom(self):
        """Test APIResponse with custom values."""
        data = {"key": "value"}
        response = APIResponse(success=False, message="Error occurred", data=data)
        assert response.success == False
        assert response.message == "Error occurred"
        assert response.data == data

    def test_api_response_serialization(self):
        """Test APIResponse can be serialized."""
        response = APIResponse(data={"test": True})
        response_dict = response.dict()
        assert "success" in response_dict
        assert "message" in response_dict
        assert "data" in response_dict
        assert "timestamp" in response_dict


class TestHealthResponse:
    """Test HealthResponse model."""

    def test_health_response_default(self):
        """Test HealthResponse with default values."""
        response = HealthResponse()
        assert response.status == "healthy"
        assert response.version == "2.0.0"
        assert isinstance(response.timestamp, datetime)
        assert response.services == {}
        assert response.uptime is None

    def test_health_response_custom(self):
        """Test HealthResponse with custom values."""
        services = {"database": "ok", "redis": "ok"}
        response = HealthResponse(
            status="degraded", version="1.0.0", services=services, uptime=3600.5
        )
        assert response.status == "degraded"
        assert response.version == "1.0.0"
        assert response.services == services
        assert response.uptime == 3600.5

    def test_health_response_with_services(self):
        """Test HealthResponse with service status."""
        services = {"database": "healthy", "cache": "degraded", "queue": "unhealthy"}
        response = HealthResponse(services=services)
        assert len(response.services) == 3
        assert response.services["database"] == "healthy"
        assert response.services["cache"] == "degraded"


class TestErrorResponse:
    """Test ErrorResponse model."""

    def test_error_response_basic(self):
        """Test ErrorResponse with basic values."""
        response = ErrorResponse(error="VALIDATION_ERROR", message="Invalid input provided")
        assert response.success == False
        assert response.error == "VALIDATION_ERROR"
        assert response.message == "Invalid input provided"
        assert isinstance(response.timestamp, datetime)
        assert response.details is None

    def test_error_response_with_details(self):
        """Test ErrorResponse with details."""
        details = {"field": "email", "reason": "invalid format"}
        response = ErrorResponse(
            error="FIELD_ERROR", message="Field validation failed", details=details
        )
        assert response.details == details
        assert response.details["field"] == "email"

    def test_error_response_serialization(self):
        """Test ErrorResponse can be serialized."""
        response = ErrorResponse(error="TEST_ERROR", message="Test error message")
        response_dict = response.dict()
        assert response_dict["success"] == False
        assert "error" in response_dict
        assert "message" in response_dict
        assert "timestamp" in response_dict


class TestCreateAPIRouter:
    """Test create_api_router function."""

    def test_create_api_router(self):
        """Test creating API router."""
        router = create_api_router()
        assert isinstance(router, APIRouter)
        assert router.prefix == "/api"
        assert "core" in router.tags

    def test_api_router_has_routes(self):
        """Test API router has expected routes."""
        router = create_api_router()
        route_paths = [route.path for route in router.routes]

        # Should have health endpoint
        assert any("/health" in path for path in route_paths)

    def test_api_router_health_endpoint(self):
        """Test health endpoint functionality."""
        from fastapi import FastAPI

        app = FastAPI()
        router = create_api_router()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data

    def test_api_router_response_format(self):
        """Test API router response format."""
        from fastapi import FastAPI

        app = FastAPI()
        router = create_api_router()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/health")

        data = response.json()
        # Should match HealthResponse model structure
        assert "status" in data
        assert "version" in data
        assert "timestamp" in data
        assert "services" in data


class TestAPIIntegration:
    """Test API integration scenarios."""

    def test_api_response_models_compatibility(self):
        """Test that response models work together."""
        # APIResponse with HealthResponse data
        health_data = HealthResponse(status="healthy")
        api_response = APIResponse(data=health_data.dict())

        assert api_response.success == True
        assert api_response.data["status"] == "healthy"

    def test_error_response_in_api_response(self):
        """Test using ErrorResponse within APIResponse."""
        error_data = ErrorResponse(error="TEST_ERROR", message="Test error")
        api_response = APIResponse(
            success=False, message="Operation failed", data=error_data.dict()
        )

        assert api_response.success == False
        assert api_response.data["error"] == "TEST_ERROR"

    def test_multiple_api_routers(self):
        """Test multiple API routers can be created."""
        router1 = create_api_router()
        router2 = create_api_router()

        assert router1 is not router2
        assert router1.prefix == router2.prefix
        assert router1.tags == router2.tags

    def test_api_router_with_fastapi_app(self):
        """Test API router integration with FastAPI app."""
        from fastapi import FastAPI

        app = FastAPI()
        router = create_api_router()

        # Should be able to include router without errors
        app.include_router(router)

        # App should have the router's routes
        all_routes = [route.path for route in app.routes]
        assert any("/api/health" in path for path in all_routes)

    def test_api_response_timestamp_format(self):
        """Test API response timestamp is properly formatted."""
        response = APIResponse()

        # Timestamp should be a datetime object
        assert isinstance(response.timestamp, datetime)

        # Should be serializable to dict
        response_dict = response.dict()
        assert "timestamp" in response_dict

        # Timestamp should be properly formatted when serialized
        timestamp_str = response.json()
        assert "timestamp" in timestamp_str


class TestAPIUtilities:
    """Test API utility functions."""

    def test_validate_api_key_valid(self):
        """Test validate_api_key with valid key."""
        from nexus.api import validate_api_key

        result = validate_api_key("demo-api-key")
        assert result == True

    def test_validate_api_key_invalid(self):
        """Test validate_api_key with invalid key."""
        from nexus.api import validate_api_key

        result = validate_api_key("invalid-key")
        assert result == False

    def test_validate_api_key_none(self):
        """Test validate_api_key with None."""
        from nexus.api import validate_api_key

        result = validate_api_key(None)
        assert result == False

    def test_validate_api_key_empty(self):
        """Test validate_api_key with empty string."""
        from nexus.api import validate_api_key

        result = validate_api_key("")
        assert result == False

    def test_require_api_key_valid(self):
        """Test require_api_key with valid key."""
        import asyncio

        from nexus.api import require_api_key

        # Should not raise exception
        async def test_func():
            await require_api_key("demo-api-key")

        asyncio.run(test_func())

    def test_require_api_key_invalid(self):
        """Test require_api_key with invalid key."""
        import asyncio

        from fastapi import HTTPException

        from nexus.api import require_api_key

        async def test_func():
            with pytest.raises(HTTPException) as exc_info:
                await require_api_key("invalid-key")

            assert exc_info.value.status_code == 401
            assert "Invalid or missing API key" in str(exc_info.value.detail)

        asyncio.run(test_func())

    def test_require_api_key_none(self):
        """Test require_api_key with None."""
        import asyncio

        from fastapi import HTTPException

        from nexus.api import require_api_key

        async def test_func():
            with pytest.raises(HTTPException) as exc_info:
                await require_api_key(None)

            assert exc_info.value.status_code == 401

        asyncio.run(test_func())


class TestAPIRouterEndpoints:
    """Test API router endpoints for coverage."""

    def test_router_info_endpoint(self):
        """Test the /info endpoint."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        router = create_api_router()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/info")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "name" in data["data"]
        assert data["data"]["name"] == "Nexus Framework"
        assert data["data"]["version"] == "2.0.0"
        assert "documentation" in data["data"]
        assert "repository" in data["data"]

    def test_router_status_endpoint(self):
        """Test the /status endpoint."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        router = create_api_router()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/status")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "status" in data["data"]
        assert data["data"]["status"] == "running"
        assert "uptime" in data["data"]
        assert "plugins_loaded" in data["data"]
        assert "active_connections" in data["data"]
        assert "memory_usage" in data["data"]
        assert "cpu_usage" in data["data"]

    def test_router_version_endpoint(self):
        """Test the /version endpoint."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        app = FastAPI()
        router = create_api_router()
        app.include_router(router)

        client = TestClient(app)
        response = client.get("/api/version")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] == True
        assert "version" in data["data"]
        assert data["data"]["version"] == "2.0.0"
        assert "build" in data["data"]
        assert "release_date" in data["data"]
        assert "python_version" in data["data"]
        assert "framework" in data["data"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
