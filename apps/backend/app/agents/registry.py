"""
Agent Registry
==============
Centralized service locator & registry for all specialized agents.
Allows dependency injection and prevents scattering direct agent instantiations.
"""
from __future__ import annotations

from typing import Dict, List, Optional
import structlog
from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}

    def register(self, agent: BaseAgent) -> None:
        """Register an agent instance."""
        if agent.name in self._agents:
            logger.warning("agent_re_registered", name=agent.name)
        self._agents[agent.name] = agent
        logger.info("agent_registered", name=agent.name, version=agent.version)

    def get(self, name: str) -> BaseAgent:
        """Retrieve an agent by name. Raises KeyError if not found."""
        if name not in self._agents:
            raise KeyError(f"Agent '{name}' is not registered in AgentRegistry. Available: {list(self._agents.keys())}")
        return self._agents[name]

    def has(self, name: str) -> bool:
        return name in self._agents

    def list_agents(self) -> List[str]:
        return list(self._agents.keys())

    def clear(self) -> None:
        self._agents.clear()


# Global Singleton Registry
_global_registry: Optional[AgentRegistry] = None


def get_agent_registry() -> AgentRegistry:
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry()
    return _global_registry
