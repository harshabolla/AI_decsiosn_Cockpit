"""
Semantic Layer — Business Metadata Registry
===========================================
Maps business terminology to physical schema, aggregations,
and approved dimensions. The LLM must resolve terminology
through this layer instead of guessing physical column names.
"""
from __future__ import annotations

from typing import Any

import structlog
import yaml

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Embedded semantic metadata (Phase 1 — YAML config, later: Snowflake Semantic Views)
# ---------------------------------------------------------------------------
_SEMANTIC_YAML = """
metrics:
  net_sales:
    name: Net Sales
    description: >
      Total revenue after configured discounts, returns, and trade
      deductions per the Opella Commercial Policy v2.3.
    formula: "SUM(fact_sales.net_sales)"
    unit: USD
    allowed_dimensions: [product, region, channel, month, quarter, year]
    physical_columns:
      - table: fact_sales
        column: net_sales
        aggregation: SUM

  gross_revenue:
    name: Gross Revenue
    description: Total invoice value before any deductions.
    formula: "SUM(fact_sales.gross_revenue)"
    unit: USD
    allowed_dimensions: [product, region, channel, month, quarter, year]
    physical_columns:
      - table: fact_sales
        column: gross_revenue
        aggregation: SUM

  units_sold:
    name: Units Sold
    description: Total number of units sold to trade customers.
    formula: "SUM(fact_sales.units_sold)"
    unit: units
    allowed_dimensions: [product, region, channel, month, quarter, year]
    physical_columns:
      - table: fact_sales
        column: units_sold
        aggregation: SUM

  stock_on_hand:
    name: Stock on Hand
    description: Available inventory units at end of period.
    formula: "SUM(fact_inventory.stock_on_hand)"
    unit: units
    allowed_dimensions: [product, region, month]
    physical_columns:
      - table: fact_inventory
        column: stock_on_hand
        aggregation: SUM

  days_of_supply:
    name: Days of Supply
    description: >
      Estimated number of days current stock can cover demand
      at the current consumption rate.
    formula: "AVG(fact_inventory.days_of_supply)"
    unit: days
    allowed_dimensions: [product, region, month]
    physical_columns:
      - table: fact_inventory
        column: days_of_supply
        aggregation: AVG

dimensions:
  product:
    name: Product
    physical_table: dim_product
    key_column: product_key
    label_column: product_name
    join_on: fact_sales.product_key = dim_product.product_key

  region:
    name: Region / Country
    physical_table: dim_region
    key_column: region_key
    label_column: region_name
    join_on: fact_sales.region_key = dim_region.region_key

  month:
    name: Month
    physical_table: dim_date
    key_column: date_key
    label_column: month_name
    join_on: fact_sales.date_key = dim_date.date_key

  channel:
    name: Sales Channel
    physical_table: fact_sales
    key_column: channel
    label_column: channel
    join_on: null

aliases:
  "sales":          "net_sales"
  "revenue":        "net_sales"
  "income":         "net_sales"
  "turnover":       "net_sales"
  "top line":       "gross_revenue"
  "inventory":      "stock_on_hand"
  "stock":          "stock_on_hand"
  "dos":            "days_of_supply"
  "country":        "region"
  "market":         "region"
  "medicine":       "product"
  "drug":           "product"
  "brand":          "product"

products:
  - Allegra
  - Buscopan
  - Doliprane
  - Dulcolax
  - Mucosolvan

regions:
  - India
  - France
  - Germany
  - UK
"""


class SemanticLayer:
    """
    Resolves business terminology to physical schema constructs.
    """

    def __init__(self) -> None:
        self._meta: dict[str, Any] = yaml.safe_load(_SEMANTIC_YAML)
        self._metrics: dict[str, Any] = self._meta["metrics"]
        self._dimensions: dict[str, Any] = self._meta["dimensions"]
        self._aliases: dict[str, str] = self._meta["aliases"]

    def resolve_metric(self, term: str) -> dict[str, Any] | None:
        """Resolve a business term to its metric definition."""
        key = term.lower().strip()
        # Direct match
        if key in self._metrics:
            return self._metrics[key]
        # Alias lookup
        if key in self._aliases:
            resolved = self._aliases[key]
            return self._metrics.get(resolved)
        return None

    def resolve_dimension(self, term: str) -> dict[str, Any] | None:
        """Resolve a business term to its dimension definition."""
        key = term.lower().strip()
        if key in self._dimensions:
            return self._dimensions[key]
        if key in self._aliases:
            resolved = self._aliases[key]
            return self._dimensions.get(resolved)
        return None

    def get_schema_context(self, metrics: list[str], dimensions: list[str]) -> str:
        """
        Build a compact schema context string for the SQL prompt.
        Only includes tables/columns relevant to the request.
        """
        lines: list[str] = ["-- Semantic Schema Context (resolved from business terms)"]
        tables_used: set[str] = set()

        for m_term in metrics:
            metric = self.resolve_metric(m_term)
            if metric:
                for pc in metric.get("physical_columns", []):
                    tables_used.add(pc["table"])
                lines.append(
                    f"-- Metric: {metric['name']} → {metric['formula']}"
                )

        for d_term in dimensions:
            dim = self.resolve_dimension(d_term)
            if dim:
                tables_used.add(dim["physical_table"])
                if dim.get("join_on"):
                    lines.append(f"-- Dimension: {dim['name']} → JOIN {dim['physical_table']} ON {dim['join_on']}")

        lines.append(f"-- Tables involved: {', '.join(sorted(tables_used))}")
        return "\n".join(lines)

    def get_all_metrics_summary(self) -> list[dict[str, str]]:
        return [
            {"key": k, "name": v["name"], "description": v["description"].strip()}
            for k, v in self._metrics.items()
        ]

    @property
    def known_products(self) -> list[str]:
        return self._meta.get("products", [])

    @property
    def known_regions(self) -> list[str]:
        return self._meta.get("regions", [])


# Singleton
_semantic_layer: SemanticLayer | None = None


def get_semantic_layer() -> SemanticLayer:
    global _semantic_layer
    if _semantic_layer is None:
        _semantic_layer = SemanticLayer()
    return _semantic_layer
