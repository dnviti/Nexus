"""
Data Components for Nexus UI System
Provides components for displaying and manipulating data
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from .base import BaseComponent, ComponentProps


class TableVariant(Enum):
    """Table style variants."""

    DEFAULT = "default"
    STRIPED = "striped"
    BORDERED = "bordered"
    HOVER = "hover"
    COMPACT = "compact"


@dataclass
class TableColumn:
    """Table column definition."""

    key: str
    title: str
    sortable: bool = False
    searchable: bool = False
    width: Optional[str] = None
    align: str = "left"
    formatter: Optional[Callable[[Any], str]] = None


@dataclass
class TableProps(ComponentProps):
    """Properties for table components."""

    variant: TableVariant = TableVariant.DEFAULT
    sortable: bool = False
    searchable: bool = False
    paginated: bool = False
    page_size: int = 10
    responsive: bool = True


class Table(BaseComponent):
    """Table component for displaying tabular data."""

    def __init__(
        self,
        columns: Optional[List[TableColumn]] = None,
        data: Optional[List[Dict[str, Any]]] = None,
        variant: TableVariant = TableVariant.DEFAULT,
        props: Optional[TableProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("table", props, **kwargs)
        self.columns = columns or []
        self.data = data or []
        self.variant = variant

        # Add table classes
        self.add_class("table")
        self.add_class(f"table-{variant.value}")

    def add_column(self, key: str, title: str, sortable: bool = False, **kwargs: Any) -> "Table":
        """Add a column to the table."""
        column = TableColumn(key=key, title=title, sortable=sortable, **kwargs)
        self.columns.append(column)
        return self

    def set_table_data(self, data: List[Dict[str, Any]]) -> "Table":
        """Set table data."""
        self.data = data
        return self

    def render(self) -> str:
        """Render table."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()

        # Table header
        header_html = "<thead><tr>"
        for column in self.columns:
            col_classes = []
            if column.align != "left":
                col_classes.append(f"text-{column.align}")
            if column.sortable:
                col_classes.append("sortable")

            col_attrs = ""
            if col_classes:
                col_attrs = f' class="{" ".join(col_classes)}"'
            if column.width:
                col_attrs += f' style="width: {column.width}"'

            header_html += f"<th{col_attrs}>{column.title}</th>"
        header_html += "</tr></thead>"

        # Table body
        body_html = "<tbody>"
        for row in self.data:
            body_html += "<tr>"
            for column in self.columns:
                value = row.get(column.key, "")
                if column.formatter:
                    value = column.formatter(value)

                cell_classes = []
                if column.align != "left":
                    cell_classes.append(f"text-{column.align}")

                cell_attrs = ""
                if cell_classes:
                    cell_attrs = f' class="{" ".join(cell_classes)}"'

                body_html += f"<td{cell_attrs}>{value}</td>"
            body_html += "</tr>"
        body_html += "</tbody>"

        return f"<table {attrs}>{header_html}{body_html}</table>"


