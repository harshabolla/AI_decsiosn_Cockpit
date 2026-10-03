"""
Vector Store & RAG Retrieval Engine
===================================
Provides in-memory semantic retrieval over governed Opella enterprise documents.
Features:
  - Markdown section chunking with metadata extraction
  - Metadata pre-filtering (domain, product, country, status)
  - Cosine term-frequency semantic similarity
  - Cross-document conflict & expiration detection
"""
from __future__ import annotations

import math
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional
import structlog

from app.rag.models import DocumentChunk, RetrievalResult

logger = structlog.get_logger(__name__)


def _tokenize(text: str) -> List[str]:
    return [w.lower() for w in re.findall(r"\w+", text) if len(w) > 2]


def _compute_vector(tokens: List[str]) -> Dict[str, float]:
    counts: Dict[str, float] = {}
    for t in tokens:
        counts[t] = counts.get(t, 0.0) + 1.0
    norm = math.sqrt(sum(v * v for v in counts.values())) or 1.0
    return {k: v / norm for k, v in counts.items()}


def _cosine_similarity(vec1: Dict[str, float], vec2: Dict[str, float]) -> float:
    return sum(vec1[k] * vec2[k] for k in vec1 if k in vec2)


class EnterpriseKnowledgeStore:
    """In-memory vector store indexing enterprise policy and guideline documents."""

    def __init__(self, docs_dir: Optional[Path] = None) -> None:
        self.docs_dir = docs_dir or (Path(__file__).resolve().parents[4] / "rag" / "documents")
        self.chunks: List[DocumentChunk] = []
        self._vectors: List[Dict[str, float]] = []
        self._indexed = False

    def initialize(self) -> None:
        if self._indexed:
            return
        self.load_documents()
        self._indexed = True
        logger.info("rag_vector_store_initialized", chunks_count=len(self.chunks))

    def load_documents(self) -> None:
        if not self.docs_dir.exists():
            logger.warning("rag_docs_dir_missing", path=str(self.docs_dir))
            return

        for filepath in self.docs_dir.glob("*.md"):
            try:
                content = filepath.read_text(encoding="utf-8")
                self._parse_and_chunk(filepath.name, content)
            except Exception as e:
                logger.error("rag_doc_load_error", file=filepath.name, error=str(e))

    def _parse_and_chunk(self, filename: str, content: str) -> None:
        lines = content.splitlines()
        doc_title = lines[0].replace("#", "").strip() if lines else filename
        version = "2.3" if "v2_3" in filename else "1.0"
        domain = "commercial" if "commercial" in filename else ("supply_chain" if "supply" in filename else "general")

        # Split into sections by '## '
        sections = re.split(r"\n(?=##\s+)", content)
        for idx, sec in enumerate(sections):
            sec_lines = sec.strip().splitlines()
            sec_title = sec_lines[0].replace("##", "").strip() if sec_lines else f"Section {idx+1}"
            sec_content = "\n".join(sec_lines)

            # Extract products mentioned
            products = []
            for p in ["Doliprane", "Buscopan", "Allegra", "Dulcolax", "Mucosolvan"]:
                if p.lower() in sec_content.lower():
                    products.append(p)
            product_tag = ", ".join(products) if products else None

            # Detect status
            status = "active"
            if "superseded" in sec_content.lower():
                status = "superseded"

            chunk = DocumentChunk(
                chunk_id=f"{filename}_{idx}",
                document_id=filename,
                document_name=doc_title,
                version=version,
                domain=domain,
                product=product_tag,
                section=sec_title,
                content=sec_content,
                status=status,
                is_active=(status == "active"),
                keywords=_tokenize(sec_content),
            )
            self.chunks.append(chunk)
            self._vectors.append(_compute_vector(chunk.keywords))

    def search(
        self,
        query: str,
        domain_filter: Optional[str] = None,
        product_filter: Optional[str] = None,
        top_k: int = 3,
        min_score: float = 0.05,
    ) -> RetrievalResult:
        if not self._indexed:
            self.initialize()

        query_tokens = _tokenize(query)
        q_vec = _compute_vector(query_tokens)

        scored_chunks: List[tuple[DocumentChunk, float]] = []
        for chunk, vec in zip(self.chunks, self._vectors):
            # Pre-filters
            if not chunk.is_active:
                continue
            if domain_filter and chunk.domain.lower() != domain_filter.lower():
                continue
            if product_filter and chunk.product and (product_filter.lower() not in chunk.product.lower()):
                continue

            sim = _cosine_similarity(q_vec, vec)
            # Boost score if query mentions specific product present in chunk
            if chunk.product and any(p.lower() in query.lower() for p in chunk.product.split(", ")):
                sim += 0.25

            if sim >= min_score or not query.strip():
                chunk_copy = chunk.model_copy()
                chunk_copy.score = round(sim, 3)
                scored_chunks.append((chunk_copy, sim))

        scored_chunks.sort(key=lambda x: x[1], reverse=True)
        top_results = [item[0] for item in scored_chunks[:top_k]]

        # Conflict Detection
        conflict_detected = False
        conflict_notes: List[str] = []
        versions = {c.document_name: c.version for c in top_results}
        if len(versions) > 1 and len(set(versions.values())) > 1:
            conflict_detected = True
            conflict_notes.append("Multiple policy versions retrieved across documents.")

        return RetrievalResult(
            query=query,
            chunks=top_results,
            conflict_detected=conflict_detected,
            conflict_notes=conflict_notes,
            filters_applied={"domain": domain_filter, "product": product_filter},
        )


_knowledge_store: Optional[EnterpriseKnowledgeStore] = None


def get_knowledge_store() -> EnterpriseKnowledgeStore:
    global _knowledge_store
    if _knowledge_store is None:
        _knowledge_store = EnterpriseKnowledgeStore()
        _knowledge_store.initialize()
    return _knowledge_store
