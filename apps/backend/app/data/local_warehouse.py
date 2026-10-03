"""
Local Warehouse Adapter — DEMO / LOCAL ADAPTER
=============================================
⚠  This adapter uses DuckDB with synthetic demo data.
   It is NOT connected to a real Snowflake instance.
   The UI clearly marks all results with "DEMO / LOCAL ADAPTER".

   To connect to a real Snowflake instance, set:
     WAREHOUSE_ADAPTER=snowflake
   in your .env and provide Snowflake credentials.
"""
from __future__ import annotations

import asyncio
import time
from typing import Any

import duckdb
import pandas as pd
import structlog
from app.data.warehouse_client import WarehouseClient, WarehouseStatus

logger = structlog.get_logger(__name__)

# ── Synthetic Demo Data ───────────────────────────────────────────────────────
# Clearly marked as DEMO DATA — not actual Opella production data.

DEMO_PRODUCTS = ["Allegra", "Buscopan", "Doliprane", "Dulcolax", "Mucosolvan"]
DEMO_REGIONS = ["India", "France", "Germany", "UK"]
DEMO_CHANNELS = ["Retail", "Hospital", "Online", "Wholesale"]


def _build_demo_sql() -> str:
    """Return DML that seeds in-memory DuckDB with demo analytics data."""
    return """
-- ============================================================
-- DEMO DATA — Synthetic, not actual Opella production data
-- ============================================================

CREATE TABLE IF NOT EXISTS dim_product (
    product_key INTEGER PRIMARY KEY,
    product_name VARCHAR,
    category VARCHAR,
    launch_year INTEGER
);

CREATE TABLE IF NOT EXISTS dim_region (
    region_key INTEGER PRIMARY KEY,
    region_name VARCHAR,
    country_code VARCHAR
);

CREATE TABLE IF NOT EXISTS dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE,
    year INTEGER,
    month INTEGER,
    month_name VARCHAR,
    quarter INTEGER
);

CREATE TABLE IF NOT EXISTS fact_sales (
    sale_id INTEGER PRIMARY KEY,
    date_key INTEGER,
    product_key INTEGER,
    region_key INTEGER,
    channel VARCHAR,
    units_sold INTEGER,
    gross_revenue DOUBLE,
    discounts DOUBLE,
    net_sales DOUBLE
);

CREATE TABLE IF NOT EXISTS fact_inventory (
    inventory_id INTEGER PRIMARY KEY,
    date_key INTEGER,
    product_key INTEGER,
    region_key INTEGER,
    stock_on_hand INTEGER,
    days_of_supply DOUBLE,
    reorder_point INTEGER,
    stockout_flag BOOLEAN
);

INSERT OR IGNORE INTO dim_product VALUES
    (1, 'Allegra',    'Antihistamine', 2005),
    (2, 'Buscopan',   'Antispasmodic',  1952),
    (3, 'Doliprane',  'Analgesic',     1963),
    (4, 'Dulcolax',   'Laxative',       1954),
    (5, 'Mucosolvan', 'Expectorant',   1963);

INSERT OR IGNORE INTO dim_region VALUES
    (1, 'India',   'IN'),
    (2, 'France',  'FR'),
    (3, 'Germany', 'DE'),
    (4, 'UK',      'GB');

INSERT OR IGNORE INTO dim_date VALUES
    (202401, '2024-01-15', 2024, 1,  'January',   1),
    (202402, '2024-02-15', 2024, 2,  'February',  1),
    (202403, '2024-03-15', 2024, 3,  'March',     1),
    (202404, '2024-04-15', 2024, 4,  'April',     2),
    (202405, '2024-05-15', 2024, 5,  'May',       2),
    (202406, '2024-06-15', 2024, 6,  'June',      2),
    (202407, '2024-07-15', 2024, 7,  'July',      3),
    (202408, '2024-08-15', 2024, 8,  'August',    3),
    (202409, '2024-09-15', 2024, 9,  'September', 3),
    (202410, '2024-10-15', 2024, 10, 'October',   4),
    (202411, '2024-11-15', 2024, 11, 'November',  4),
    (202412, '2024-12-15', 2024, 12, 'December',  4);

INSERT OR IGNORE INTO fact_sales VALUES
-- India / Allegra
(1001,202401,1,1,'Retail',  1200,180000,9000,171000),
(1002,202402,1,1,'Retail',  1150,172500,8625,163875),
(1003,202403,1,1,'Retail',  1300,195000,9750,185250),
(1004,202404,1,1,'Retail',  1250,187500,9375,178125),
(1005,202405,1,1,'Retail',  1400,210000,10500,199500),
(1006,202406,1,1,'Retail',  1380,207000,10350,196650),
-- India / Buscopan
(1011,202401,2,1,'Hospital',900,135000,6750,128250),
(1012,202402,2,1,'Hospital',850,127500,6375,121125),
(1013,202403,2,1,'Hospital',950,142500,7125,135375),
(1014,202404,2,1,'Hospital',800,120000,6000,114000),
(1015,202405,2,1,'Hospital',750,112500,5625,106875),
(1016,202406,2,1,'Hospital',600,90000,4500,85500),  -- declining
-- India / Doliprane
(1021,202401,3,1,'Retail',  2000,300000,15000,285000),
(1022,202402,3,1,'Retail',  2100,315000,15750,299250),
(1023,202403,3,1,'Retail',  2200,330000,16500,313500),
(1024,202404,3,1,'Retail',  1800,270000,13500,256500),
(1025,202405,3,1,'Retail',  1500,225000,11250,213750),
(1026,202406,3,1,'Retail',  1200,180000,9000,171000),  -- significant decline
-- India / Dulcolax
(1031,202401,4,1,'Wholesale',600,54000,2700,51300),
(1032,202402,4,1,'Wholesale',620,55800,2790,53010),
(1033,202403,4,1,'Wholesale',650,58500,2925,55575),
(1034,202404,4,1,'Wholesale',640,57600,2880,54720),
(1035,202405,4,1,'Wholesale',610,54900,2745,52155),
(1036,202406,4,1,'Wholesale',580,52200,2610,49590),
-- India / Mucosolvan
(1041,202401,5,1,'Online',  400,60000,3000,57000),
(1042,202402,5,1,'Online',  420,63000,3150,59850),
(1043,202403,5,1,'Online',  450,67500,3375,64125),
(1044,202404,5,1,'Online',  430,64500,3225,61275),
(1045,202405,5,1,'Online',  410,61500,3075,58425),
(1046,202406,5,1,'Online',  390,58500,2925,55575),
-- France / Doliprane
(2021,202401,3,2,'Retail',  5000,750000,37500,712500),
(2022,202402,3,2,'Retail',  5200,780000,39000,741000),
(2023,202403,3,2,'Retail',  5400,810000,40500,769500),
(2024,202404,3,2,'Retail',  5100,765000,38250,726750),
(2025,202405,3,2,'Retail',  5300,795000,39750,755250),
(2026,202406,3,2,'Retail',  5500,825000,41250,783750),
-- Germany / Buscopan
(3012,202401,2,3,'Hospital',1200,180000,9000,171000),
(3013,202402,2,3,'Hospital',1250,187500,9375,178125),
(3014,202403,2,3,'Hospital',1300,195000,9750,185250),
(3015,202404,2,3,'Hospital',1280,192000,9600,182400),
(3016,202405,2,3,'Hospital',1260,189000,9450,179550),
(3017,202406,2,3,'Hospital',1240,186000,9300,176700),
-- UK / Allegra
(4001,202401,1,4,'Retail',  800,120000,6000,114000),
(4002,202402,1,4,'Retail',  820,123000,6150,116850),
(4003,202403,1,4,'Retail',  850,127500,6375,121125),
(4004,202404,1,4,'Retail',  830,124500,6225,118275),
(4005,202405,1,4,'Retail',  810,121500,6075,115425),
(4006,202406,1,4,'Retail',  790,118500,5925,112575);

INSERT OR IGNORE INTO fact_inventory VALUES
-- India / Doliprane — supply issue (low stock)
(5001,202404,3,1,45,3.5,60,false),
(5002,202405,3,1,20,1.5,60,true),
(5003,202406,3,1,15,1.1,60,true),
-- India / Buscopan
(5011,202404,2,1,80,5.2,60,false),
(5012,202405,2,1,50,3.3,60,false),
(5013,202406,2,1,35,2.3,60,false),
-- Other regions (healthy)
(5021,202406,3,2,400,18.0,60,false),
(5022,202406,2,3,300,15.0,60,false),
(5023,202406,1,4,200,12.0,60,false);
"""


