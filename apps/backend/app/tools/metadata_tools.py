"""
Metadata & Semantic Tools
=========================
Tools for inspecting semantic definitions and data lineage.
"""
from __future__ import annotations

from typing import Any, Dict
from app.tools.base import BaseTool
from app.semantic.semantic_layer import get_semantic_layer, SemanticLayer


class ResolveMetricTool(BaseTool):
    name = "resolve_semantic_metric"
    description = "Resolve a business term into an authoritative certified metric formula and physical table mappings."
    target_system = "Semantic Layer"
    risk_level = "low"
    requires_approval = False

    parameters = {
        "type": "object",
        "properties": {
            "metric_name": {
                "type": "string",
                "description": "Business term or alias (e.g. net_sales, gross_revenue, dos).",
            },
        },
        "required": ["metric_name"],
    }

    def __init__(self, semantic_layer: SemanticLayer | None = None) -> None:
        super().__init__()
        self.semantic_layer = semantic_layer or get_semantic_layer()

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        m_name = kwargs.get("metric_name", "")
        meta = self.semantic_layer.resolve_metric(m_name)
        if not meta:
            return {
                "status": "not_found",
                "available_metrics": list(self.semantic_layer.catalogue.get("metrics", {}).keys()),
            }

        return {
            "status": "success",
            "metric": meta,
        }
