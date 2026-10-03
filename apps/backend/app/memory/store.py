"""
Conversation Memory Store — Session State & Context Management
==============================================================
Thread-safe in-memory session manager with TTL pruning and sliding window retrieval.
Enables multi-turn contextual reasoning across agent workflows.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import structlog

from app.memory.models import ConversationTurn, SessionMemory

logger = structlog.get_logger(__name__)


class ConversationMemoryStore:
    """In-memory store managing active chat sessions and turn history."""

    def __init__(self, max_turns_per_session: int = 20, ttl_hours: int = 24) -> None:
        self.max_turns_per_session = max_turns_per_session
        self.ttl = timedelta(hours=ttl_hours)
        self._sessions: Dict[str, SessionMemory] = {}
        self._lock = asyncio.Lock()

    async def get_or_create_session(self, session_id: str, metadata: Optional[Dict[str, Any]] = None) -> SessionMemory:
        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory(
                    session_id=session_id,
                    metadata=metadata or {},
                )
            else:
                self._sessions[session_id].last_active = datetime.now(timezone.utc)
            return self._sessions[session_id]

    async def add_turn(
        self,
        session_id: str,
        user_input: str,
        assistant_answer: str,
        intent_type: Optional[str] = None,
        kpis: Optional[List[Dict[str, Any]]] = None,
        sql_executed: Optional[str] = None,
        tables_referenced: Optional[List[str]] = None,
        retrieved_doc_ids: Optional[List[str]] = None,
        latency_ms: float = 0.0,
    ) -> ConversationTurn:
        turn = ConversationTurn(
            turn_id=str(uuid.uuid4()),
            user_input=user_input,
            assistant_answer=assistant_answer,
            intent_type=intent_type,
            kpis=kpis or [],
            sql_executed=sql_executed,
            tables_referenced=tables_referenced or [],
            retrieved_doc_ids=retrieved_doc_ids or [],
            latency_ms=latency_ms,
        )

        async with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = SessionMemory(session_id=session_id)

            session = self._sessions[session_id]
            session.turns.append(turn)
            session.last_active = datetime.now(timezone.utc)

            # Enforce max turns sliding window
            if len(session.turns) > self.max_turns_per_session:
                session.turns = session.turns[-self.max_turns_per_session:]

        logger.info("conversation_memory_turn_added", session_id=session_id, turn_id=turn.turn_id)
        return turn

    async def get_context_turns(self, session_id: str, limit: int = 5) -> List[ConversationTurn]:
        """Retrieve recent conversation turns for context injection into LLM prompts."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session or not session.turns:
                return []
            return session.turns[-limit:]

    async def get_session(self, session_id: str) -> Optional[SessionMemory]:
        async with self._lock:
            return self._sessions.get(session_id)

    async def list_sessions(self) -> List[Dict[str, Any]]:
        async with self._lock:
            return [
                {
                    "session_id": s.session_id,
                    "created_at": s.created_at.isoformat(),
                    "last_active": s.last_active.isoformat(),
                    "turn_count": len(s.turns),
                }
                for s in self._sessions.values()
            ]

    async def clear_session(self, session_id: str) -> bool:
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    async def prune_expired(self) -> int:
        now = datetime.now(timezone.utc)
        async with self._lock:
            expired_keys = [
                sid for sid, s in self._sessions.items()
                if (now - s.last_active) > self.ttl
            ]
            for sid in expired_keys:
                del self._sessions[sid]
            return len(expired_keys)


_memory_store: Optional[ConversationMemoryStore] = None


def get_conversation_memory() -> ConversationMemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = ConversationMemoryStore()
    return _memory_store
