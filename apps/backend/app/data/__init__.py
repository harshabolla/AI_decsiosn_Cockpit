"""
Data warehouse package.
Provides factory function get_warehouse_client() adhering to Dependency Inversion.
"""
from __future__ import annotations

from typing import Optional
from app.core.config import settings
from app.data.warehouse_client import WarehouseClient, WarehouseStatus
from app.data.local_warehouse import LocalWarehouseAdapter
from app.data.snowflake_adapter import SnowflakeWarehouseAdapter

_client_instance: Optional[WarehouseClient] = None


def get_warehouse_client() -> WarehouseClient:
    """Return configured warehouse client (Snowflake or DuckDB Local)."""
    global _client_instance
    if _client_instance is None:
        adapter_type = settings.WAREHOUSE_ADAPTER.lower()
        if adapter_type == "snowflake":
            _client_instance = SnowflakeWarehouseAdapter()
        else:
            _client_instance = LocalWarehouseAdapter.get_instance()
    return _client_instance


__all__ = [
    "WarehouseClient",
    "WarehouseStatus",
    "LocalWarehouseAdapter",
    "SnowflakeWarehouseAdapter",
    "get_warehouse_client",
]
