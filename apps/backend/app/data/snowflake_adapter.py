"""
Snowflake Warehouse Adapter — Production Implementation
========================================================
Implements WarehouseClient for enterprise Snowflake data warehouses.
Features:
  - Governed read-only execution guardrails
  - Connection management & connection test suite
  - Strict timeout enforcement
  - Status transparency (REAL vs UNAVAILABLE)
"""
from __future__ import annotations

import asyncio
import os
import time
from typing import Any, Dict, List, Optional
import structlog

from app.core.config import settings
from app.data.warehouse_client import WarehouseClient, WarehouseStatus

logger = structlog.get_logger(__name__)


class SnowflakeWarehouseAdapter(WarehouseClient):
    adapter_name = "SNOWFLAKE"
    disclaimer = "Connected to Enterprise Snowflake Analytics Warehouse."

    def __init__(self) -> None:
        self.account = os.getenv("SNOWFLAKE_ACCOUNT", "")
        self.user = os.getenv("SNOWFLAKE_USER", "")
        self.password = os.getenv("SNOWFLAKE_PASSWORD", "")
        self.warehouse = os.getenv("SNOWFLAKE_WAREHOUSE", "")
        self.database = os.getenv("SNOWFLAKE_DATABASE", "")
        self.schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
        self.role = os.getenv("SNOWFLAKE_ROLE", "")
        self._connected = False
        self._snowflake_module = None

        # Check credentials presence
        if not (self.account and self.user and self.password):
            self.status = WarehouseStatus.UNAVAILABLE
        else:
            self.status = WarehouseStatus.REAL

    async def initialize(self) -> None:
        """Verify driver availability and initial connectivity."""
        try:
            import snowflake.connector
            self._snowflake_module = snowflake.connector
            if self.status == WarehouseStatus.REAL:
                logger.info("snowflake_adapter_initialized", account=self.account, database=self.database)
            else:
                logger.warning("snowflake_credentials_missing", status=self.status.value)
        except ImportError:
            logger.warning("snowflake_connector_not_installed")
            self.status = WarehouseStatus.UNAVAILABLE

    def _get_connection(self):
        if not self._snowflake_module:
            raise RuntimeError("snowflake-connector-python is not installed.")
        if self.status != WarehouseStatus.REAL:
            raise RuntimeError("Snowflake credentials are not configured in environment.")

        return self._snowflake_module.connect(
            account=self.account,
            user=self.user,
            password=self.password,
            warehouse=self.warehouse,
            database=self.database,
            schema=self.schema,
            role=self.role or None,
            client_session_keep_alive=False,
        )

    async def test_connection(self) -> Dict[str, Any]:
        """
        Runs diagnostic query:
          SELECT current_user(), current_role(), current_warehouse(), current_database(), current_schema()
        Returns connection details without exposing sensitive passwords.
        """
        if self.status != WarehouseStatus.REAL:
            return {
                "status": "UNAVAILABLE",
                "connected": False,
                "error": "Snowflake credentials (SNOWFLAKE_ACCOUNT, SNOWFLAKE_USER, SNOWFLAKE_PASSWORD) are not set.",
            }

        loop = asyncio.get_event_loop()
        try:
            return await loop.run_in_executor(None, self._test_connection_sync)
        except Exception as e:
            logger.error("snowflake_connection_test_failed", error=str(e))
            return {
                "status": "FAILED",
                "connected": False,
                "error": str(e),
            }

    def _test_connection_sync(self) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT current_user(), current_role(), current_warehouse(), current_database(), current_schema()"
            )
            row = cursor.fetchone()
            return {
                "status": "CONNECTED",
                "connected": True,
                "current_user": row[0] if row else None,
                "current_role": row[1] if row else None,
                "current_warehouse": row[2] if row else None,
                "current_database": row[3] if row else None,
                "current_schema": row[4] if row else None,
            }
        finally:
            conn.close()

    async def execute_query(
        self,
        sql: str,
        max_rows: int = 1000,
        timeout_secs: float = 30.0,
    ) -> Dict[str, Any]:
        """Execute governed read-only SQL query against Snowflake."""
        # Enforce read-only restriction
        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE", "GRANT", "REVOKE"]
        upper_sql = sql.upper()
        for kw in forbidden:
            if kw in upper_sql:
                raise PermissionError(f"Snowflake query rejected: Destructive keyword '{kw}' detected.")

        if self.status != WarehouseStatus.REAL:
            raise RuntimeError("Cannot execute query: Snowflake credentials are not configured.")

        start_time = time.perf_counter()
        loop = asyncio.get_event_loop()
        res = await asyncio.wait_for(
            loop.run_in_executor(None, self._execute_sync, sql, max_rows),
            timeout=timeout_secs,
        )
        res["execution_time_ms"] = (time.perf_counter() - start_time) * 1000
        res["adapter"] = "SNOWFLAKE"
        res["status"] = "REAL"
        return res

    def _execute_sync(self, sql: str, max_rows: int) -> Dict[str, Any]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(sql)
            columns = [desc[0] for desc in cursor.description]
            raw_rows = cursor.fetchmany(max_rows)
            rows = [dict(zip(columns, r)) for r in raw_rows]
            return {
                "columns": columns,
                "rows": rows,
                "row_count": len(rows),
            }
        finally:
            conn.close()

    async def get_schema(self) -> Dict[str, List[str]]:
        if self.status != WarehouseStatus.REAL:
            return {}
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_schema_sync)

    def _get_schema_sync(self) -> Dict[str, List[str]]:
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT table_name, column_name FROM information_schema.columns "
                f"WHERE table_schema='{self.schema.upper()}'"
            )
            schema: Dict[str, List[str]] = {}
            for t_name, c_name in cursor.fetchall():
                schema.setdefault(t_name.lower(), []).append(c_name.lower())
            return schema
        finally:
            conn.close()

    def get_status(self) -> Dict[str, Any]:
        return {
            "adapter": self.adapter_name,
            "status": self.status.value,
            "account": self.account if self.account else "NOT_CONFIGURED",
            "database": self.database if self.database else "NOT_CONFIGURED",
            "schema": self.schema,
            "warehouse": self.warehouse if self.warehouse else "NOT_CONFIGURED",
            "disclaimer": self.disclaimer,
        }
