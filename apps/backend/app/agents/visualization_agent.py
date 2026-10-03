"""
Visualization Agent
===================
Responsible for constructing declarative chart specifications (Recharts-compatible).
Translates query results and intent into structured chart JSON specs.
"""
from __future__ import annotations

from typing import Any
import structlog

from app.agents.base import BaseAgent
from app.agents.types import AgentState, VisualizationSpec
from app.visualization.viz_builder import build_visualization

logger = structlog.get_logger(__name__)


class VisualizationAgent(BaseAgent[AgentState]):
    name = "visualization"
    version = "1.0.0"

    def validate_input(self, state: AgentState) -> None:
        pass

    async def process(self, state: AgentState) -> AgentState:
        q_res = state.get("query_result")
        intent = state.get("intent")

        if not q_res or not q_res.rows:
            state["visualization"] = None
            return state

        intent_dict = intent.model_dump() if intent else {}
        viz_dict = build_visualization(
            intent=intent_dict,
            rows=q_res.rows,
            columns=q_res.columns,
        )

        if viz_dict:
            state["visualization"] = VisualizationSpec(
                type=viz_dict.get("type", "bar"),
                title=viz_dict.get("title", "Query Results"),
                x=viz_dict.get("x"),
                y=viz_dict.get("y"),
                data=viz_dict.get("data", []),
                config=viz_dict.get("config", {}),
                columns=viz_dict.get("columns"),
            )
        else:
            state["visualization"] = None

        return state

    def summarize_execution(self, state: AgentState) -> str:
        v = state.get("visualization")
        if not v:
            return "Visualization: None (No tabular data to chart)"
        return f"Visualization: Generated {v.type.upper()} chart ('{v.title}')"