class LocalWarehouseAdapter(WarehouseClient):
    """
    Local DuckDB adapter for development and demo.
    ⚠ DEMO / LOCAL ADAPTER — not Snowflake.
    """

    adapter_name = "DUCKDB_DEMO"
    status = WarehouseStatus.DEMO
    disclaimer = "⚠ DEMO / LOCAL ADAPTER — results are synthetic demo data, not real Snowflake."
    _instance: "LocalWarehouseAdapter | None" = None
    ADAPTER_NOTE = "⚠ DEMO / LOCAL ADAPTER — results are synthetic demo data, not real Snowflake."

    def __init__(self) -> None:
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "LocalWarehouseAdapter":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def initialize(self) -> None:
        if self._initialized:
            return
        logger.info("local_warehouse_init", adapter="DuckDB (DEMO)")
        self._conn = duckdb.connect(database=":memory:")
        self._conn.execute(_build_demo_sql())
        self._initialized = True
        logger.info("local_warehouse_ready", adapter="DuckDB (DEMO)")

    def _ensure_ready(self) -> None:
        if not self._initialized or self._conn is None:
            raise RuntimeError("LocalWarehouseAdapter not initialized. Call initialize() first.")

    async def get_schema(self) -> dict[str, list[str]]:
        """Return table → columns mapping for prompt construction."""
        self._ensure_ready()
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._get_schema_sync)

    def _get_schema_sync(self) -> dict[str, list[str]]:
        tables = self._conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='main'"
        ).fetchall()
        schema: dict[str, list[str]] = {}
        for (table,) in tables:
            cols = self._conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name='{table}'"
            ).fetchall()
            schema[table] = [c[0] for c in cols]
        return schema

    async def execute_query(
        self,
        sql: str,
        max_rows: int = 1000,
        timeout_secs: float = 30.0,
    ) -> dict[str, Any]:
        """
        Execute a read-only SQL query.
        Returns: {columns, rows, row_count, execution_time_ms}
        """
        self._ensure_ready()
        start = time.perf_counter()
        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(None, self._execute_sync, sql, max_rows),
            timeout=timeout_secs,
        )
        result["execution_time_ms"] = (time.perf_counter() - start) * 1000
        result["adapter"] = "LOCAL_DEMO"
        return result

    def _execute_sync(self, sql: str, max_rows: int) -> dict[str, Any]:
        df: pd.DataFrame = self._conn.execute(sql).df()
        if len(df) > max_rows:
            df = df.head(max_rows)
        return {
            "columns": df.columns.tolist(),
            "rows": df.to_dict(orient="records"),
            "row_count": len(df),
        }

    def get_status(self) -> dict[str, Any]:
        return {
            "adapter": self.adapter_name,
            "status": self.status.value,
            "connected": self._initialized,
            "disclaimer": self.disclaimer,
        }
