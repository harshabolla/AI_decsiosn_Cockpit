"""
Snowflake Warehouse Tools
=========================
Governed read-only execution tools connecting to WarehouseClient.
"""
from __future__ import annotations

from typing import Any, Dict
from app.tools.base import BaseTool
from app.data import get_warehouse_client, WarehouseClient
from app.security.sql_validator import validate_sql


class ExecuteReadOnlyQueryTool(BaseTool):
    name = "execute_readonly_query"
    description = "Execute a governed, validated read-only SQL query against the analytical warehouse (Snowflake/DuckDB)."
    target_system = "Snowflake"
    risk_level = "low"
    requires_approval = False

    parameters = {
        "type": "object",
        "properties": {
            "sql": {
                "type": "string",
                "description": "Validated read-only SELECT query to execute.",
            },
            "max_rows": {
                "type": "integer",
                "default": 1000,
                "description": "Maximum number of rows to return.",
            },
        },
        "required": ["sql"],
    }

    def __init__(self, warehouse_client: WarehouseClient | None = None) -> None:
        super().__init__()
        self.warehouse = warehouse_client or get_warehouse_client()

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        sql = kwargs.get("sql", "")
        max_rows = kwargs.get("max_rows", 1000)

        # Validate SQL
        val = validate_sql(sql)
        if not val.valid:
            return {
                "status": "error",
                "error": f"SQL validation failed: {', '.join(val.errors)}",
                "validation": {"valid": False, "errors": val.errors},
            }

        res = await self.warehouse.execute_query(sql, max_rows=max_rows)
        return {
            "status": "success",
            "columns": res.get("columns", []),
            "rows": res.get("rows", []),
            "row_count": res.get("row_count", 0),
            "execution_time_ms": res.get("execution_time_ms", 0.0),
            "adapter": res.get("adapter", "LOCAL_DEMO"),
        }


class DescribeTableTool(BaseTool):
    name = "describe_warehouse_table"
    description = "Inspect table schema, columns, and data types in the analytical warehouse."
    target_system = "Snowflake"
    risk_level = "low"
    requires_approval = False

    parameters = {
        "type": "object",
        "properties": {
            "table_name": {
                "type": "string",
                "description": "Name of the table to describe (e.g., fact_sales, dim_product).",
            },
        },
        "required": ["table_name"],
    }

    def __init__(self, warehouse_client: WarehouseClient | None = None) -> None:
        super().__init__()
        self.warehouse = warehouse_client or get_warehouse_client()

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        table_name = kwargs.get("table_name", "").lower()
        schema = await self.warehouse.get_schema()
        if table_name in schema:
            return {
                "status": "success",
                "table_name": table_name,
                "columns": schema[table_name],
            }
        return {
            "status": "not_found",
            "table_name": table_name,
            "available_tables": list(schema.keys()),
        }