class DataGrid(BaseComponent):
    """Advanced data grid with sorting, filtering, and pagination."""

    def __init__(
        self,
        columns: Optional[List[TableColumn]] = None,
        data: Optional[List[Dict[str, Any]]] = None,
        sortable: bool = True,
        searchable: bool = True,
        paginated: bool = True,
        page_size: int = 10,
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.columns = columns or []
        self.data = data or []
        self.sortable = sortable
        self.searchable = searchable
        self.paginated = paginated
        self.page_size = page_size

        self.add_class("data-grid")

    def render(self) -> str:
        """Render data grid with controls."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()
        content_parts = []

        # Search bar
        if self.searchable:
            search_html = """
            <div class="data-grid-search">
                <input type="text"
                       class="form-control"
                       placeholder="Search..."
                       id="grid-search">
            </div>
            """
            content_parts.append(search_html)

        # Table
        table = Table(self.columns, self.data, TableVariant.STRIPED)
        table.add_class("data-grid-table")
        content_parts.append(table.render())

        # Pagination
        if self.paginated:
            pagination_html = """
            <div class="data-grid-pagination">
                <nav>
                    <ul class="pagination">
                        <li class="page-item disabled">
                            <span class="page-link">Previous</span>
                        </li>
                        <li class="page-item active">
                            <span class="page-link">1</span>
                        </li>
                        <li class="page-item">
                            <a class="page-link" href="#">2</a>
                        </li>
                        <li class="page-item">
                            <a class="page-link" href="#">Next</a>
                        </li>
                    </ul>
                </nav>
            </div>
            """
            content_parts.append(pagination_html)

        return f'<div {attrs}>{"".join(content_parts)}</div>'


@dataclass
class ChartData:
    """Chart data structure."""

    labels: List[str] = field(default_factory=list)
    datasets: List[Dict[str, Any]] = field(default_factory=list)


class ChartType(Enum):
    """Chart types."""

    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    DOUGHNUT = "doughnut"
    AREA = "area"


class Chart(BaseComponent):
    """Chart component for data visualization."""

    def __init__(
        self,
        chart_type: ChartType = ChartType.BAR,
        data: Optional[ChartData] = None,
        width: str = "400px",
        height: str = "300px",
        props: Optional[ComponentProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.chart_type = chart_type
        self.chart_data = data or ChartData()
        self.width = width
        self.height = height

        self.add_class("chart")
        self.add_class(f"chart-{chart_type.value}")

    def set_chart_data(self, data: ChartData) -> "Chart":
        """Set chart data."""
        self.chart_data = data
        return self

    def render(self) -> str:
        """Render chart."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()

        # Chart container with canvas
        chart_id = self.props.id or f"chart-{id(self)}"
        canvas_html = f"""
        <canvas id="{chart_id}-canvas"
                width="{self.width}"
                height="{self.height}">
        </canvas>
        """

        # Chart script
        data_json = {
            "type": self.chart_type.value,
            "data": {"labels": self.chart_data.labels, "datasets": self.chart_data.datasets},
            "options": {"responsive": True, "maintainAspectRatio": False},
        }

        script_html = f"""
        <script>
            (function() {{
                const ctx = document.getElementById('{chart_id}-canvas').getContext('2d');
                new Chart(ctx, {data_json});
            }})();
        </script>
        """

        return f"<div {attrs}>{canvas_html}{script_html}</div>"


@dataclass
class MetricCardProps(ComponentProps):
    """Properties for metric card components."""

    title: str = ""
    value: Union[str, int, float] = ""
    unit: str = ""
    trend: Optional[str] = None  # "up", "down", "neutral"
    color: str = "primary"


class MetricCard(BaseComponent):
    """Metric card component for displaying key metrics."""

    def __init__(
        self,
        title: str = "",
        value: Union[str, int, float] = "",
        unit: str = "",
        trend: Optional[str] = None,
        color: str = "primary",
        props: Optional[MetricCardProps] = None,
        **kwargs: Any,
    ) -> None:
        super().__init__("div", props, **kwargs)
        self.title = title
        self.value = value
        self.unit = unit
        self.trend = trend
        self.color = color

        # Add metric card classes
        self.add_class("metric-card")
        self.add_class(f"metric-card-{color}")

        if trend:
            self.add_class(f"metric-trend-{trend}")

    def render(self) -> str:
        """Render metric card."""
        if not self.props.visible:
            return ""

        attrs = self._render_attributes()

        # Trend icon
        trend_icons = {"up": "📈", "down": "📉", "neutral": "➡️"}
        trend_icon = trend_icons.get(self.trend or "", "")

        content = f"""
        <div class="metric-card-header">
            <h4 class="metric-card-title">{self.title}</h4>
            {f'<span class="metric-trend">{trend_icon}</span>' if trend_icon else ''}
        </div>
        <div class="metric-card-body">
            <div class="metric-value">{self.value}</div>
            {f'<div class="metric-unit">{self.unit}</div>' if self.unit else ''}
        </div>
        """

        return f"<div {attrs}>{content}</div>"


# Convenience functions
def table(
    columns: Optional[List[Dict[str, Any]]] = None,
    data: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> Table:
    """Create a table with column definitions."""
    if columns:
        table_columns = [
            TableColumn(
                key=col.get("key", ""),
                title=col.get("title", ""),
                sortable=col.get("sortable", False),
                **{k: v for k, v in col.items() if k not in ["key", "title", "sortable"]},
            )
            for col in columns
        ]
    else:
        table_columns = []

    return Table(table_columns, data, **kwargs)


def data_grid(
    columns: Optional[List[Dict[str, Any]]] = None,
    data: Optional[List[Dict[str, Any]]] = None,
    **kwargs: Any,
) -> DataGrid:
    """Create a data grid with column definitions."""
    if columns:
        grid_columns = [
            TableColumn(
                key=col.get("key", ""),
                title=col.get("title", ""),
                sortable=col.get("sortable", True),
                **{k: v for k, v in col.items() if k not in ["key", "title", "sortable"]},
            )
            for col in columns
        ]
    else:
        grid_columns = []

    return DataGrid(grid_columns, data, **kwargs)


def chart(chart_type: Union[ChartType, str] = ChartType.BAR, **kwargs: Any) -> Chart:
    """Create a chart."""
    if isinstance(chart_type, str):
        chart_type = ChartType(chart_type)
    return Chart(chart_type, **kwargs)


def metric_card(title: str, value: Union[str, int, float], **kwargs: Any) -> MetricCard:
    """Create a metric card."""
    return MetricCard(title, value, **kwargs)
