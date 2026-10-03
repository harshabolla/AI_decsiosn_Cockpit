"""
Unit tests for Governed Tools and Model Context Protocol (MCP) Client.
"""
import pytest
from app.tools.registry import ToolRegistry, get_tool_registry
from app.tools import init_default_tools
from app.tools.snowflake_tools import ExecuteReadOnlyQueryTool, DescribeTableTool
from app.tools.servicenow_tools import SearchIncidentsTool, CreateIncidentTool, RequestApprovalTool
from app.tools.rag_tools import SearchKnowledgeBaseTool
from app.tools.dbt_tools import GetModelLineageTool
from app.mcp.client import MCPClient
from app.data.local_warehouse import LocalWarehouseAdapter


@pytest.fixture(autouse=True)
async def init_warehouse():
    adapter = LocalWarehouseAdapter.get_instance()
    await adapter.initialize()


def test_tool_registry():
    reg = ToolRegistry()
    tool = SearchIncidentsTool()
    reg.register(tool)

    assert reg.has("servicenow_search_incidents")
    assert reg.get("servicenow_search_incidents") == tool
    assert len(reg.list_tools()) == 1


@pytest.mark.asyncio
async def test_snowflake_query_tool_read_only():
    tool = ExecuteReadOnlyQueryTool()
    res = await tool.execute(sql="SELECT * FROM dim_product LIMIT 3;")
    assert res["status"] == "success"
    assert res["row_count"] > 0
    assert len(res["rows"]) <= 3


@pytest.mark.asyncio
async def test_snowflake_query_tool_blocks_dml():
    tool = ExecuteReadOnlyQueryTool()
    res = await tool.execute(sql="DROP TABLE fact_sales;")
    assert res["status"] == "error"
    assert "validation failed" in res["error"].lower()


@pytest.mark.asyncio
async def test_servicenow_tools():
    search_tool = SearchIncidentsTool()
    s_res = await search_tool.execute(query="Doliprane")
    assert s_res["status"] == "success"

    create_tool = CreateIncidentTool()
    assert create_tool.requires_approval is True
    c_res = await create_tool.execute(short_description="Test alert", urgency="2 - Medium")
    assert c_res["status"] == "created"
    assert "ticket_id" in c_res


@pytest.mark.asyncio
async def test_rag_knowledge_tool():
    tool = SearchKnowledgeBaseTool()
    res = await tool.execute(query="commercial discounting cap")
    assert res["status"] == "success"
    assert res["count"] > 0


@pytest.mark.asyncio
async def test_dbt_lineage_tool():
    tool = GetModelLineageTool()
    res = await tool.execute(model_name="fct_sales_monthly")
    assert res["status"] == "success"
    assert "stg_sales" in res["upstream"]


@pytest.mark.asyncio
async def test_mcp_client_integration():
    mcp = MCPClient()

    # Snowflake MCP
    sf_res = await mcp.call_tool("snowflake", "snowflake_query", {"sql": "SELECT 1"})
    assert sf_res["status"] == "success"

    # dbt MCP
    dbt_res = await mcp.call_tool("dbt", "dbt_get_metric_lineage", {"metric_name": "net_sales"})
    assert "fct_sales_monthly" in dbt_res.get("model", "")

    # ServiceNow MCP
    sn_res = await mcp.call_tool("servicenow", "servicenow_create_incident", {"short_description": "MCP Alert", "urgency": "1 - High"})
    assert sn_res["status"] == "created"
