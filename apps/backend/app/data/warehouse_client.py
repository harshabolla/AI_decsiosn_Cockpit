"""
Warehouse Client Abstract Base Class
====================================
Defines the standard contract for analytical data warehouse adapters:
  - SnowflakeWarehouseAdapter (Production Snowflake)
  - DuckDBWarehouseAdapter (Local in-memory demonstration)

Enforces Liskov Substitution Principle (LSP): Application code, agents,
and tools interact only with WarehouseClient.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List


class WarehouseStatus(str, Enum):
    REAL = "REAL"
    DEMO = "DEMO"
    UNAVAILABLE = "UNAVAILABLE"


class WarehouseClient(ABC):
    """Abstract Base Class for all data warehouse adapters."""

    adapter_name: str = "base"
    status: WarehouseStatus = WarehouseStatus.UNAVAILABLE
    disclaimer: str = ""

    @abstractmethod
    async def initialize(self) -> None:
        """Initialize connection pool or in-memory database."""
        ...

    @abstractmethod
    async def execute_query(
        self,
        sql: str,
        max_rows: int = 1000,
        timeout_secs: float = 30.0,
    ) -> Dict[str, Any]:
        """
        Execute a governed read-only SQL query.
        Returns:
            {
                "columns": list[str],
                "rows": list[dict[str, Any]],
                "row_count": int,
                "execution_time_ms": float,
                "adapter": str,
                "status": str (REAL | DEMO)
            }
        """
        ...

    @abstractmethod
    async def get_schema(self) -> Dict[str, List[str]]:
        """Return mapping of table_name -> list[column_name]."""
        ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]:
        """Return connectivity metadata, provider name, and live status."""
        ...
