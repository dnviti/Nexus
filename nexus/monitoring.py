"""
Nexus Framework Monitoring Module
Basic health checks and metrics collection functionality.
"""

import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

import psutil
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HealthStatus(BaseModel):
    """Health check status model."""

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str = "OK"
    timestamp: datetime = datetime.utcnow()
    response_time_ms: Optional[float] = None
    details: Dict[str, Any] = {}


class SystemMetrics(BaseModel):
    """System metrics model."""

    cpu_percent: float
    memory_percent: float
    memory_used_mb: float
    memory_total_mb: float
    disk_usage_percent: float
    load_average: List[float]
    uptime_seconds: float
    timestamp: datetime = datetime.utcnow()


class ApplicationMetrics(BaseModel):
    """Application-specific metrics model."""

    active_connections: int = 0
    total_requests: int = 0
    failed_requests: int = 0
    average_response_time_ms: float = 0.0
    plugins_loaded: int = 0
    plugins_active: int = 0
    timestamp: datetime = datetime.utcnow()


@dataclass
class HealthCheck:
    """Health check configuration and execution."""

    name: str
    check_function: Callable
    timeout_seconds: float = 5.0
    interval_seconds: float = 30.0
    last_check: Optional[datetime] = None
    last_status: Optional[HealthStatus] = None
    failure_count: int = 0
    max_failures: int = 3

    async def execute(self) -> HealthStatus:
        """Execute the health check."""
        start_time = time.time()

        try:
            # Execute the check function
            if hasattr(self.check_function, "__call__"):
                if hasattr(self.check_function, "__await__"):
                    result = await self.check_function()
                else:
                    result = self.check_function()
            else:
                result = True

            response_time = (time.time() - start_time) * 1000  # Convert to ms

            if result:
                status = HealthStatus(
                    name=self.name,
                    status="healthy",
                    message="Check passed",
                    response_time_ms=response_time,
                )
                self.failure_count = 0
            else:
                status = HealthStatus(
                    name=self.name,
                    status="unhealthy",
                    message="Check failed",
                    response_time_ms=response_time,
                )
                self.failure_count += 1

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            status = HealthStatus(
                name=self.name,
                status="unhealthy",
                message=f"Check error: {str(e)}",
                response_time_ms=response_time,
                details={"error": str(e)},
            )
            self.failure_count += 1
            logger.error(f"Health check '{self.name}' failed: {e}")

        self.last_check = datetime.utcnow()
        self.last_status = status
        return status


class MetricsCollector:
    """Collects and stores application metrics."""

    def __init__(self):
        """Initialize metrics collector."""
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.response_times = []
        self.health_checks: Dict[str, HealthCheck] = {}

    def record_request(self, response_time_ms: float, status_code: int):
        """Record a request metric."""
        self.request_count += 1
        self.response_times.append(response_time_ms)

        # Keep only last 1000 response times for average calculation
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

        if status_code >= 400:
            self.error_count += 1

    def get_system_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            load_avg = psutil.getloadavg() if hasattr(psutil, "getloadavg") else [0.0, 0.0, 0.0]

            return SystemMetrics(
                cpu_percent=psutil.cpu_percent(interval=1),
                memory_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_total_mb=memory.total / 1024 / 1024,
                disk_usage_percent=disk.percent,
                load_average=list(load_avg),
                uptime_seconds=time.time() - self.start_time,
            )
        except Exception as e:
            logger.error(f"Failed to collect system metrics: {e}")
            return SystemMetrics(
                cpu_percent=0.0,
                memory_percent=0.0,
                memory_used_mb=0.0,
                memory_total_mb=0.0,
                disk_usage_percent=0.0,
                load_average=[0.0, 0.0, 0.0],
                uptime_seconds=time.time() - self.start_time,
            )

    def get_application_metrics(self) -> ApplicationMetrics:
        """Get current application metrics."""
        avg_response_time = (
            sum(self.response_times) / len(self.response_times) if self.response_times else 0.0
        )

        return ApplicationMetrics(
            total_requests=self.request_count,
            failed_requests=self.error_count,
            average_response_time_ms=avg_response_time,
            plugins_loaded=0,  # Would be populated by plugin manager
            plugins_active=0,  # Would be populated by plugin manager
        )

    def add_health_check(self, health_check: HealthCheck):
        """Add a health check."""
        self.health_checks[health_check.name] = health_check
        logger.info(f"Added health check: {health_check.name}")

    async def run_health_checks(self) -> Dict[str, HealthStatus]:
        """Run all health checks."""
        results = {}
        for name, check in self.health_checks.items():
            try:
                status = await check.execute()
                results[name] = status
            except Exception as e:
                logger.error(f"Failed to run health check '{name}': {e}")
                results[name] = HealthStatus(
                    name=name, status="unhealthy", message=f"Execution failed: {str(e)}"
                )
        return results

    def get_overall_health(self) -> str:
        """Get overall application health status."""
        if not self.health_checks:
            return "unknown"

        unhealthy_checks = [
            check
            for check in self.health_checks.values()
            if check.last_status and check.last_status.status == "unhealthy"
        ]

        degraded_checks = [
            check
            for check in self.health_checks.values()
            if check.last_status and check.last_status.status == "degraded"
        ]

        if unhealthy_checks:
            return "unhealthy"
        elif degraded_checks:
            return "degraded"
        else:
            return "healthy"


# Default health checks
def database_health_check() -> bool:
    """Basic database health check."""
    # In a real implementation, this would test database connectivity
    return True


def memory_health_check() -> bool:
    """Memory usage health check."""
    try:
        memory = psutil.virtual_memory()
        return memory.percent < 90  # Consider unhealthy if > 90% memory usage
    except Exception:
        return False


def disk_health_check() -> bool:
    """Disk usage health check."""
    try:
        disk = psutil.disk_usage("/")
        return disk.percent < 95  # Consider unhealthy if > 95% disk usage
    except Exception:
        return False


def create_default_health_checks() -> List[HealthCheck]:
    """Create default health checks."""
    return [
        HealthCheck(
            name="database",
            check_function=database_health_check,
            timeout_seconds=5.0,
            interval_seconds=30.0,
        ),
        HealthCheck(
            name="memory",
            check_function=memory_health_check,
            timeout_seconds=1.0,
            interval_seconds=60.0,
        ),
        HealthCheck(
            name="disk",
            check_function=disk_health_check,
            timeout_seconds=1.0,
            interval_seconds=300.0,  # Check every 5 minutes
        ),
    ]


__all__ = [
    "HealthStatus",
    "SystemMetrics",
    "ApplicationMetrics",
    "HealthCheck",
    "MetricsCollector",
    "database_health_check",
    "memory_health_check",
    "disk_health_check",
    "create_default_health_checks",
]
