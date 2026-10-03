"""
Model Context Protocol (MCP) Client
===================================
Provides backend connectivity to MCP servers:
  - Snowflake MCP Server (warehouse queries, table lineage)
  - dbt MCP Server (model transformations, metric lineage)
  - ServiceNow MCP Server (incident management, approval requests)
Strictly enforces server-side validation and audit logging.
"""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

logger = structlog.get_logger(__name__)

# Ensure mcp root is importable
MCP_ROOT = Path(__file__).resolve().parents[4] / "mcp"
if str(MCP_ROOT) not in sys.path:
    sys.path.insert(0, str(MCP_ROOT))


class MCPClient:
    """Unified client connecting backend agents to MCP servers."""

    def __init__(self) -> None:
        self._servers: Dict[str, Any] = {}

    def _get_server_handler(self, server_name: str):
        server_key = server_name.lower()
        if server_key not in self._servers:
            if server_key == "snowflake":
                from snowflake_server.server import handle_tool_call, TOOLS
                self._servers[server_key] = {"handler": handle_tool_call, "tools": TOOLS}
            elif server_key == "dbt":
                from dbt_server.server import handle_tool_call, TOOLS
                self._servers[server_key] = {"handler": handle_tool_call, "tools": TOOLS}
            elif server_key == "servicenow":
                from servicenow_server.server import handle_tool_call, TOOLS
                self._servers[server_key] = {"handler": handle_tool_call, "tools": TOOLS}
            else:
                raise ValueError(f"Unknown MCP server: {server_name}")
        return self._servers[server_key]

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Execute a tool call on the specified MCP server."""
        logger.info("mcp_call_initiated", server=server_name, tool=tool_name)
        try:
            server = self._get_server_handler(server_name)
            handler = server["handler"]
            result = await handler(tool_name, arguments)
            logger.info("mcp_call_completed", server=server_name, tool=tool_name, status="success")
            return result
        except Exception as e:
            logger.error("mcp_call_failed", server=server_name, tool=tool_name, error=str(e))
            return {"error": f"MCP execution error: {str(e)}", "status": "failed"}

    def list_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        server = self._get_server_handler(server_name)
        return server.get("tools", [])


_mcp_client: Optional[MCPClient] = None


def get_mcp_client() -> MCPClient:
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
    return _mcp_client
