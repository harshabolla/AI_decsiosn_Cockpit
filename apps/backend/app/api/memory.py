"""
Memory API — Session Management & History Inspection Endpoints
=============================================================
GET /api/memory/sessions
  List all active conversation sessions.
GET /api/memory/sessions/{session_id}
  Retrieve the complete turn history and context for a specific session.
DELETE /api/memory/sessions/{session_id}
  Clear conversation state and history for a session.
"""
from __future__ import annotations

from typing import Any, Dict, List
import structlog
from fastapi import APIRouter, HTTPException

from app.memory.store import get_conversation_memory

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/memory", tags=["memory"])


@router.get("/sessions")
async def list_sessions() -> List[Dict[str, Any]]:
    """List active sessions and turn statistics."""
    mem = get_conversation_memory()
    return await mem.list_sessions()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> Dict[str, Any]:
    """Retrieve full history for a given session."""
    mem = get_conversation_memory()
    session = await mem.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return session.model_dump()


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str) -> Dict[str, str]:
    """Clear memory for a given session."""
    mem = get_conversation_memory()
    cleared = await mem.clear_session(session_id)
    if not cleared:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    return {"status": "ok", "message": f"Session {session_id} memory cleared"}
