"""
Governed Tools Package
======================
Registers all enterprise tools (Snowflake, dbt, ServiceNow, RAG, Semantic).
"""
from __future__ import annotations

from app.tools.base import BaseTool
from app.tools.registry import ToolRegistry, get_tool_registry
from app.tools.snowflake_tools import ExecuteReadOnlyQueryTool, DescribeTableTool
from app.tools.dbt_tools import GetModelLineageTool
from app.tools.servicenow_tools import SearchIncidentsTool, CreateIncidentTool, RequestApprovalTool
from app.tools.rag_tools import SearchKnowledgeBaseTool
from app.tools.metadata_tools import ResolveMetricTool


def init_default_tools(registry: ToolRegistry | None = None) -> ToolRegistry:
    reg = registry or get_tool_registry()
    tools = [
        ExecuteReadOnlyQueryTool(),
        DescribeTableTool(),
        GetModelLineageTool(),
        SearchIncidentsTool(),
        CreateIncidentTool(),
        RequestApprovalTool(),
        SearchKnowledgeBaseTool(),
        ResolveMetricTool(),
    ]
    for t in tools:
        reg.register(t)
    return reg


__all__ = [
    "BaseTool",
    "ToolRegistry",
    "get_tool_registry",
    "init_default_tools",
    "ExecuteReadOnlyQueryTool",
    "DescribeTableTool",
    "GetModelLineageTool",
    "SearchIncidentsTool",
    "CreateIncidentTool",
    "RequestApprovalTool",
    "SearchKnowledgeBaseTool",
    "ResolveMetricTool",
]
