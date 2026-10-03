"""
Semantic Agent
==============
Responsible exclusively for resolving business terms into authoritative
semantic definitions, metric formulas, and dimension join paths.
Never generates SQL or connects directly to databases.
"""
from __future__ import annotations

from typing import Any
import structlog

from app.agents.base import BaseAgent
from app.agents.types import AgentState, SemanticContext
from app.semantic.semantic_layer import get_semantic_layer, SemanticLayer

logger = structlog.get_logger(__name__)


class SemanticAgent(BaseAgent[AgentState]):
    name = "semantic"
    version = "1.0.0"

    def __init__(self, semantic_layer: SemanticLayer | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.semantic_layer = semantic_layer or get_semantic_layer()

    def validate_input(self, state: AgentState) -> None:
        if "intent" not in state or not state["intent"]:
            raise ValueError("SemanticAgent requires 'intent' in state.")

    async def process(self, state: AgentState) -> AgentState:
        intent = state["intent"]
        metrics_to_resolve = intent.metrics or ["net_sales"]
        dimensions_to_resolve = intent.dimensions or ["product"]

        resolved_metrics: list[str] = []
        metric_formulas: dict[str, str] = {}
        tables_involved: set[str] = set()

        for m in metrics_to_resolve:
            meta = self.semantic_layer.resolve_metric(m)
            if meta:
                canonical = meta["name"]
                # Include both the original key and canonical name for downstream compatibility
                if m not in resolved_metrics:
                    resolved_metrics.append(m)
                if canonical not in resolved_metrics:
                    resolved_metrics.append(canonical)
                metric_formulas[canonical] = meta["formula"]
                metric_formulas[m] = meta["formula"]  # alias
                for pc in meta.get("physical_columns", []):
                    tables_involved.add(pc["table"])
            else:
                # Unresolved: pass through as-is
                if m not in resolved_metrics:
                    resolved_metrics.append(m)

        resolved_dimensions: list[str] = []
        join_conditions: list[str] = []
        for d in dimensions_to_resolve:
            dim = self.semantic_layer.resolve_dimension(d)
            if dim:
                resolved_dimensions.append(dim["name"])
                tables_involved.add(dim["physical_table"])
                if dim.get("join_on"):
                    join_conditions.append(dim["join_on"])

        schema_context = self.semantic_layer.get_schema_context(
            metrics_to_resolve, dimensions_to_resolve
        )

        state["semantic_context"] = SemanticContext(
            resolved_metrics=resolved_metrics,
            resolved_dimensions=resolved_dimensions,
            schema_context=schema_context,
            tables_involved=sorted(list(tables_involved)),
            join_conditions=join_conditions,
            metric_formulas=metric_formulas,
        )
        return state

    def summarize_execution(self, state: AgentState) -> str:
        sc = state.get("semantic_context")
        if not sc:
            return "Semantic Resolver: No context generated."
        return f"Semantic: Metrics={sc.resolved_metrics} | Tables={sc.tables_involved}"
