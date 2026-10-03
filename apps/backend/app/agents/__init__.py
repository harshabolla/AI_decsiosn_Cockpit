"""
Agents package initialization.
Registers all 10 specialized enterprise agents into AgentRegistry.
"""
from __future__ import annotations

from app.agents.base import BaseAgent
from app.agents.registry import AgentRegistry, get_agent_registry
from app.agents.types import AgentState, IntentResult, SecurityResult
from app.agents.security_agent import SecurityAgent
from app.agents.intent_agent import IntentAgent
from app.agents.semantic_agent import SemanticAgent
from app.agents.analytics_agent import AnalyticsAgent
from app.agents.rag_agent import RAGAgent
from app.agents.guideline_agent import GuidelineAgent
from app.agents.operations_agent import OperationsAgent
from app.agents.reviewer_agent import ReviewerAgent
from app.agents.visualization_agent import VisualizationAgent
from app.agents.summary_agent import SummaryAgent
from app.agents.supervisor_agent import get_compiled_graph


def init_default_agents(registry: AgentRegistry | None = None) -> AgentRegistry:
    reg = registry or get_agent_registry()
    agents = [
        SecurityAgent(),
        IntentAgent(),
        SemanticAgent(),
        AnalyticsAgent(),
        RAGAgent(),
        GuidelineAgent(),
        OperationsAgent(),
        ReviewerAgent(),
        VisualizationAgent(),
        SummaryAgent(),
    ]
    for a in agents:
        reg.register(a)
    return reg


# Auto-initialize agents on import
init_default_agents()

__all__ = [
    "BaseAgent",
    "AgentRegistry",
    "get_agent_registry",
    "init_default_agents",
    "AgentState",
    "SecurityAgent",
    "IntentAgent",
    "SemanticAgent",
    "AnalyticsAgent",
    "RAGAgent",
    "GuidelineAgent",
    "OperationsAgent",
    "ReviewerAgent",
    "VisualizationAgent",
    "SummaryAgent",
    "get_compiled_graph",
]
