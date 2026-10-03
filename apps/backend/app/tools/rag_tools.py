"""
RAG Knowledge Tools
===================
Governed tools for searching enterprise documentation and retrieving policy citations.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
from app.tools.base import BaseTool
from app.rag.vector_store import get_knowledge_store, EnterpriseKnowledgeStore


class SearchKnowledgeBaseTool(BaseTool):
    name = "rag_search_knowledge_base"
    description = "Retrieve relevant policy sections, supply chain guidelines, and SOPs with metadata filters."
    target_system = "Enterprise Knowledge Store"
    risk_level = "low"
    requires_approval = False

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query to search documents for.",
            },
            "domain": {
                "type": "string",
                "enum": ["commercial", "supply_chain", "finance", "governance"],
                "description": "Optional domain filter.",
            },
            "product": {
                "type": "string",
                "description": "Optional product filter (e.g. Doliprane, Allegra).",
            },
            "top_k": {
                "type": "integer",
                "default": 3,
                "description": "Number of relevant chunks to retrieve.",
            },
        },
        "required": ["query"],
    }

    def __init__(self, store: Optional[EnterpriseKnowledgeStore] = None) -> None:
        super().__init__()
        self.store = store or get_knowledge_store()

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        query = kwargs.get("query", "")
        domain = kwargs.get("domain")
        product = kwargs.get("product")
        top_k = kwargs.get("top_k", 3)

        result = self.store.search(
            query=query,
            domain_filter=domain,
            product_filter=product,
            top_k=top_k,
        )

        return {
            "status": "success",
            "count": len(result.chunks),
            "chunks": [c.model_dump() for c in result.chunks],
            "conflict_detected": result.conflict_detected,
            "conflict_notes": result.conflict_notes,
        }
