"""
Provider Types — Shared Request/Response Models
================================================
All provider interactions use these types.
NO provider-specific SDK objects escape into agent code.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ProviderName(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    BEDROCK = "bedrock"
    GEMINI = "gemini"
    GROK = "grok"


class LLMTask(str, Enum):
    INTENT = "intent"
    SQL = "sql"
    SQL_PLAN = "sql_plan"
    RAG_QUERY_REWRITE = "rag_query_rewrite"
    GUIDELINE_REASONING = "guideline_reasoning"
    SUMMARY = "summary"
    VISUALIZATION = "visualization"
    REVIEWER = "reviewer"
    FAST_SUMMARY = "fast_summary"
    GENERAL = "general"


class MessageRole(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


class Message(BaseModel):
    role: MessageRole
    content: str


class LLMRequest(BaseModel):
    messages: List[Dict[str, str]]  # Keep as dicts for SDK compat
    temperature: float = 0.1
    max_tokens: int = 2048
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    stream: bool = False


class TokenUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0

    def __getitem__(self, item: str) -> int:
        return getattr(self, item)


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: ProviderName
    usage: TokenUsage = Field(default_factory=TokenUsage)
    latency_ms: float = 0.0
    finish_reason: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class ProviderHealth(BaseModel):
    provider: ProviderName
    status: str  # "configured" | "not_configured" | "error"
    model: Optional[str] = None
    error: Optional[str] = None
