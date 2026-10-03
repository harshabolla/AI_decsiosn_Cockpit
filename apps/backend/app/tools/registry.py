"""
Tool Registry
=============
Centralized registry of governed tools.
Exposes tools to agents and MCP client wrappers.
"""
from __future__ import annotations

from typing import Dict, List, Optional
import structlog
from app.tools.base import BaseTool

logger = structlog.get_logger(__name__)


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        if tool.name in self._tools:
            logger.warning("tool_re_registered", name=tool.name)
        self._tools[tool.name] = tool
        logger.info("tool_registered", name=tool.name, system=tool.target_system)

    def get(self, name: str) -> BaseTool:
        if name not in self._tools:
            raise KeyError(f"Tool '{name}' not found. Available: {list(self._tools.keys())}")
        return self._tools[name]

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_tools(self) -> List[Dict[str, Any]]:
        return [tool.get_schema() for tool in self._tools.values()]

    def list_names(self) -> List[str]:
        return list(self._tools.keys())


_global_registry: Optional[ToolRegistry] = None


def get_tool_registry() -> ToolRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = ToolRegistry()
    return _global_registry
