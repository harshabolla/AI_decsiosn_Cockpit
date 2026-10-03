"""
Snowflake MCP Server
Exposes tools for querying schema, running read-only analytical SQL,
and inspecting table lineage.
"""
from typing import Any, Dict, List
import structlog

logger = structlog.get_logger(__name__)

TOOLS = [
    {
        "name": "snowflake_query",
        "description": "Execute a governed, read-only SQL query against Snowflake data warehouse.",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string",
                    "description": "The SELECT query to execute"
                },
                "max_rows": {
                    "type": "integer",
                    "default": 100,
                    "description": "Maximum number of rows to return"
                }
            },
            "required": ["sql"]
        }
    },
    {
        "name": "snowflake_describe_table",
        "description": "Retrieve column definitions and data types for a table.",
        "parameters": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Name of the table (e.g. fact_sales, dim_product)"
                }
            },
            "required": ["table_name"]
        }
    }
]


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("mcp_snowflake_call", tool=tool_name, args=arguments)
    if tool_name == "snowflake_query":
        sql = arguments.get("sql", "")
        # Enforce read-only restriction
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"]
        if any(word in sql.upper() for word in forbidden):
            return {"error": "Permission denied: Non-read-only queries are strictly prohibited."}
        return {
            "status": "success",
            "sql": sql,
            "columns": ["product_name", "total_sales"],
            "rows": [
                {"product_name": "Doliprane", "total_sales": 1420000},
                {"product_name": "Buscopan", "total_sales": 890000},
                {"product_name": "Allegra", "total_sales": 640000}
            ],
            "row_count": 3,
            "adapter": "SNOWFLAKE_MCP"
        }
    elif tool_name == "snowflake_describe_table":
        table = arguments.get("table_name", "").lower()
        return {
            "status": "success",
            "table": table,
            "columns": ["sale_id", "sale_date", "product_key", "net_sales", "units_sold"]
        }
    return {"error": f"Unknown tool: {tool_name}"}
