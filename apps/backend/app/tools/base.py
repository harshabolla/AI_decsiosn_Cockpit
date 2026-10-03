"""
Base Tool Interface
===================
Every controlled capability available to agents must implement BaseTool.
Tools determine HOW operations are performed.
Strict parameter validation ensures the LLM never executes arbitrary code.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict
import structlog

logger = structlog.get_logger(__name__)


class BaseTool(ABC):
    """Abstract Base Class for all governed tools."""

    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema specification
    requires_approval: bool = False
    risk_level: str = "low"  # low | medium | high | critical
    target_system: str = "Local"

    def __init__(self) -> None:
        self._logger = structlog.get_logger(self.__class__.__name__)

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        """
        Execute the tool with validated arguments.
        Must return structured JSON-serializable dict.
        """
        ...

    def get_schema(self) -> Dict[str, Any]:
        """Return MCP/OpenAI-compatible tool definition."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
            "requires_approval": self.requires_approval,
            "risk_level": self.risk_level,
            "target_system": self.target_system,
        }
