"""
RAG Models & Metadata Schemas
=============================
Defines standard schema for document chunks, metadata, and retrieval outputs.
"""
from __future__ import annotations

from typing import List, Optional
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    document_name: str
    version: str = "1.0"
    domain: str  # commercial | supply_chain | finance | governance
    country: Optional[str] = None
    product: Optional[str] = None
    section: str = ""
    content: str
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    status: str = "active"  # active | expired | superseded
    is_active: bool = True
    keywords: List[str] = Field(default_factory=list)
    score: float = 1.0


class RetrievalResult(BaseModel):
    query: str
    chunks: List[DocumentChunk]
    conflict_detected: bool = False
    conflict_notes: List[str] = Field(default_factory=list)
    filters_applied: dict = Field(default_factory=dict)
