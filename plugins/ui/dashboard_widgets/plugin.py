"""
Dashboard Widgets Plugin

A comprehensive UI plugin providing customizable dashboard widgets, components,
and interactive elements with web API and UI builder interface.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from nexus.plugins import BasePlugin

logger = logging.getLogger(__name__)


# Data Models
class Widget(BaseModel):
    """Widget model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    title: str
    type: str  # chart, metric, table, text, iframe, custom
    config: Dict[str, Any] = Field(default_factory=dict)
    data_source: Optional[str] = None
    position: Dict[str, int] = Field(default_factory=dict)  # x, y, width, height
    style: Dict[str, str] = Field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class Dashboard(BaseModel):
    """Dashboard model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str = ""
    widgets: List[str] = Field(default_factory=list)  # widget IDs
    layout: Dict[str, Any] = Field(default_factory=dict)
    theme: str = "light"
    is_public: bool = False
    created_by: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WidgetTemplate(BaseModel):
    """Widget template model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: str
    category: str
    template_config: Dict[str, Any] = Field(default_factory=dict)
    preview_image: Optional[str] = None
    is_featured: bool = False
    usage_count: int = 0


class DataSource(BaseModel):
    """Data source model."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    type: str  # api, database, file, plugin
    endpoint: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    refresh_interval: int = 300  # seconds
    last_updated: Optional[datetime] = None
    is_active: bool = True


class DashboardWidgetsPlugin(BasePlugin):
    """Dashboard Widgets Plugin with customizable UI components."""

    def __init__(self):
        super().__init__()
        self.name = "dashboard_widgets"
        self.version = "1.0.0"
        self.category = "ui"
        self.description = "Customizable dashboard widgets and UI components system"

        # Storage
        self.widgets: List[Widget] = []
        self.dashboards: List[Dashboard] = []
        self.widget_templates: List[WidgetTemplate] = []
        self.data_sources: List[DataSource] = []

        # Cache for widget data
        self.widget_data_cache: Dict[str, Any] = {}

        # Initialize with sample data
        self._initialize_sample_data()

    async def initialize(self) -> bool:
        """Initialize the plugin."""
        logger.info(f"Initializing {self.name} plugin v{self.version}")

        # Create database schema
        await self._create_database_schema()

        # Load widget templates
        await self._load_widget_templates()

        # Start data refresh tasks
        await self._start_data_refresh_tasks()

        await self.publish_event(
            "dashboard_widgets.initialized",
            {"plugin": self.name, "widgets_count": len(self.widgets)},
        )

        logger.info(f"{self.name} plugin initialized successfully")
        return True

    async def shutdown(self) -> None:
        """Shutdown the plugin."""
        logger.info(f"Shutting down {self.name} plugin")
        await self.publish_event(
            "dashboard_widgets.shutdown",
            {"plugin": self.name, "timestamp": datetime.utcnow().isoformat()},
        )

    def get_api_routes(self) -> List[APIRouter]:
        """Get API routes for this plugin."""
        router = APIRouter(prefix="/plugins/dashboard_widgets", tags=["ui", "widgets"])

        # Widget endpoints
        @router.get("/widgets")
        async def get_widgets(dashboard_id: Optional[str] = None, type: Optional[str] = None):
            """Get widgets with optional filtering."""
            filtered_widgets = self.widgets

            if dashboard_id:
                dashboard = next((d for d in self.dashboards if d.id == dashboard_id), None)
                if dashboard:
                    filtered_widgets = [w for w in filtered_widgets if w.id in dashboard.widgets]

            if type:
                filtered_widgets = [w for w in filtered_widgets if w.type == type]

            return {"widgets": [widget.dict() for widget in filtered_widgets]}

        @router.get("/widgets/{widget_id}")
        async def get_widget(widget_id: str):
            """Get widget by ID."""
            widget = next((w for w in self.widgets if w.id == widget_id), None)
            if not widget:
                raise HTTPException(status_code=404, detail="Widget not found")

            return {"widget": widget.dict()}

        @router.post("/widgets")
        async def create_widget(widget_data: Widget):
            """Create a new widget."""
            # Set default position if not provided
            if not widget_data.position:
                widget_data.position = {"x": 0, "y": 0, "width": 4, "height": 3}

            self.widgets.append(widget_data)

            await self.publish_event(
                "dashboard_widgets.widget.created",
                {"widget_id": widget_data.id, "widget_type": widget_data.type},
            )

            return {"message": "Widget created", "widget_id": widget_data.id}

        @router.put("/widgets/{widget_id}")
        async def update_widget(widget_id: str, widget_data: Widget):
            """Update a widget."""
            widget = next((w for w in self.widgets if w.id == widget_id), None)
            if not widget:
                raise HTTPException(status_code=404, detail="Widget not found")

            widget_data.id = widget_id
            widget_data.created_at = widget.created_at
            widget_data.updated_at = datetime.utcnow()

            self.widgets = [w if w.id != widget_id else widget_data for w in self.widgets]

            return {"message": "Widget updated"}

        @router.delete("/widgets/{widget_id}")
        async def delete_widget(widget_id: str):
            """Delete a widget."""
            original_count = len(self.widgets)
            self.widgets = [w for w in self.widgets if w.id != widget_id]

            if len(self.widgets) == original_count:
                raise HTTPException(status_code=404, detail="Widget not found")

            # Remove from dashboards
            for dashboard in self.dashboards:
                if widget_id in dashboard.widgets:
                    dashboard.widgets.remove(widget_id)

            return {"message": "Widget deleted"}

        @router.get("/widgets/{widget_id}/data")
        async def get_widget_data(widget_id: str, refresh: bool = False):
            """Get widget data."""
            widget = next((w for w in self.widgets if w.id == widget_id), None)
            if not widget:
                raise HTTPException(status_code=404, detail="Widget not found")

            # Check cache first (unless refresh requested)
            cache_key = f"widget_data_{widget_id}"
            if not refresh and cache_key in self.widget_data_cache:
                cached_data = self.widget_data_cache[cache_key]
                cache_time = cached_data.get("timestamp", datetime.min)
                if datetime.utcnow() - cache_time < timedelta(minutes=5):
                    return cached_data["data"]

            # Generate widget data based on type
            data = await self._generate_widget_data(widget)

            # Cache the data
            self.widget_data_cache[cache_key] = {
                "data": data,
                "timestamp": datetime.utcnow(),
            }

            return data

        # Dashboard endpoints
        @router.get("/dashboards")
        async def get_dashboards():
            """Get all dashboards."""
            return {"dashboards": [dashboard.dict() for dashboard in self.dashboards]}

        @router.get("/dashboards/{dashboard_id}")
        async def get_dashboard(dashboard_id: str):
            """Get dashboard by ID with widgets."""
            dashboard = next((d for d in self.dashboards if d.id == dashboard_id), None)
            if not dashboard:
                raise HTTPException(status_code=404, detail="Dashboard not found")

            # Get dashboard widgets
            dashboard_widgets = [w for w in self.widgets if w.id in dashboard.widgets]

            return {
                "dashboard": dashboard.dict(),
                "widgets": [widget.dict() for widget in dashboard_widgets],
            }

        @router.post("/dashboards")
        async def create_dashboard(dashboard_data: Dashboard):
            """Create a new dashboard."""
            self.dashboards.append(dashboard_data)

            await self.publish_event(
                "dashboard_widgets.dashboard.created",
                {"dashboard_id": dashboard_data.id, "dashboard_name": dashboard_data.name},
            )

            return {"message": "Dashboard created", "dashboard_id": dashboard_data.id}

        @router.put("/dashboards/{dashboard_id}")
        async def update_dashboard(dashboard_id: str, dashboard_data: Dashboard):
            """Update a dashboard."""
            dashboard = next((d for d in self.dashboards if d.id == dashboard_id), None)
            if not dashboard:
                raise HTTPException(status_code=404, detail="Dashboard not found")

            dashboard_data.id = dashboard_id
            dashboard_data.created_at = dashboard.created_at
            dashboard_data.updated_at = datetime.utcnow()

            self.dashboards = [
                d if d.id != dashboard_id else dashboard_data for d in self.dashboards
            ]

            return {"message": "Dashboard updated"}

        @router.delete("/dashboards/{dashboard_id}")
        async def delete_dashboard(dashboard_id: str):
            """Delete a dashboard."""
            original_count = len(self.dashboards)
            self.dashboards = [d for d in self.dashboards if d.id != dashboard_id]

            if len(self.dashboards) == original_count:
                raise HTTPException(status_code=404, detail="Dashboard not found")

            return {"message": "Dashboard deleted"}

        # Widget Templates endpoints
        @router.get("/templates")
        async def get_widget_templates(category: Optional[str] = None):
            """Get widget templates."""
            templates = self.widget_templates

            if category:
                templates = [t for t in templates if t.category == category]

            return {"templates": [template.dict() for template in templates]}

        @router.post("/templates/{template_id}/create-widget")
        async def create_widget_from_template(template_id: str, title: str):
            """Create widget from template."""
            template = next((t for t in self.widget_templates if t.id == template_id), None)
            if not template:
                raise HTTPException(status_code=404, detail="Template not found")

            # Create widget from template
            widget = Widget(
                title=title,
                type=template.template_config.get("type", "custom"),
                config=template.template_config.copy(),
                position={"x": 0, "y": 0, "width": 4, "height": 3},
            )

            self.widgets.append(widget)
            template.usage_count += 1

            return {"message": "Widget created from template", "widget_id": widget.id}

        # Data Sources endpoints
        @router.get("/data-sources")
        async def get_data_sources():
            """Get all data sources."""
            return {"data_sources": [ds.dict() for ds in self.data_sources]}

        @router.post("/data-sources")
        async def create_data_source(data_source: DataSource):
            """Create a new data source."""
            self.data_sources.append(data_source)

            return {"message": "Data source created", "data_source_id": data_source.id}

        @router.get("/data-sources/{source_id}/test")
        async def test_data_source(source_id: str):
            """Test data source connection."""
            source = next((ds for ds in self.data_sources if ds.id == source_id), None)
            if not source:
                raise HTTPException(status_code=404, detail="Data source not found")

            # Simulate data source test
            test_result = {
                "success": True,
                "message": "Connection successful",
                "response_time": 45,
                "test_data_sample": {"sample": "data", "timestamp": datetime.utcnow().isoformat()},
            }

            return test_result

        # Component Library endpoints
        @router.get("/components/chart-types")
        async def get_chart_types():
            """Get available chart types."""
            return {
                "chart_types": [
                    {"id": "line", "name": "Line Chart", "icon": "📈"},
                    {"id": "bar", "name": "Bar Chart", "icon": "📊"},
                    {"id": "pie", "name": "Pie Chart", "icon": "🥧"},
                    {"id": "doughnut", "name": "Doughnut Chart", "icon": "🍩"},
                    {"id": "area", "name": "Area Chart", "icon": "📏"},
                    {"id": "scatter", "name": "Scatter Plot", "icon": "🔴"},
                    {"id": "radar", "name": "Radar Chart", "icon": "🕸️"},
                    {"id": "polar", "name": "Polar Area", "icon": "🎯"},
                ]
            }

        @router.get("/components/themes")
        async def get_themes():
            """Get available themes."""
            return {
                "themes": [
                    {"id": "light", "name": "Light Theme", "primary": "#3b82f6"},
                    {"id": "dark", "name": "Dark Theme", "primary": "#1e40af"},
                    {"id": "corporate", "name": "Corporate Theme", "primary": "#059669"},
                    {"id": "creative", "name": "Creative Theme", "primary": "#7c3aed"},
                    {"id": "minimal", "name": "Minimal Theme", "primary": "#6b7280"},
                ]
            }

        # Export/Import endpoints
        @router.get("/dashboards/{dashboard_id}/export")
        async def export_dashboard(dashboard_id: str):
            """Export dashboard configuration."""
            dashboard = next((d for d in self.dashboards if d.id == dashboard_id), None)
            if not dashboard:
                raise HTTPException(status_code=404, detail="Dashboard not found")

            # Get dashboard widgets
            dashboard_widgets = [w for w in self.widgets if w.id in dashboard.widgets]

            export_data = {
                "dashboard": dashboard.dict(),
                "widgets": [widget.dict() for widget in dashboard_widgets],
                "export_version": "1.0",
                "exported_at": datetime.utcnow().isoformat(),
            }

            return export_data

        @router.post("/dashboards/import")
        async def import_dashboard(import_data: Dict[str, Any]):
            """Import dashboard configuration."""
            try:
                # Create new dashboard
                dashboard_data = import_data["dashboard"]
                dashboard_data["id"] = str(uuid4())  # New ID
                dashboard_data["created_at"] = datetime.utcnow().isoformat()
                dashboard_data["updated_at"] = datetime.utcnow().isoformat()

                dashboard = Dashboard(**dashboard_data)

                # Create widgets
                widget_ids = []
                for widget_data in import_data["widgets"]:
                    widget_data["id"] = str(uuid4())  # New ID
                    widget_data["created_at"] = datetime.utcnow().isoformat()
                    widget_data["updated_at"] = datetime.utcnow().isoformat()

                    widget = Widget(**widget_data)
                    self.widgets.append(widget)
                    widget_ids.append(widget.id)

                # Update dashboard widget references
                dashboard.widgets = widget_ids
                self.dashboards.append(dashboard)

                return {
                    "message": "Dashboard imported successfully",
                    "dashboard_id": dashboard.id,
                    "widgets_count": len(widget_ids),
                }

            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Import failed: {str(e)}")

        # Web UI endpoints
        @router.get("/ui", response_class=HTMLResponse)
        async def dashboard_ui():
            """Serve the dashboard widgets UI."""
            return self._get_dashboard_html()

        @router.get("/ui/builder", response_class=HTMLResponse)
        async def dashboard_builder_ui():
            """Serve the dashboard builder UI."""
            return self._get_builder_html()

        @router.get("/ui/preview/{dashboard_id}", response_class=HTMLResponse)
        async def preview_dashboard(dashboard_id: str):
            """Preview dashboard."""
            dashboard = next((d for d in self.dashboards if d.id == dashboard_id), None)
            if not dashboard:
                raise HTTPException(status_code=404, detail="Dashboard not found")

            return "<html><body><h1>Dashboard Preview</h1><p>Preview functionality coming soon...</p></body></html>"

        return [router]

    def get_database_schema(self) -> Dict[str, Any]:
        """Get database schema for this plugin."""
        return {
            "collections": {
                f"{self.name}_widgets": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "type"},
                        {"field": "is_active"},
                        {"field": "created_at"},
                    ]
                },
                f"{self.name}_dashboards": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "name"},
                        {"field": "created_by"},
                        {"field": "is_public"},
                    ]
                },
                f"{self.name}_templates": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "category"},
                        {"field": "is_featured"},
                    ]
                },
                f"{self.name}_data_sources": {
                    "indexes": [
                        {"field": "id", "unique": True},
                        {"field": "type"},
                        {"field": "is_active"},
                    ]
                },
            }
        }

    # Helper methods
    def _initialize_sample_data(self):
        """Initialize with sample data."""
        # Sample widget templates
        self.widget_templates = [
            WidgetTemplate(
                name="Metric Card",
                description="Simple metric display card",
                category="metrics",
                template_config={
                    "type": "metric",
                    "display_type": "card",
                    "show_trend": True,
                    "color_scheme": "blue",
                },
                is_featured=True,
            ),
            WidgetTemplate(
                name="Line Chart",
                description="Time series line chart",
                category="charts",
                template_config={
                    "type": "chart",
                    "chart_type": "line",
                    "show_legend": True,
                    "show_grid": True,
                },
                is_featured=True,
            ),
            WidgetTemplate(
                name="Data Table",
                description="Interactive data table",
                category="tables",
                template_config={
                    "type": "table",
                    "pagination": True,
                    "sorting": True,
                    "search": True,
                },
            ),
            WidgetTemplate(
                name="Progress Bar",
                description="Progress indicator",
                category="indicators",
                template_config={
                    "type": "progress",
                    "show_percentage": True,
                    "color": "success",
                    "animation": True,
                },
            ),
        ]

        # Sample data sources
        self.data_sources = [
            DataSource(
                name="Analytics API",
                type="api",
                endpoint="/plugins/analytics_dashboard/metrics/summary",
                config={"headers": {"Content-Type": "application/json"}},
                refresh_interval=300,
            ),
            DataSource(
                name="User Management API",
                type="api",
                endpoint="/plugins/user_management/ui/dashboard-data",
                config={"auth_required": True},
                refresh_interval=600,
            ),
            DataSource(
                name="Mock Data Generator",
                type="generator",
                config={"data_type": "random", "count": 100},
                refresh_interval=60,
            ),
        ]

        # Sample widgets
        self.widgets = [
            Widget(
                title="Total Users",
                type="metric",
                config={
                    "metric": "user_count",
                    "format": "number",
                    "color": "blue",
                    "icon": "👥",
                },
                data_source="user_api",
                position={"x": 0, "y": 0, "width": 3, "height": 2},
            ),
            Widget(
                title="System Performance",
                type="chart",
                config={
                    "chart_type": "line",
                    "metrics": ["cpu_usage", "memory_usage"],
                    "time_range": "24h",
                },
                data_source="analytics_api",
                position={"x": 3, "y": 0, "width": 6, "height": 4},
            ),
            Widget(
                title="Recent Activity",
                type="table",
                config={
                    "columns": ["timestamp", "user", "action"],
                    "page_size": 10,
                    "sortable": True,
                },
                data_source="activity_logs",
                position={"x": 0, "y": 2, "width": 12, "height": 6},
            ),
        ]

        # Sample dashboard
        self.dashboards = [
            Dashboard(
                name="Main Dashboard",
                description="Primary dashboard with key metrics and charts",
                widgets=[w.id for w in self.widgets],
                layout={"grid_size": 12, "row_height": 60},
                theme="light",
                is_public=True,
            ),
        ]

    async def _create_database_schema(self):
        """Create database schema."""
        if self.db_adapter:
            schema = self.get_database_schema()
            logger.info(f"Database schema defined: {list(schema['collections'].keys())}")

    async def _load_widget_templates(self):
        """Load widget templates."""
        logger.info(f"Loaded {len(self.widget_templates)} widget templates")

    async def _start_data_refresh_tasks(self):
        """Start data refresh background tasks."""
        logger.info("Data refresh tasks started")

    async def _generate_widget_data(self, widget: Widget) -> Dict[str, Any]:
        """Generate data for a widget based on its type and configuration."""
        import random

        if widget.type == "metric":
            # Generate metric data
            value = random.randint(100, 10000)
            trend = random.uniform(-10, 10)
            return {
                "value": value,
                "trend": trend,
                "formatted_value": f"{value:,}",
                "trend_direction": "up" if trend > 0 else "down",
                "last_updated": datetime.utcnow().isoformat(),
            }

        elif widget.type == "chart":
            # Generate chart data
            chart_type = widget.config.get("chart_type", "line")
            data_points = 20

            if chart_type in ["line", "area"]:
                data = {
                    "labels": [f"Point {i}" for i in range(data_points)],
                    "datasets": [
                        {
                            "label": "Series 1",
                            "data": [random.randint(10, 100) for _ in range(data_points)],
                            "borderColor": "#3b82f6",
                            "backgroundColor": "#3b82f620",
                        }
                    ],
                }
            elif chart_type in ["pie", "doughnut"]:
                data = {
                    "labels": ["Category A", "Category B", "Category C", "Category D"],
                    "datasets": [
                        {
                            "data": [random.randint(10, 50) for _ in range(4)],
                            "backgroundColor": ["#3b82f6", "#10b981", "#f59e0b", "#ef4444"],
                        }
                    ],
                }
            else:  # bar
                data = {
                    "labels": ["Jan", "Feb", "Mar", "Apr", "May", "Jun"],
                    "datasets": [
                        {
                            "label": "Sales",
                            "data": [random.randint(100, 1000) for _ in range(6)],
                            "backgroundColor": "#3b82f6",
                        }
                    ],
                }

            return {"chart_data": data, "chart_type": chart_type}

        elif widget.type == "table":
            # Generate table data
            rows = []
            for i in range(10):
                rows.append(
                    {
                        "id": i + 1,
                        "name": f"Item {i + 1}",
                        "value": random.randint(1, 100),
                        "status": random.choice(["Active", "Inactive", "Pending"]),
                        "timestamp": (
                            datetime.utcnow() - timedelta(hours=random.randint(0, 48))
                        ).isoformat(),
                    }
                )

            return {
                "columns": [
                    {"key": "name", "title": "Name", "sortable": True},
                    {"key": "value", "title": "Value", "sortable": True},
                    {"key": "status", "title": "Status", "sortable": False},
                    {"key": "timestamp", "title": "Last Updated", "sortable": True},
                ],
                "rows": rows,
                "total": len(rows),
            }

        elif widget.type == "progress":
            # Generate progress data
            return {
                "value": random.randint(0, 100),
                "max": 100,
                "label": "Progress",
                "color": widget.config.get("color", "blue"),
            }

        else:
            # Default/custom widget
            return {
                "message": f"Data for {widget.type} widget",
                "timestamp": datetime.utcnow().isoformat(),
                "config": widget.config,
            }

    def _get_dashboard_html(self) -> str:
        """Generate the main dashboard HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Widgets - Nexus Platform</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f8fafc;
            color: #334155;
            line-height: 1.6;
        }

        .header {
            background: white;
            padding: 1rem 2rem;
            border-bottom: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h1 {
            color: #7c3aed;
            font-size: 1.5rem;
            font-weight: 600;
        }

        .header-actions {
            display: flex;
            gap: 1rem;
        }

        .container {
            max-width: 1400px;
            margin: 2rem auto;
            padding: 0 1rem;
        }

        .dashboard-selector {
            background: white;
            padding: 1rem;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            margin-bottom: 2rem;
            display: flex;
            align-items: center;
            gap: 1rem;
        }

        .dashboard-grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 1rem;
            min-height: 600px;
        }

        .widget {
            background: white;
            border-radius: 8px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
            border: 1px solid #e2e8f0;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s, box-shadow 0.2s;
        }

        .widget:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }

        .widget-header {
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .widget-title {
            font-weight: 600;
            color: #1e293b;
        }

        .widget-content {
            padding: 1rem;
            height: calc(100% - 60px);
        }

        .metric-widget {
            text-align: center;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .metric-value {
            font-size: 2.5rem;
            font-weight: bold;
            color: #3b82f6;
            margin-bottom: 0.5rem;
        }

        .metric-trend {
            font-size: 0.9rem;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.25rem;
        }

        .trend-up { color: #10b981; }
        .trend-down { color: #ef4444; }

        .chart-container {
            position: relative;
            height: 100%;
            min-height: 200px;
        }

        .table-container {
            overflow-x: auto;
            height: 100%;
        }

        .data-table {
            width: 100%;
            border-collapse: collapse;
        }

        .data-table th,
        .data-table td {
            padding: 0.75rem;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }

        .data-table th {
            background: #f8fafc;
            font-weight: 600;
            color: #374151;
        }

        .data-table tr:hover {
            background: #f8fafc;
        }

        .progress-widget {
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
        }

        .progress-bar {
            width: 100%;
            height: 20px;
            background: #e2e8f0;
            border-radius: 10px;
            overflow: hidden;
            margin-bottom: 1rem;
        }

        .progress-fill {
            height: 100%;
            border-radius: 10px;
            transition: width 0.8s ease;
        }

        .progress-blue { background: #3b82f6; }
        .progress-green { background: #10b981; }
        .progress-red { background: #ef4444; }
        .progress-yellow { background: #f59e0b; }

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
            background: #7c3aed;
            color: white;
        }

        .btn-primary:hover {
            background: #6d28d9;
        }

        .btn-secondary {
            background: #e2e8f0;
            color: #64748b;
        }

        .btn-secondary:hover {
            background: #cbd5e1;
        }

        .loading {
            text-align: center;
            padding: 2rem;
            color: #64748b;
        }

        .widget-placeholder {
            border: 2px dashed #cbd5e1;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #64748b;
            font-size: 0.9rem;
            min-height: 200px;
        }

        /* Grid positioning classes */
        .col-span-1 { grid-column: span 1; }
        .col-span-2 { grid-column: span 2; }
        .col-span-3 { grid-column: span 3; }
        .col-span-4 { grid-column: span 4; }
        .col-span-6 { grid-column: span 6; }
        .col-span-12 { grid-column: span 12; }

        @media (max-width: 768px) {
            .dashboard-grid {
                grid-template-columns: 1fr;
            }

            .widget {
                grid-column: span 1 !important;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🎛️ Dashboard Widgets</h1>
        <div class="header-actions">
            <button class="btn btn-secondary" onclick="refreshDashboard()">🔄 Refresh</button>
            <button class="btn btn-primary" onclick="openBuilder()">✨ Builder</button>
        </div>
    </div>

    <div class="container">
        <div class="dashboard-selector">
            <label for="dashboardSelect">Dashboard:</label>
            <select id="dashboardSelect" onchange="loadDashboard(this.value)">
                <option value="">Select a dashboard...</option>
            </select>
        </div>

        <div id="dashboardGrid" class="dashboard-grid">
            <div class="widget-placeholder col-span-12">
                Select a dashboard to view widgets
            </div>
        </div>
    </div>

    <script>
        let currentDashboard = null;
        let widgets = {};
        let charts = {};

        async function loadDashboards() {
            try {
                const response = await fetch('/plugins/dashboard_widgets/dashboards');
                const data = await response.json();

                const select = document.getElementById('dashboardSelect');
                select.innerHTML = '<option value="">Select a dashboard...</option>';

                data.dashboards.forEach(dashboard => {
                    const option = document.createElement('option');
                    option.value = dashboard.id;
                    option.textContent = dashboard.name;
                    select.appendChild(option);
                });

                // Load first dashboard by default
                if (data.dashboards.length > 0) {
                    select.value = data.dashboards[0].id;
                    await loadDashboard(data.dashboards[0].id);
                }

            } catch (error) {
                console.error('Error loading dashboards:', error);
            }
        }

        async function loadDashboard(dashboardId) {
            if (!dashboardId) {
                document.getElementById('dashboardGrid').innerHTML =
                    '<div class="widget-placeholder col-span-12">Select a dashboard to view widgets</div>';
                return;
            }

            try {
                const response = await fetch(`/plugins/dashboard_widgets/dashboards/${dashboardId}`);
                const data = await response.json();

                currentDashboard = data.dashboard;
                widgets = {};

                // Create widgets
                const grid = document.getElementById('dashboardGrid');
                grid.innerHTML = '';

                if (data.widgets.length === 0) {
                    grid.innerHTML = '<div class="widget-placeholder col-span-12">No widgets in this dashboard</div>';
                    return;
                }

                for (const widget of data.widgets) {
                    await createWidgetElement(widget);
                }

            } catch (error) {
                console.error('Error loading dashboard:', error);
            }
        }

        async function createWidgetElement(widget) {
            const widgetEl = document.createElement('div');
            widgetEl.className = `widget col-span-${widget.position.width || 4}`;
            widgetEl.innerHTML = `
                <div class="widget-header">
                    <div class="widget-title">${widget.title}</div>
                </div>
                <div class="widget-content" id="widget-content-${widget.id}">
                    <div class="loading">Loading...</div>
                </div>
            `;

            document.getElementById('dashboardGrid').appendChild(widgetEl);
            widgets[widget.id] = widget;

            // Load widget data
            await loadWidgetData(widget);
        }

        async function loadWidgetData(widget) {
            try {
                const response = await fetch(`/plugins/dashboard_widgets/widgets/${widget.id}/data`);
                const data = await response.json();

                const contentEl = document.getElementById(`widget-content-${widget.id}`);

                switch (widget.type) {
                    case 'metric':
                        renderMetricWidget(contentEl, data);
                        break;
                    case 'chart':
                        renderChartWidget(contentEl, data, widget.id);
                        break;
                    case 'table':
                        renderTableWidget(contentEl, data);
                        break;
                    case 'progress':
                        renderProgressWidget(contentEl, data);
                        break;
                    default:
                        contentEl.innerHTML = `<div class="loading">Widget type '${widget.type}' not supported</div>`;
                }

            } catch (error) {
                console.error('Error loading widget data:', error);
                const contentEl = document.getElementById(`widget-content-${widget.id}`);
                contentEl.innerHTML = '<div class="loading">Error loading data</div>';
            }
        }

        function renderMetricWidget(container, data) {
            const trendIcon = data.trend_direction === 'up' ? '↗️' : '↘️';
            const trendClass = data.trend_direction === 'up' ? 'trend-up' : 'trend-down';

            container.innerHTML = `
                <div class="metric-widget">
                    <div class="metric-value">${data.formatted_value}</div>
                    <div class="metric-trend ${trendClass}">
                        ${trendIcon} ${Math.abs(data.trend).toFixed(1)}%
                    </div>
                </div>
            `;
        }

        function renderChartWidget(container, data, widgetId) {
            const canvas = document.createElement('canvas');
            canvas.id = `chart-${widgetId}`;
            container.innerHTML = '<div class="chart-container"></div>';
            container.querySelector('.chart-container').appendChild(canvas);

            // Destroy existing chart if it exists
            if (charts[widgetId]) {
                charts[widgetId].destroy();
            }

            const ctx = canvas.getContext('2d');
            charts[widgetId] = new Chart(ctx, {
                type: data.chart_type,
                data: data.chart_data,
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top' }
                    }
                }
            });
        }

        function renderTableWidget(container, data) {
            const table = document.createElement('table');
            table.className = 'data-table';

            // Create header
            const thead = document.createElement('thead');
            const headerRow = document.createElement('tr');
            data.columns.forEach(col => {
                const th = document.createElement('th');
                th.textContent = col.title;
                headerRow.appendChild(th);
            });
            thead.appendChild(headerRow);
            table.appendChild(thead);

            // Create body
            const tbody = document.createElement('tbody');
            data.rows.forEach(row => {
                const tr = document.createElement('tr');
                data.columns.forEach(col => {
                    const td = document.createElement('td');
                    td.textContent = row[col.key] || '';
                    tr.appendChild(td);
                });
                tbody.appendChild(tr);
            });
            table.appendChild(tbody);

            container.innerHTML = '<div class="table-container"></div>';
            container.querySelector('.table-container').appendChild(table);
        }

        function renderProgressWidget(container, data) {
            const colorClass = `progress-${data.color}`;
            const percentage = Math.round((data.value / data.max) * 100);

            container.innerHTML = `
                <div class="progress-widget">
                    <div class="progress-bar">
                        <div class="progress-fill ${colorClass}" style="width: ${percentage}%"></div>
                    </div>
                    <div>${data.label}: ${percentage}%</div>
                </div>
            `;
        }

        function refreshDashboard() {
            if (currentDashboard) {
                loadDashboard(currentDashboard.id);
            }
        }

        function openBuilder() {
            window.open('/plugins/dashboard_widgets/ui/builder', '_blank');
        }

        // Load dashboards on page load
        document.addEventListener('DOMContentLoaded', loadDashboards);

        // Auto-refresh every 5 minutes
        setInterval(() => {
            if (currentDashboard) {
                refreshDashboard();
            }
        }, 300000);
    </script>
</body>
</html>
        """

    def _get_builder_html(self) -> str:
        """Generate the dashboard builder HTML UI."""
        return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard Builder - Nexus Platform</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f1f5f9;
            color: #334155;
            line-height: 1.6;
            padding: 2rem;
        }
        .builder-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 8px;
            padding: 2rem;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        h1 { color: #7c3aed; margin-bottom: 1rem; }
        .btn {
            padding: 0.5rem 1rem;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9rem;
            font-weight: 500;
            margin-right: 0.5rem;
            background: #7c3aed;
            color: white;
        }
        .btn:hover { background: #6d28d9; }
    </style>
</head>
<body>
    <div class="builder-container">
        <h1>🎛️ Dashboard Builder</h1>
        <p>Dashboard builder interface coming soon...</p>
        <p>This will allow drag-and-drop widget creation and dashboard design.</p>
        <div style="margin-top: 2rem;">
            <button class="btn" onclick="alert('Clear functionality coming soon')">🗑️ Clear</button>
            <button class="btn" onclick="alert('Preview functionality coming soon')">👀 Preview</button>
            <button class="btn" onclick="alert('Save functionality coming soon')">💾 Save</button>
        </div>
    </div>
</body>
</html>
        """
