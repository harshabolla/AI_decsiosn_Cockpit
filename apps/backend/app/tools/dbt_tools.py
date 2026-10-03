"""
dbt Governance Tools
====================
Inspects dbt model definitions, documentation, tests, and lineage DAG.
"""
from __future__ import annotations

from typing import Any, Dict
from app.tools.base import BaseTool

# Static dbt manifest metadata seeded from project marts
DBT_MANIFEST = {
    "models": {
        "stg_sales": {
            "description": "Staged commercial sales transactions cleaned from ERP.",
            "columns": ["sale_id", "sale_date", "product_name", "region_name", "channel_name", "gross_amount", "net_amount", "quantity"],
            "upstream": ["raw_erp_sales"],
            "tests": ["unique(sale_id)", "not_null(net_amount)", "accepted_values(region_name)"],
        },
        "stg_inventory": {
            "description": "Staged warehouse stock positions across manufacturing and distribution hubs.",
            "columns": ["inventory_id", "snapshot_date", "product_name", "country_name", "stock_on_hand_units", "daily_burn_rate"],
            "upstream": ["raw_wms_stock"],
            "tests": ["not_null(stock_on_hand_units)", "positive_value(daily_burn_rate)"],
        },
        "fct_sales_monthly": {
            "description": "Gold-layer analytical mart aggregating monthly net sales and units across product, region, and channel.",
            "columns": ["year_month", "product_name", "region_name", "channel_name", "total_gross_revenue", "total_net_sales", "total_units"],
            "upstream": ["stg_sales"],
            "tests": ["not_null(total_net_sales)", "check_positive_revenue"],
        },
    }
}


class GetModelLineageTool(BaseTool):
    name = "get_dbt_lineage"
    description = "Retrieve upstream sources and downstream analytical models for a dbt model."
    target_system = "dbt"
    risk_level = "low"
    requires_approval = False

    parameters = {
        "type": "object",
        "properties": {
            "model_name": {
                "type": "string",
                "description": "dbt model name (e.g., fct_sales_monthly, stg_sales).",
            },
        },
        "required": ["model_name"],
    }

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        m_name = kwargs.get("model_name", "").lower()
        model = DBT_MANIFEST["models"].get(m_name)
        if not model:
            return {
                "status": "not_found",
                "available_models": list(DBT_MANIFEST["models"].keys()),
            }

        return {
            "status": "success",
            "model_name": m_name,
            "upstream": model["upstream"],
            "description": model["description"],
            "columns": model["columns"],
            "tests": model["tests"],
        }
