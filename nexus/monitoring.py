"""
Nexus Framework Monitoring Module
Basic health checks and metrics collection functionality.
"""

import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

import psutil
from pydantic import BaseModel, Field

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

    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_percent: float = 0.0
    disk_usage_percent: float = 0.0
    load_average: List[float] = []
    network_stats: Dict[str, Any] = {}
    uptime_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class PerformanceMetrics(BaseModel):
    """Performance metrics model."""

    request_count: int = 0
    error_count: int = 0
    avg_response_time: float = 0.0
    max_response_time: float = 0.0
    min_response_time: float = 0.0
    percentiles: Dict[str, float] = {}
    time_window_seconds: int = 3600

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.request_count == 0:
            return 0.0
        return (self.error_count / self.request_count) * 100

    @property
    def throughput(self) -> float:
        """Calculate throughput as requests per second."""
        if self.time_window_seconds == 0:
            return 0.0
        return self.request_count / self.time_window_seconds


class HealthChecker:
    """Health checker class for managing health checks."""

    def __init__(self) -> None:
        self.checks: Dict[str, Any] = {}
        self.check_configs: Dict[str, Dict[str, Any]] = {}
        self.alert_handlers: List[Callable[[str, Dict[str, Any]], None]] = []

    def add_check(
        self,
        name: str,
        check_function: Callable[[], bool],
        interval: int = 30,
        timeout: int = 5,
        enabled: bool = True,
    ) -> str:
        """Add a health check."""
        check_id = f"{name}_{len(self.checks)}"
        self.checks[check_id] = {"name": name, "function": check_function, "enabled": enabled}
        self.check_configs[check_id] = {
            "interval": interval,
            "timeout": timeout,
            "enabled": enabled,
        }
        return check_id

    def get_check_config(self, check_id: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a check."""
        return self.check_configs.get(check_id)

    async def run_checks(self) -> List[HealthStatus]:
        """Run all enabled health checks."""
        results = []
        for check_id, check_data in self.checks.items():
            if not check_data["enabled"]:
                continue

            try:
                result = check_data["function"]()
                status = "healthy" if result else "unhealthy"
                message = "Check passed" if result else "Check failed"
            except Exception as e:
                status = "unhealthy"
                message = f"Check failed: {str(e)}"

            health_status = HealthStatus(name=check_data["name"], status=status, message=message)
            results.append(health_status)

        return results

    def remove_check(self, check_id: str) -> bool:
        """Remove a health check."""
        if check_id in self.checks:
            del self.checks[check_id]
            del self.check_configs[check_id]
            return True
        return False

    def disable_check(self, check_id: str) -> None:
        """Disable a health check."""
        if check_id in self.checks:
            self.checks[check_id]["enabled"] = False
            self.check_configs[check_id]["enabled"] = False

    def enable_check(self, check_id: str) -> None:
        """Enable a health check."""
        if check_id in self.checks:
            self.checks[check_id]["enabled"] = True
            self.check_configs[check_id]["enabled"] = True

    def add_alert_handler(self, handler: Callable[[str, Dict[str, Any]], None]) -> None:
        """Add an alert handler."""
        self.alert_handlers.append(handler)


class MetricsCollector:
    """Metrics collector for recording and retrieving metrics."""

    def __init__(self) -> None:
        self.metrics: Dict[str, Any] = {}
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.histograms: Dict[str, Dict[str, Any]] = {}
        self.time_series: Dict[str, List[Dict[str, Any]]] = {}
        self.start_time = time.time()
        self.request_count = 0
        self.error_count = 0
        self.response_times: List[float] = []

    def record_metric(self, name: str, value: Any, labels: Optional[Dict[str, str]] = None) -> None:
        """Record a metric value."""
        metric_key = self._build_metric_key(name, labels)
        self.metrics[metric_key] = value

    def get_metrics(self) -> Dict[str, Any]:
        """Get all recorded metrics."""
        result = {}
        result.update(self.metrics)
        result.update(self.counters)
        result.update(self.gauges)

        # Add histogram data
        for name, data in self.histograms.items():
            result[name] = data

        return result

    def increment_counter(self, name: str, amount: int = 1) -> None:
        """Increment a counter metric."""
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += amount

    def record_histogram(self, name: str, value: float) -> None:
        """Record a histogram value."""
        if name not in self.histograms:
            self.histograms[name] = {"count": 0, "sum": 0.0, "values": []}

        self.histograms[name]["count"] += 1
        self.histograms[name]["sum"] += value
        self.histograms[name]["values"].append(value)

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge metric value."""
        self.gauges[name] = value

    def record_metric_with_timestamp(self, name: str, value: Any, timestamp: float) -> None:
        """Record a metric with timestamp for time series."""
        if name not in self.time_series:
            self.time_series[name] = []

        self.time_series[name].append({"value": value, "timestamp": timestamp})

    def get_time_series(self, name: str) -> List[Dict[str, Any]]:
        """Get time series data for a metric."""
        return self.time_series.get(name, [])

    def record_request(self, response_time_ms: float, status_code: int) -> None:
        """Record a request metric."""
        self.request_count += 1
        self.response_times.append(response_time_ms)

        # Keep only last 1000 response times for average calculation
        if len(self.response_times) > 1000:
            self.response_times = self.response_times[-1000:]

        if status_code >= 400:
            self.error_count += 1

    def _build_metric_key(self, name: str, labels: Optional[Dict[str, str]]) -> str:
        """Build a metric key with labels."""
        if labels:
            label_str = ",".join(f"{k}={v}" for k, v in labels.items())
            return f"{name}{{{label_str}}}"
        return name


class SystemMonitor:
    """System monitor for collecting system metrics."""

    def __init__(
        self,
        interval: int = 60,
        enable_network_monitoring: bool = False,
        enable_process_monitoring: bool = False,
    ):
        self.interval = interval
        self.enable_network_monitoring = enable_network_monitoring
        self.enable_process_monitoring = enable_process_monitoring
        self.monitoring = False
        self.history: List[SystemMetrics] = []
        self.max_history_entries = 1000
        self.thresholds: Dict[str, Dict[str, float]] = {}
        self.custom_collectors: Dict[str, Callable[[], Dict[str, Any]]] = {}

    def start_monitoring(self) -> None:
        """Start system monitoring."""
        self.monitoring = True

    def stop_monitoring(self) -> None:
        """Stop system monitoring."""
        self.monitoring = False

    def is_monitoring(self) -> bool:
        """Check if monitoring is active."""
        return self.monitoring

    def get_current_metrics(self) -> SystemMetrics:
        """Get current system metrics."""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")

        metrics = SystemMetrics(
            cpu_percent=cpu_percent,
            memory_percent=memory.percent,
            disk_percent=disk.percent,
            load_average=list(psutil.getloadavg()) if hasattr(psutil, "getloadavg") else [],
        )

        if self.enable_network_monitoring:
            net_io = psutil.net_io_counters()
            metrics.network_stats = {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
            }

        return metrics

    def get_configuration(self) -> Dict[str, Any]:
        """Get monitor configuration."""
        return {
            "interval": self.interval,
            "enable_network_monitoring": self.enable_network_monitoring,
            "enable_process_monitoring": self.enable_process_monitoring,
        }

    def set_threshold(self, metric: str, max_value: float) -> None:
        """Set threshold for a metric."""
        self.thresholds[metric] = {"max": max_value}

    def check_thresholds(self) -> List[Dict[str, Any]]:
        """Check if any thresholds are exceeded."""
        alerts = []
        current_metrics = self.get_current_metrics()

        for metric, threshold in self.thresholds.items():
            if hasattr(current_metrics, metric):
                value = getattr(current_metrics, metric)
                if value > threshold["max"]:
                    alerts.append(
                        {
                            "metric": metric,
                            "value": value,
                            "threshold": threshold["max"],
                            "message": f"{metric} exceeded threshold: {value} > {threshold['max']}",
                        }
                    )

        return alerts

    def enable_history_collection(self, max_entries: int = 1000) -> None:
        """Enable metrics history collection."""
        self.max_history_entries = max_entries

    def _add_to_history(self, metrics: SystemMetrics) -> None:
        """Add metrics to history."""
        self.history.append(metrics)
        if len(self.history) > self.max_history_entries:
            self.history.pop(0)

    def get_metrics_history(self, limit: int = 100) -> List[SystemMetrics]:
        """Get metrics history."""
        return self.history[-limit:]

    def add_custom_collector(self, name: str, collector_func: Callable[[], Dict[str, Any]]) -> None:
        """Add custom metrics collector."""
        self.custom_collectors[name] = collector_func


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
    check_function: Callable[[], bool]
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
                import asyncio

                if asyncio.iscoroutinefunction(self.check_function):
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


# Default health checks
def database_health_check() -> bool:
    """Basic database health check."""
    # In a real implementation, this would test database connectivity
    return True


def memory_health_check() -> bool:
    """Memory usage health check."""
    try:
        memory = psutil.virtual_memory()
        return bool(memory.percent < 90.0)  # Consider unhealthy if > 90% memory usage
    except Exception:
        return False


def disk_health_check() -> bool:
    """Disk usage health check."""
    try:
        disk = psutil.disk_usage("/")
        return bool(disk.percent < 95.0)  # Consider unhealthy if > 95% disk usage
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
