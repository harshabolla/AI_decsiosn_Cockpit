"""
Providers Package
=================
Multi-model provider architecture for Opella AI Decision Cockpit.

Architecture:
    Agent
      |
      v
  ModelRouter  (providers.router)
      |
  ┌───┼─────────────┬──────────┬──────────┐
  v   v             v          v          v
OpenAI  Anthropic  Gemini    Grok     Bedrock

All agents use:
    from app.providers.router import get_model_router
    router = get_model_router()
    response = await router.generate(task=LLMTask.SQL, messages=[...])

Agents NEVER import provider-specific SDKs.
"""
from app.providers.types import (
    LLMTask,
    LLMRequest,
    LLMResponse,
    ProviderName,
    ProviderHealth,
    TokenUsage,
    Message,
    MessageRole,
)
from app.providers.base import LLMProvider
from app.providers.router import ModelRouter, get_model_router

__all__ = [
    "LLMTask",
    "LLMRequest",
    "LLMResponse",
    "ProviderName",
    "ProviderHealth",
    "TokenUsage",
    "Message",
    "MessageRole",
    "LLMProvider",
    "ModelRouter",
    "get_model_router",
]
