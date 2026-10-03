"""
Supervisor Agent & LangGraph Orchestrator
=========================================
Coordinates multi-agent state execution.
Routes requests conditionally based on user intent and security boundaries:
  - SecurityAgent
  - IntentAgent
  - SemanticAgent
  - AnalyticsAgent
  - RAGAgent
  - GuidelineAgent
  - OperationsAgent
  - ReviewerAgent
  - VisualizationAgent
  - SummaryAgent
"""
from __future__ import annotations

from typing import Any, Dict
import structlog
from langgraph.graph import StateGraph, END

from app.agents.types import AgentState, IntentType
from app.agents.registry import get_agent_registry, AgentRegistry
from app.agents.base import BaseAgent

logger = structlog.get_logger(__name__)


# ── Generic Node Runner (Calls Agent via Registry) ────────────────────────────

def _create_node_func(agent_name: str):
    async def node_func(state: AgentState) -> AgentState:
        reg = get_agent_registry()
        agent = reg.get(agent_name)
        return await agent.execute(state)
    return node_func


# ── Conditional Routing Functions ─────────────────────────────────────────────

def route_after_security(state: AgentState) -> str:
    sec = state.get("security_result")
    if sec and not sec.allowed:
        return "blocked"
    return "continue"


def route_after_intent(state: AgentState) -> str:
    intent = state.get("intent")
    if not intent:
        return "analytics"

    if intent.intent_type in (IntentType.INJECTION_ATTEMPT, IntentType.OFF_TOPIC, IntentType.CLARIFICATION_NEEDED):
        return "skip_to_summary"

    if intent.intent_type == IntentType.RAG:
        return "rag_path"

    if intent.intent_type == IntentType.OPERATIONS:
        return "operations_path"

    # Default: Analytics (or hybrid)
    return "analytics_path"


def build_supervisor_graph() -> Any:
    """Build the 10-node governed LangGraph multi-agent state graph."""
    graph = StateGraph(AgentState)

    # Add all 10 specialized agent nodes
    graph.add_node("security", _create_node_func("security"))
    graph.add_node("intent_agent", _create_node_func("intent"))
    graph.add_node("semantic", _create_node_func("semantic"))
    graph.add_node("analytics", _create_node_func("analytics"))
    graph.add_node("rag", _create_node_func("rag"))
    graph.add_node("guideline", _create_node_func("guideline"))
    graph.add_node("operations", _create_node_func("operations"))
    graph.add_node("reviewer", _create_node_func("reviewer"))
    graph.add_node("visualization_agent", _create_node_func("visualization"))
    graph.add_node("summary", _create_node_func("summary"))

    # Entry point
    graph.set_entry_point("security")

    # Security routing
    graph.add_conditional_edges(
        "security",
        route_after_security,
        {
            "blocked": "summary",
            "continue": "intent_agent",
        },
    )

    # Intent routing
    graph.add_conditional_edges(
        "intent_agent",
        route_after_intent,
        {
            "skip_to_summary": "summary",
            "analytics_path": "semantic",
            "rag_path": "rag",
            "operations_path": "operations",
        },
    )

    # Analytics path -> Semantic -> Analytics -> Guideline
    graph.add_edge("semantic", "analytics")
    graph.add_edge("analytics", "guideline")

    # RAG path -> RAG -> Guideline
    graph.add_edge("rag", "guideline")

    # Operations path -> Operations -> Reviewer
    graph.add_edge("operations", "reviewer")

    # Guideline -> Operations (checks if rules require operational incident/action)
    graph.add_edge("guideline", "operations")

    # Reviewer -> Visualization -> Summary -> END
    graph.add_edge("reviewer", "visualization_agent")
    graph.add_edge("visualization_agent", "summary")
    graph.add_edge("summary", END)

    return graph.compile()


_compiled_graph: Any = None


def get_compiled_graph() -> Any:
    global _compiled_graph
    if _compiled_graph is None:
        _compiled_graph = build_supervisor_graph()
    return _compiled_graph
