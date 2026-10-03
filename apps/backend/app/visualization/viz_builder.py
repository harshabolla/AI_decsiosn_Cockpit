"""
Visualization Builder — Structured Chart Specifications
=======================================================
Produces JSON chart specs from query results.
The LLM does NOT generate JavaScript/HTML.
The frontend renders the spec using Recharts.
"""
from __future__ import annotations

from typing import Any


def build_visualization(
    intent: dict[str, Any],
    rows: list[dict[str, Any]],
    columns: list[str],
) -> dict[str, Any] | None:
    """
    Build a visualization spec from intent and data.
    Returns a structured spec that the frontend renders.
    """
    if not rows or not columns:
        return None

    metrics = intent.get("metrics", ["net_sales"])
    dimensions = intent.get("dimensions", [])
    filters = intent.get("filters", {})
    region = filters.get("region")

    # Determine the primary dimension for x-axis
    x_col = _find_column(columns, ["product_name", "month_name", "region_name", "channel"])
    y_col = _find_column(columns, ["net_sales", "gross_revenue", "units_sold", "stock_on_hand", "days_of_supply"])

    if not x_col or not y_col:
        return _table_spec(columns, rows)

    # Choose chart type based on dimensions
    if "month" in dimensions or "month_name" in columns:
        chart_type = "line"
    elif len(rows) <= 5:
        chart_type = "bar"
    else:
        chart_type = "bar"

    title_parts = [_label(y_col)]
    if region:
        title_parts.append(f"— {region}")
    if filters.get("time_period"):
        title_parts.append(f"({_period_label(filters['time_period'])})")

    return {
        "type": chart_type,
        "title": " ".join(title_parts),
        "x": x_col,
        "y": y_col,
        "data": rows,
        "config": {
            "color": "#6366f1",
            "grid": True,
            "legend": False,
        }
    }


def _find_column(available: list[str], preferences: list[str]) -> str | None:
    for col in preferences:
        if col in available:
            return col
    return None


def _label(col: str) -> str:
    return col.replace("_", " ").title()


def _period_label(period: str) -> str:
    labels = {
        "last_month": "Last Month",
        "last_quarter": "Last Quarter",
        "last_6_months": "Last 6 Months",
        "ytd": "Year to Date",
    }
    return labels.get(period, period)


def _table_spec(columns: list[str], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "type": "table",
        "title": "Query Results",
        "columns": columns,
        "data": rows,
        "config": {},
    }
