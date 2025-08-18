"""
Analytics Dashboard Plugin

A comprehensive analytics dashboard plugin providing metrics collection,
visualization, and reporting capabilities with web API and UI.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


# Data Models
class MetricData(BaseModel):
    """Metric data model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    value: float
    unit: str = ""
    category: str = "general"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    tags: Dict[str, str] = Field(default_factory=dict)


class DashboardWidget(BaseModel):
    """Dashboard widget configuration."""

    id: str
    title: str
    type: str  # chart, metric, table, gauge
    config: Dict[str, Any]
    position: Dict[str, int]  # x, y, width, height


class AnalyticsReport(BaseModel):
    """Analytics report model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    description: str
    metrics: List[str]
    date_range: Dict[str, datetime]
    filters: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AnalyticsDashboardPlugin(BasePlugin):
    """Analytics Dashboard Plugin with comprehensive metrics and visualization."""

    def __init__(self):
        super().__init__()
        self.name = "analytics_dashboard"
        self.version = "1.0.0"
        self.category = "analytics"
        self.description = (
            "Comprehensive analytics dashboard with metrics collection and visualization"
        )

        # In-memory storage for demo (replace with real database)
        self.metrics_data: List[MetricData] = []
        self.dashboard_config: List[DashboardWidget] = []
        self.reports: List[AnalyticsReport] = []

        # Initialize with sample data
        self._initialize_sample_data()

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin v{self.version}")

        # Create database tables
        await self._create_database_schema()

        # Start metric collection
        await self._start_metric_collection()

        logger.info(f"{self.name} plugin initialized successfully")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")
        await self.publish_event(
            "analytics.dashboard.shutdown",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix="/plugins/analytics_dashboard", tags=["analytics"])

        # Metrics endpoints
        @router.get("/metrics")
        async def get_metrics(category: Optional[str] = None, limit: int = 100, offset: int = 0):
            """Get metrics data."""
            filtered_metrics = self.metrics_data

            if category:
                filtered_metrics = [m for m in filtered_metrics if m.category == category]

            total = len(filtered_metrics)
            metrics = filtered_metrics[offset : offset + limit]

            return {
                "metrics": [m.dict() for m in metrics],
                "total": total,
                "limit": limit,
                "offset": offset,
            }

        @router.post("/metrics")
        async def create_metric(metric: MetricData):
            """Create a new metric."""
            self.metrics_data.append(metric)

            await self.publish_event(
                "analytics.metric.created",
                {"metric_id": metric.id, "name": metric.name, "category": metric.category},
            )

            return {"message": "Metric created", "id": metric.id}

        @router.get("/metrics/categories")
        async def get_metric_categories():
            """Get available metric categories."""
            categories = list(set(m.category for m in self.metrics_data))
            return {"categories": categories}

        @router.get("/metrics/summary")
        async def get_metrics_summary():
            """Get metrics summary with aggregated data."""
            now = datetime.utcnow()
            last_24h = now - timedelta(hours=24)
            last_7d = now - timedelta(days=7)

            recent_metrics = [m for m in self.metrics_data if m.timestamp >= last_24h]
            weekly_metrics = [m for m in self.metrics_data if m.timestamp >= last_7d]

            categories = {}
            for metric in self.metrics_data:
                if metric.category not in categories:
                    categories[metric.category] = {"count": 0, "avg_value": 0}
                categories[metric.category]["count"] += 1

            return {
                "total_metrics": len(self.metrics_data),
                "last_24h": len(recent_metrics),
                "last_7d": len(weekly_metrics),
                "categories": categories,
                "latest_update": max(
                    (m.timestamp for m in self.metrics_data), default=now
                ).isoformat(),
            }

        # Dashboard endpoints
        @router.get("/dashboard")
        async def get_dashboard_config():
            """Get dashboard configuration."""
            return {"widgets": [w.dict() for w in self.dashboard_config]}

        @router.post("/dashboard/widgets")
        async def create_widget(widget: DashboardWidget):
            """Create a dashboard widget."""
            # Remove existing widget with same ID
            self.dashboard_config = [w for w in self.dashboard_config if w.id != widget.id]
            self.dashboard_config.append(widget)

            return {"message": "Widget created", "id": widget.id}

        @router.delete("/dashboard/widgets/{widget_id}")
        async def delete_widget(widget_id: str):
            """Delete a dashboard widget."""
            original_count = len(self.dashboard_config)
            self.dashboard_config = [w for w in self.dashboard_config if w.id != widget_id]

            if len(self.dashboard_config) == original_count:
                raise HTTPException(status_code=404, detail="Widget not found")

            return {"message": "Widget deleted"}

        # Reports endpoints
        @router.get("/reports")
        async def get_reports():
            """Get analytics reports."""
            return {"reports": [r.dict() for r in self.reports]}

        @router.post("/reports")
        async def create_report(report: AnalyticsReport):
            """Create an analytics report."""
            self.reports.append(report)
            return {"message": "Report created", "id": report.id}

        @router.get("/reports/{report_id}/generate")
        async def generate_report(report_id: str):
            """Generate report data."""
            report = next((r for r in self.reports if r.id == report_id), None)
            if not report:
                raise HTTPException(status_code=404, detail="Report not found")

            # Filter metrics based on report criteria
            filtered_metrics = []
            for metric in self.metrics_data:
                if report.date_range.get("start") and metric.timestamp < report.date_range["start"]:
                    continue
                if report.date_range.get("end") and metric.timestamp > report.date_range["end"]:
                    continue
                if report.metrics and metric.name not in report.metrics:
                    continue
                filtered_metrics.append(metric)

            return {
                "report": report.dict(),
                "data": [m.dict() for m in filtered_metrics],
                "summary": {
                    "total_records": len(filtered_metrics),
                    "date_range": report.date_range,
                    "generated_at": datetime.utcnow().isoformat(),
                },
            }

        # Web UI endpoint
        @router.get("/ui", response_class=HTMLResponse)
        async def dashboard_ui():
            """Serve the analytics dashboard UI."""
            return self._get_dashboard_html()

        @router.get("/ui/widget/{widget_type}")
        async def get_widget_data(widget_type: str):
            """Get data for specific widget type."""
            if widget_type == "metrics_chart":
                # Group metrics by category for chart
                chart_data = {}
                for metric in self.metrics_data[-50:]:  # Last 50 metrics
                    if metric.category not in chart_data:
                        chart_data[metric.category] = []
                    chart_data[metric.category].append(
                        {"x": metric.timestamp.isoformat(), "y": metric.value}
                    )
                return {"chart_data": chart_data}

            elif widget_type == "summary_cards":
                return await get_metrics_summary()

            elif widget_type == "recent_activity":
                recent = sorted(self.metrics_data, key=lambda m: m.timestamp, reverse=True)[:10]
                return {
                    "activities": [
                        {
                            "id": m.id,
                            "description": f"Metric '{m.name}' recorded: {m.value} {m.unit}",
                            "timestamp": m.timestamp.isoformat(),
                            "category": m.category,
                        }
                        for m in recent
                    ]
                }

            return {"error": "Unknown widget type"}

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_metrics": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "name"},
                        {"field": "category"},
                        {"field": "timestamp"},
                    ]
                },
                f"{self.name}_widgets": {
                    "indexes": [{"field": "id", "unique": True}, {"field": "type"}]
                },
                f"{self.name}_reports": {
                    "indexes": [{"field": "id", "unique": True}, {"field": "created_at"}]
                },
            }
        }

    async def _create_database_schema(self):
        """Create database schema if using real database."""
        if self.db_adapter:
            schema = self.get_database_schema()
            # Implementation would depend on your database adapter
            logger.info(f"Database schema defined: {list(schema['collections'].keys())}")

    async def _start_metric_collection(self):
        """Start background metric collection."""
        # In a real implementation, this would start background tasks
        # to collect system metrics, API usage, etc.
        await self.publish_event(
            "analytics.collection.started",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def _initialize_sample_data(self):
        """Initialize with sample data for demonstration."""
        # Sample metrics
        categories = ["performance", "usage", "errors", "business"]
        metric_names = {
            "performance": ["response_time", "cpu_usage", "memory_usage", "disk_io"],
            "usage": ["api_calls", "active_users", "page_views", "downloads"],
            "errors": ["error_rate", "failed_requests", "timeout_count", "exception_count"],
            "business": ["revenue", "conversions", "leads", "customer_satisfaction"],
        }

        # Generate sample data for the last 7 days
        base_time = datetime.utcnow() - timedelta(days=7)
        for i in range(168):  # 7 days * 24 hours
            timestamp = base_time + timedelta(hours=i)
            for category in categories:
                for metric_name in metric_names[category]:
                    value = self._generate_sample_value(metric_name, i)
                    self.metrics_data.append(
                        MetricData(
                            name=metric_name,
                            value=value,
                            unit=self._get_metric_unit(metric_name),
                            category=category,
                            timestamp=timestamp,
                            tags={"source": "sample_data", "period": "hourly"},
                        )
                    )

        # Sample dashboard widgets
        self.dashboard_config = [
            DashboardWidget(
                id="summary_cards",
                title="Metrics Summary",
                type="cards",
                config={"show_trends": True},
                position={"x": 0, "y": 0, "width": 12, "height": 3},
            ),
            DashboardWidget(
                id="performance_chart",
                title="Performance Metrics",
                type="line_chart",
                config={"metrics": ["response_time", "cpu_usage"], "time_range": "24h"},
                position={"x": 0, "y": 3, "width": 8, "height": 6},
            ),
            DashboardWidget(
                id="usage_pie",
                title="Usage Distribution",
                type="pie_chart",
                config={"category": "usage", "time_range": "7d"},
                position={"x": 8, "y": 3, "width": 4, "height": 6},
            ),
            DashboardWidget(
                id="recent_activity",
                title="Recent Activity",
                type="activity_feed",
                config={"limit": 10},
                position={"x": 0, "y": 9, "width": 12, "height": 4},
            ),
        ]

    def _generate_sample_value(self, metric_name: str, hour_offset: int) -> float:
        """Generate realistic sample values for different metrics."""
        import math
        import random

        # Add some daily and weekly patterns
        daily_pattern = math.sin(2 * math.pi * hour_offset / 24) * 0.3
        weekly_pattern = math.sin(2 * math.pi * hour_offset / 168) * 0.2
        noise = random.uniform(-0.1, 0.1)

        base_values = {
            "response_time": 150,
            "cpu_usage": 45,
            "memory_usage": 65,
            "disk_io": 30,
            "api_calls": 1000,
            "active_users": 250,
            "page_views": 5000,
            "downloads": 100,
            "error_rate": 2.5,
            "failed_requests": 25,
            "timeout_count": 5,
            "exception_count": 3,
            "revenue": 10000,
            "conversions": 45,
            "leads": 20,
            "customer_satisfaction": 4.2,
        }

        base = base_values.get(metric_name, 50)
        pattern_value = base * (1 + daily_pattern + weekly_pattern + noise)
        return max(0, round(pattern_value, 2))

    def _get_metric_unit(self, metric_name: str) -> str:
        """Get appropriate unit for metric."""
        units = {
            "response_time": "ms",
            "cpu_usage": "%",
            "memory_usage": "%",
            "disk_io": "MB/s",
            "api_calls": "count",
            "active_users": "users",
            "page_views": "views",
            "downloads": "count",
            "error_rate": "%",
            "failed_requests": "count",
            "timeout_count": "count",
            "exception_count": "count",
            "revenue": "USD",
            "conversions": "count",
            "leads": "count",
            "customer_satisfaction": "score",
        }
        return units.get(metric_name, "")

    def _get_dashboard_html(self) -> str:
        """Generate the dashboard HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Analytics Dashboard - Nexus Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f5f7fa;
            color: #2d3748;
            line-height: 1.6;
        }

        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }

        .header h1 {
            color: #2b6cb0;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .container {
            max-width: 1200px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }

        .widget {
            background: white;
            border-radius: 8px;
            padding: 1.5rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
        }

        .widget h3 {
            margin-bottom: 1rem;
            color: #2d3748;
            font-size: 1.1rem;
            font-weight: 600;
        }

        .stats-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
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
            color: #2b6cb0;
            margin-bottom: 0.5rem;
        }

        .stat-label {
            color: #718096;
            font-size: 0.9rem;
        }

        .chart-container {
            position: relative;
            height: 300px;
            margin-top: 1rem;
        }

        .activity-item {
            padding: 0.75rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .activity-item:last-child {
            border-bottom: none;
        }

        .activity-desc {
            flex: 1;
        }

        .activity-time {
            color: #718096;
            font-size: 0.8rem;
        }

        .category-badge {
            display: inline-block;
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 500;
            margin-left: 0.5rem;
        }

        .badge-performance { background: #e6fffa; color: #00695c; }
        .badge-usage { background: #e3f2fd; color: #1565c0; }
        .badge-errors { background: #ffebee; color: #c62828; }
        .badge-business { background: #f3e5f5; color: #7b1fa2; }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #718096;
        }

        .refresh-btn {
            background: #2b6cb0;
            color: white;
            border: none;
            padding: 0.5rem 1rem;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.9rem;
            float: right;
            margin-bottom: 1rem;
        }

        .refresh-btn:hover {
            background: #2c5aa0;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 Analytics Dashboard</h1>
    </div>

    <div class="container">
        <button class="refresh-btn" onclick="refreshDashboard()">🔄 Refresh</button>

        <div class="stats-grid" id="statsGrid">
            <div class="stat-card">
                <div class="stat-value" id="totalMetrics">-</div>
                <div class="stat-label">Total Metrics</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="last24h">-</div>
                <div class="stat-label">Last 24 Hours</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="last7d">-</div>
                <div class="stat-label">Last 7 Days</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" id="categories">-</div>
                <div class="stat-label">Categories</div>
            </div>
        </div>

        <div class="dashboard-grid">
            <div class="widget">
                <h3>📈 Performance Trends</h3>
                <div class="chart-container">
                    <canvas id="performanceChart"></canvas>
                </div>
            </div>

            <div class="widget">
                <h3>🎯 Usage Distribution</h3>
                <div class="chart-container">
                    <canvas id="usageChart"></canvas>
                </div>
            </div>
        </div>

        <div class="widget">
            <h3>🔄 Recent Activity</h3>
            <div id="recentActivity" class="loading">Loading activity...</div>
        </div>
    </div>

    <script>
        let performanceChart, usageChart;

        async function loadDashboard() {
            try {
                // Load summary stats
                const summaryResponse = await fetch('/plugins/analytics_dashboard/metrics/summary');
                const summary = await summaryResponse.json();

                document.getElementById('totalMetrics').textContent = summary.total_metrics.toLocaleString();
                document.getElementById('last24h').textContent = summary.last_24h.toLocaleString();
                document.getElementById('last7d').textContent = summary.last_7d.toLocaleString();
                document.getElementById('categories').textContent = Object.keys(summary.categories).length;

                // Load chart data
                await loadPerformanceChart();
                await loadUsageChart();
                await loadRecentActivity();

            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        async function loadPerformanceChart() {
            try {
                const response = await fetch('/plugins/analytics_dashboard/ui/widget/metrics_chart');
                const data = await response.json();

                const ctx = document.getElementById('performanceChart').getContext('2d');

                if (performanceChart) {
                    performanceChart.destroy();
                }

                const datasets = Object.keys(data.chart_data).map(category => ({
                    label: category.charAt(0).toUpperCase() + category.slice(1),
                    data: data.chart_data[category],
                    borderColor: getCategoryColor(category),
                    backgroundColor: getCategoryColor(category) + '20',
                    fill: false,
                    tension: 0.4
                }));

                performanceChart = new Chart(ctx, {
                    type: 'line',
                    data: { datasets },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        scales: {
                            x: {
                                type: 'time',
                                time: { unit: 'hour' }
                            },
                            y: { beginAtZero: true }
                        },
                        plugins: {
                            legend: { position: 'top' }
                        }
                    }
                });
            } catch (error) {
                console.error('Error loading performance chart:', error);
            }
        }

        async function loadUsageChart() {
            try {
                const response = await fetch('/plugins/analytics_dashboard/metrics?category=usage&limit=1000');
                const data = await response.json();

                const usageByType = {};
                data.metrics.forEach(metric => {
                    usageByType[metric.name] = (usageByType[metric.name] || 0) + metric.value;
                });

                const ctx = document.getElementById('usageChart').getContext('2d');

                if (usageChart) {
                    usageChart.destroy();
                }

                usageChart = new Chart(ctx, {
                    type: 'doughnut',
                    data: {
                        labels: Object.keys(usageByType),
                        datasets: [{
                            data: Object.values(usageByType),
                            backgroundColor: [
                                '#3B82F6', '#10B981', '#F59E0B', '#EF4444',
                                '#8B5CF6', '#06B6D4', '#84CC16', '#F97316'
                            ]
                        }]
                    },
                    options: {
                        responsive: true,
                        maintainAspectRatio: false,
                        plugins: {
                            legend: { position: 'bottom' }
                        }
                    }
                });
            } catch (error) {
                console.error('Error loading usage chart:', error);
            }
        }

        async function loadRecentActivity() {
            try {
                const response = await fetch('/plugins/analytics_dashboard/ui/widget/recent_activity');
                const data = await response.json();

                const container = document.getElementById('recentActivity');

                if (data.activities && data.activities.length > 0) {
                    container.innerHTML = data.activities.map(activity => `
                        <div class="activity-item">
                            <div class="activity-desc">
                                ${activity.description}
                                <span class="category-badge badge-${activity.category}">${activity.category}</span>
                            </div>
                            <div class="activity-time">${formatTime(activity.timestamp)}</div>
                        </div>
                    `).join('');
                } else {
                    container.innerHTML = '<div class="loading">No recent activity</div>';
                }
            } catch (error) {
                console.error('Error loading recent activity:', error);
                document.getElementById('recentActivity').innerHTML = '<div class="loading">Error loading activity</div>';
            }
        }

        function getCategoryColor(category) {
            const colors = {
                performance: '#3B82F6',
                usage: '#10B981',
                errors: '#EF4444',
                business: '#8B5CF6'
            };
            return colors[category] || '#6B7280';
        }

        function formatTime(timestamp) {
            const date = new Date(timestamp);
            const now = new Date();
            const diff = now - date;
            const minutes = Math.floor(diff / 60000);
            const hours = Math.floor(minutes / 60);
            const days = Math.floor(hours / 24);

            if (days > 0) return `${days}d ago`;
            if (hours > 0) return `${hours}h ago`;
            if (minutes > 0) return `${minutes}m ago`;
            return 'Just now';
        }

        function refreshDashboard() {
            loadDashboard();
        }

        // Load dashboard on page load
        document.addEventListener('DOMContentLoaded', loadDashboard);

        // Auto-refresh every 30 seconds
        setInterval(loadDashboard, 30000);
    </script>
</body>
</html>
        """
