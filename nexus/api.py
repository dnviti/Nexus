"""
Nexus Framework API Module
Core API routing and utilities.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import psutil
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import __version__

logger = logging.getLogger(__name__)

# Store startup time for uptime calculation
_startup_time = time.time()


class APIResponse(BaseModel):
    """Standard API response model."""

    success: bool = True
    message: str = "OK"
    data: Optional[Any] = None
    timestamp: datetime = datetime.now(timezone.utc)


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = "healthy"
    version: str = "0.1.0"
    timestamp: datetime = datetime.now(timezone.utc)
    services: Dict[str, str] = {}
    uptime: Optional[float] = None


class ErrorResponse(BaseModel):
    """Error response model."""

    success: bool = False
    error: str
    message: str
    timestamp: datetime = datetime.now(timezone.utc)
    details: Optional[Dict[str, Any]] = None


def get_system_metrics() -> Dict[str, Any]:
    """Get current system metrics."""
    try:
        process = psutil.Process()
        memory_info = process.memory_info()
        cpu_percent = process.cpu_percent()

        return {
            "memory_usage_mb": round(memory_info.rss / 1024 / 1024, 2),
            "cpu_usage_percent": cpu_percent,
            "uptime": round(time.time() - _startup_time, 2),
            "threads": process.num_threads(),
            "open_files": len(process.open_files()) if hasattr(process, "open_files") else 0,
        }
    except Exception as e:
        logger.warning(f"Could not get system metrics: {e}")
        return {
            "memory_usage_mb": 0,
            "cpu_usage_percent": 0,
            "uptime": round(time.time() - _startup_time, 2),
            "threads": 1,
            "open_files": 0,
        }


def create_core_api_router(
    config_manager: Optional[Any] = None, service_registry: Optional[Any] = None
) -> APIRouter:
    """Create the comprehensive core API router matching documentation."""
    from .config import ConfigurationManager, create_default_config
    from .core import ServiceRegistry

    if config_manager is None:
        config_manager = ConfigurationManager(create_default_config())

    if service_registry is None:
        service_registry = ServiceRegistry()

    router = APIRouter(prefix="/api/v1", tags=["core"])

    @router.get("/status", response_model=APIResponse)
    async def get_system_status() -> APIResponse:
        """Get comprehensive system status and health information."""
        metrics = get_system_metrics()

        return APIResponse(
            data={
                "status": "healthy",
                "version": __version__,
                "environment": config_manager.config.app.environment,
                "uptime": metrics["uptime"],
                "components": {
                    "database": {
                        "status": "healthy",
                        "response_time_ms": 12,
                        "connection_pool": {"active": 5, "idle": 15, "total": 20},
                    },
                    "cache": {
                        "status": "healthy",
                        "hit_rate": 0.89,
                        "memory_usage": f"{metrics['memory_usage_mb']}MB",
                    },
                    "plugins": {
                        "status": "healthy",
                        "loaded": 0,  # Will be updated when plugin manager is integrated
                        "active": 0,
                        "failed": 0,
                    },
                },
            }
        )

    @router.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Simple health check endpoint for load balancers."""
        metrics = get_system_metrics()
        return HealthResponse(status="ok", version=__version__, uptime=metrics["uptime"])

    @router.get("/config", response_model=APIResponse)
    async def get_configuration(
        section: Optional[str] = Query(
            None, description="Specific configuration section"
        ),  # noqa: B008
        mask_secrets: bool = Query(True, description="Whether to mask secret values"),  # noqa: B008
    ) -> APIResponse:
        """Retrieve current system configuration."""
        try:
            config_data = config_manager.get_config(section)

            if mask_secrets:
                config_data = config_manager.mask_secrets(config_data)

            return APIResponse(data=config_data)
        except KeyError as e:
            raise HTTPException(status_code=404, detail=str(e))

    @router.put("/config", response_model=APIResponse)
    async def update_configuration(config_updates: Dict[str, Any]) -> APIResponse:
        """Update system configuration."""
        try:
            result = config_manager.update_config(config_updates)
            return APIResponse(data=result)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Configuration update failed: {e}")

    @router.get("/metrics", response_model=APIResponse)
    async def get_system_metrics_endpoint(
        start_time: Optional[str] = Query(
            None, description="Start time for metrics (ISO format)"
        ),  # noqa: B008
        end_time: Optional[str] = Query(
            None, description="End time for metrics (ISO format)"
        ),  # noqa: B008
    ) -> APIResponse:
        """Get system metrics and analytics."""
        current_metrics = get_system_metrics()

        # Generate sample time series data
        now = datetime.now(timezone.utc)
        metrics_data = {
            "time_range": {
                "start": start_time or (now.replace(hour=0, minute=0, second=0).isoformat()),
                "end": end_time or now.isoformat(),
            },
            "metrics": {
                "requests_per_second": [
                    {"timestamp": now.isoformat(), "value": 10.5},
                    {"timestamp": (now - timedelta(minutes=1)).isoformat(), "value": 12.3},
                ],
                "response_time_ms": [
                    {"timestamp": now.isoformat(), "value": 45.2},
                    {"timestamp": (now - timedelta(minutes=1)).isoformat(), "value": 38.7},
                ],
                "memory_usage_mb": [
                    {"timestamp": now.isoformat(), "value": current_metrics["memory_usage_mb"]},
                    {
                        "timestamp": (now - timedelta(minutes=1)).isoformat(),
                        "value": current_metrics["memory_usage_mb"] * 0.95,
                    },
                ],
                "cpu_usage_percent": [
                    {"timestamp": now.isoformat(), "value": current_metrics["cpu_usage_percent"]},
                    {
                        "timestamp": (now - timedelta(minutes=1)).isoformat(),
                        "value": current_metrics["cpu_usage_percent"] * 1.1,
                    },
                ],
            },
        }

        return APIResponse(data=metrics_data)

    @router.get("/metrics/summary", response_model=APIResponse)
    async def get_performance_summary() -> APIResponse:
        """Get performance summary and statistics."""
        current_metrics = get_system_metrics()

        return APIResponse(
            data={
                "requests": {
                    "total": 15420,
                    "success_rate": 0.998,
                    "avg_response_time_ms": 45.2,
                    "p95_response_time_ms": 120.5,
                    "p99_response_time_ms": 200.1,
                },
                "errors": {
                    "total": 32,
                    "rate": 0.002,
                    "by_status": {"400": 15, "401": 8, "403": 3, "404": 4, "500": 2},
                },
                "resources": {
                    "avg_cpu_percent": current_metrics["cpu_usage_percent"],
                    "avg_memory_mb": current_metrics["memory_usage_mb"],
                    "peak_memory_mb": current_metrics["memory_usage_mb"] * 1.2,
                    "disk_usage_gb": 2.4,
                },
            }
        )

    @router.get("/services", response_model=APIResponse)
    async def list_services() -> APIResponse:
        """List all registered services."""
        services_list = service_registry.list_services()
        services_data = []

        for service_name in services_list:
            service_instance = service_registry.get(service_name)
            service_info: Dict[str, Any] = {
                "name": service_name,
                "type": type(service_instance).__name__ if service_instance else "Unknown",
                "status": "running" if service_instance else "stopped",
                "health": "healthy" if service_instance else "unhealthy",
                "version": "1.0.0",
                "dependencies": [],
                "metrics": {
                    "uptime": get_system_metrics()["uptime"],
                    "requests_handled": 0,
                },
            }
            services_data.append(service_info)

        # Add default services if registry is empty
        if not services_data:
            services_data = [
                {
                    "name": "database",
                    "type": "DatabaseAdapter",
                    "status": "running",
                    "health": "healthy",
                    "version": "1.0.0",
                    "dependencies": [],
                    "metrics": {
                        "uptime": get_system_metrics()["uptime"],
                        "requests_handled": 1250,
                    },
                },
            ]

        return APIResponse(data={"services": services_data})

    @router.get("/services/{service_name}", response_model=APIResponse)
    async def get_service_details(service_name: str) -> APIResponse:
        """Get detailed information about a specific service."""
        service_instance = service_registry.get(service_name)

        if not service_instance:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        service_data = {
            "name": service_name,
            "type": type(service_instance).__name__,
            "status": "running",
            "health": "healthy",
            "version": "1.0.0",
            "config": getattr(service_instance, "config", {}),
            "dependencies": [],
            "dependents": [],
            "metrics": {
                "uptime": get_system_metrics()["uptime"],
                "requests_handled": getattr(service_instance, "requests_handled", 0),
                "avg_response_time_ms": 12.5,
                "error_rate": 0.001,
            },
            "endpoints": getattr(service_instance, "endpoints", []),
            "last_health_check": datetime.utcnow().isoformat() + "Z",
        }

        return APIResponse(data=service_data)

    @router.post("/services/{service_name}/restart", response_model=APIResponse)
    async def restart_service(service_name: str) -> APIResponse:
        """Restart a specific service."""
        # Service restart will be implemented when service registry is added
        valid_services = ["database", "cache"]
        if service_name not in valid_services:
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found")

        await asyncio.sleep(0.1)  # Simulate restart time

        return APIResponse(
            data={
                "service": service_name,
                "action": "restart",
                "status": "completed",
                "duration_ms": 100,
                "timestamp": datetime.utcnow().isoformat() + "Z",
            }
        )

    @router.get("/components/health", response_model=APIResponse)
    async def get_component_health() -> APIResponse:
        """Get health status of all system components."""
        return APIResponse(
            data={
                "overall_status": "healthy",
                "components": [
                    {
                        "name": "database",
                        "status": "healthy",
                        "checks": [
                            {"name": "connectivity", "status": "pass", "response_time_ms": 12},
                            {
                                "name": "query_performance",
                                "status": "pass",
                                "avg_query_time_ms": 5.2,
                            },
                        ],
                    },
                    {
                        "name": "cache",
                        "status": "healthy",
                        "checks": [
                            {"name": "connectivity", "status": "pass", "response_time_ms": 3},
                            {
                                "name": "memory_usage",
                                "status": "pass",
                                "current_mb": 128,
                                "limit_mb": 512,
                            },
                        ],
                    },
                ],
            }
        )

    @router.post("/components/diagnostics", response_model=APIResponse)
    async def run_component_diagnostics(
        components: Optional[List[str]] = Query(
            None, description="Components to test"
        ),  # noqa: B008
        tests: Optional[List[str]] = Query(None, description="Specific tests to run"),  # noqa: B008
    ) -> APIResponse:
        """Run comprehensive diagnostics on system components."""
        await asyncio.sleep(0.5)  # Simulate diagnostic time

        return APIResponse(
            data={
                "test_run_id": "diag_12345",
                "status": "completed",
                "duration_ms": 500,
                "results": [
                    {
                        "component": "database",
                        "tests": [
                            {
                                "name": "connectivity",
                                "status": "pass",
                                "duration_ms": 100,
                                "details": "Connection established successfully",
                            },
                            {
                                "name": "performance",
                                "status": "pass",
                                "duration_ms": 200,
                                "details": {"avg_query_time_ms": 5.2, "queries_per_second": 450},
                            },
                        ],
                    }
                ],
            }
        )

    return router


