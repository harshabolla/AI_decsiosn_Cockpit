"""
dbt MCP Server
Exposes tools for compiling models, running transformations,
and querying dbt semantic layer metric lineage.
"""
from typing import Any, Dict
import structlog

logger = structlog.get_logger(__name__)

TOOLS = [
    {
        "name": "dbt_get_metric_lineage",
        "description": "Inspect the lineage and upstream sources of a business metric.",
        "parameters": {
            "type": "object",
            "properties": {
                "metric_name": {"type": "string", "description": "e.g. net_sales, days_of_supply"}
            },
            "required": ["metric_name"]
        }
    },
    {
        "name": "dbt_run_model",
        "description": "Trigger an incremental or full refresh of a dbt model in the warehouse.",
        "parameters": {
            "type": "object",
            "properties": {
                "model_name": {"type": "string", "description": "e.g. fct_sales_monthly"}
            },
            "required": ["model_name"]
        }
    }
]


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("mcp_dbt_call", tool=tool_name, args=arguments)
    if tool_name == "dbt_get_metric_lineage":
        metric = arguments.get("metric_name", "")
        return {
            "metric": metric,
            "model": "fct_sales_monthly",
            "upstream_sources": ["raw_erp.sales_transactions", "raw_mdm.product_master"],
            "transformations": ["stg_sales", "stg_products", "int_sales_enriched"],
            "grain": "monthly"
        }
    elif tool_name == "dbt_run_model":
        model = arguments.get("model_name", "")
        return {
            "status": "success",
            "model": model,
            "execution_time_seconds": 3.42,
            "rows_affected": 2400
        }
    return {"error": f"Unknown tool: {tool_name}"}
