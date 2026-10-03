"""
Model Router — Unified Multi-Provider LLM Gateway
==================================================
Provides backwards-compatible interface re-exporting from app.providers.
Agents call this router or app.providers.router.
Supported providers: OpenAI, Anthropic, Gemini, Grok, Bedrock.
"""
from __future__ import annotations

from app.providers.router import ModelRouter, get_model_router
from app.providers.types import LLMRequest, LLMResponse, LLMTask, ProviderName, TokenUsage

__all__ = [
    "LLMTask",
    "LLMResponse",
    "LLMRequest",
    "ProviderName",
    "TokenUsage",
    "ModelRouter",
    "get_model_router",
]
