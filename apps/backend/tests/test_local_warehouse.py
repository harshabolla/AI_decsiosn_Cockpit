import pytest
from app.data.local_warehouse import LocalWarehouseAdapter


@pytest.mark.asyncio
async def test_local_warehouse_init_and_query():
    adapter = LocalWarehouseAdapter.get_instance()
    await adapter.initialize()

    schema = await adapter.get_schema()
    assert "fact_sales" in schema
    assert "dim_product" in schema

    result = await adapter.execute_query("SELECT COUNT(*) AS total_rows FROM fact_sales")
    assert result["row_count"] == 1
    assert result["columns"] == ["total_rows"]
    assert result["rows"][0]["total_rows"] > 0
    assert result["adapter"] == "LOCAL_DEMO"