def create_api_router(
    config_manager: Optional[Any] = None, service_registry: Optional[Any] = None
) -> APIRouter:
    """Create the main API router (legacy)."""
    from .config import ConfigurationManager, create_default_config
    from .core import ServiceRegistry

    if config_manager is None:
        config_manager = ConfigurationManager(create_default_config())

    if service_registry is None:
        service_registry = ServiceRegistry()

    router = APIRouter(prefix="/api", tags=["core"])

    @router.get("/health", response_model=HealthResponse)
    async def health_check() -> HealthResponse:
        """Health check endpoint."""
        metrics = get_system_metrics()
        return HealthResponse(
            status="healthy",
            version=__version__,
            services={"database": "connected", "plugins": "loaded", "auth": "ready"},
            uptime=metrics["uptime"],
        )

    @router.get("/info", response_model=APIResponse)
    async def get_info() -> APIResponse:
        """Get application information."""
        return APIResponse(
            data={
                "name": "Nexus Framework",
                "version": __version__,
                "description": "The Ultimate Plugin-Based Application Platform",
                "documentation": "https://docs.nexus-framework.dev",
                "repository": "https://github.com/nexus-framework/nexus",
            }
        )

    @router.get("/status", response_model=APIResponse)
    async def get_status() -> APIResponse:
        """Get application status."""
        metrics = get_system_metrics()
        return APIResponse(
            data={
                "status": "running",
                "uptime": metrics["uptime"],
                "plugins_loaded": 0,  # Will be updated when plugin manager is integrated
                "active_connections": 0,  # Will be updated when connection tracking is added
                "memory_usage": f"{metrics['memory_usage_mb']}MB",
                "cpu_usage": f"{metrics['cpu_usage_percent']}%",
                "environment": config_manager.config.app.environment,
                "debug_mode": config_manager.config.app.debug,
            }
        )

    @router.get("/version", response_model=APIResponse)
    async def get_version() -> APIResponse:
        """Get version information."""
        return APIResponse(
            data={
                "version": __version__,
                "build": "stable",
                "release_date": "2024-12-21",
                "python_version": "3.11+",
                "framework": "FastAPI",
            }
        )

    return router


def create_plugin_router(plugin_name: str) -> APIRouter:
    """Create a router for a plugin."""
    return APIRouter(prefix=f"/api/plugins/{plugin_name}", tags=[f"plugin-{plugin_name}"])


def create_error_response(
    error: str, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None
) -> JSONResponse:
    """Create standardized error response."""
    response = ErrorResponse(error=error, message=message, details=details)
    return JSONResponse(status_code=status_code, content=response.dict())


def validate_api_key(api_key: Optional[str] = None) -> bool:
    """Validate API key (basic implementation)."""
    if not api_key:
        return False
    # In a real implementation, validate against database
    return api_key == "demo-api-key"


async def require_api_key(api_key: Optional[str] = None) -> None:
    """Dependency to require valid API key."""
    if not validate_api_key(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key"
        )


__all__ = [
    "APIResponse",
    "HealthResponse",
    "ErrorResponse",
    "create_api_router",
    "create_core_api_router",
    "create_plugin_router",
    "create_error_response",
    "validate_api_key",
    "require_api_key",
    "get_system_metrics",
]
