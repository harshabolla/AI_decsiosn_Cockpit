"""
Conversation Memory Models
==========================
Data models for tracking multi-turn conversation context, session states, and execution summaries.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConversationTurn(BaseModel):
    turn_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    user_input: str
    assistant_answer: str
    intent_type: Optional[str] = None
    kpis: List[Dict[str, Any]] = Field(default_factory=list)
    sql_executed: Optional[str] = None
    tables_referenced: List[str] = Field(default_factory=list)
    retrieved_doc_ids: List[str] = Field(default_factory=list)
    latency_ms: float = 0.0


class SessionMemory(BaseModel):
    session_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_active: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    turns: List[ConversationTurn] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def turn_count(self) -> int:
        return len(self.turns)
