"""
LangGraph Supervisor — Multi-Agent Orchestration
=================================================
Orchestrates the 10-node governed enterprise state graph:
  START
    ↓
  SecurityAgent
    ↓
  IntentAgent
    ↓
  Router ──(Analytics)──> Semantic ──> Analytics ──> Guideline ──┐
    │                                                            │
    ├──(RAG)───────────> RAG ────────────────────────> Guideline ─┤
    │                                                            │
    └──(Operations)────> Operations ─────────────────────────────┼──> Reviewer ──> Visualization ──> Summary ──> END
"""
from __future__ import annotations

from typing import Any
import structlog

from app.agents.types import AgentState
from app.agents.supervisor_agent import get_compiled_graph, build_supervisor_graph

logger = structlog.get_logger(__name__)

# Backward-compatibility alias
CockpitState = AgentState


def get_graph() -> Any:
    """Return compiled 10-node multi-agent LangGraph workflow."""
    return get_compiled_graph()


def build_graph() -> Any:
    return build_supervisor_graph()


__all__ = [
    "CockpitState",
    "AgentState",
    "get_graph",
    "build_graph",
]
