"""
RAG Knowledge Agent
===================
Responsible exclusively for retrieving governed enterprise policies, SOPs,
and guidelines. Populates retrieved_documents and evidence in state.
"""
from __future__ import annotations

from typing import Any
import structlog

from app.agents.base import BaseAgent
from app.agents.types import (
    AgentState, RetrievedDocument, Evidence
)
from app.rag.vector_store import get_knowledge_store, EnterpriseKnowledgeStore

logger = structlog.get_logger(__name__)


class RAGAgent(BaseAgent[AgentState]):
    name = "rag"
    version = "1.0.0"

    def __init__(self, knowledge_store: EnterpriseKnowledgeStore | None = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.store = knowledge_store or get_knowledge_store()

    def validate_input(self, state: AgentState) -> None:
        if "user_input" not in state and "normalized_input" not in state:
            raise ValueError("RAGAgent requires 'user_input' or 'normalized_input'.")

    async def process(self, state: AgentState) -> AgentState:
        query = state.get("normalized_input") or state.get("user_input", "")
        intent = state.get("intent")

        domain = None
        product = None
        if intent:
            if "supply" in query.lower() or "inventory" in query.lower() or "dos" in query.lower():
                domain = "supply_chain"
            elif "discount" in query.lower() or "pricing" in query.lower() or "margin" in query.lower():
                domain = "commercial"
            if intent.entities:
                for ent in intent.entities:
                    if ent.entity_type == "product":
                        product = ent.name
                        break

        res = self.store.search(
            query=query,
            domain_filter=domain,
            product_filter=product,
            top_k=3,
        )

        retrieved: list[RetrievedDocument] = []
        evidence_list = state.get("evidence") or []

        for c in res.chunks:
            doc = RetrievedDocument(
                document_id=c.document_id,
                document_name=c.document_name,
                version=c.version,
                domain=c.domain,
                product=c.product,
                section=c.section,
                content=c.content,
                score=c.score,
                is_active=c.is_active,
            )
            retrieved.append(doc)
            evidence_list.append(
                Evidence(
                    source_type="rag",
                    source_name=f"{doc.document_name} ({doc.version})",
                    summary=f"Section: {doc.section}",
                    citation=f"Document ID: {doc.document_id} [score={doc.score}]",
                )
            )

        state["retrieved_documents"] = retrieved
        state["evidence"] = evidence_list

        if res.conflict_detected:
            state["warnings"] = state.get("warnings", []) + [
                f"Policy Conflict: {'; '.join(res.conflict_notes)}"
            ]

        return state

    def summarize_execution(self, state: AgentState) -> str:
        docs = state.get("retrieved_documents", [])
        return f"RAG Agent: Retrieved {len(docs)} policy sections."
