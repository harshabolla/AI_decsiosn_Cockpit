"""
Model Router — Multi-Provider Task-Aware Routing
=================================================
Central routing layer between agents and LLM providers.

Architecture:
    Agent
      |
      v
  ModelRouter  (this module)
      |
   Task-Based Routing
      |
  ┌───┴────────────┐
  v                v
OpenAI          Gemini    ...etc
  |
  Fallback chain on failure

Design rules:
  - Agents call router.generate(task=..., messages=...)
  - Agents NEVER call provider SDKs directly
  - Provider is selected by task config
  - Fallback chain is configurable
  - All attempts are logged with provider/model/latency/failure_reason
  - API keys are NEVER logged
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import structlog

from app.providers.base import LLMProvider
from app.providers.types import (
    LLMRequest, LLMResponse, LLMTask, ProviderHealth, ProviderName, TokenUsage
)
from app.core.config import settings

logger = structlog.get_logger(__name__)


# ── Task → Provider/Model Config ─────────────────────────────────────────────

def _get_task_config() -> Dict[LLMTask, Dict[str, str]]:
    """
    Build task routing config from environment settings.
    Allows switching providers per task without code changes.
    """
    default_provider = settings.DEFAULT_LLM_PROVIDER
    default_model = settings.DEFAULT_LLM_MODEL

    return {
        LLMTask.INTENT: {
            "provider": getattr(settings, "INTENT_PROVIDER", default_provider),
            "model": getattr(settings, "INTENT_MODEL", settings.OPENAI_FAST_MODEL),
        },
        LLMTask.SQL: {
            "provider": getattr(settings, "SQL_PROVIDER", default_provider),
            "model": getattr(settings, "SQL_MODEL", default_model),
        },
        LLMTask.SQL_PLAN: {
            "provider": getattr(settings, "SQL_PROVIDER", default_provider),
            "model": getattr(settings, "SQL_MODEL", default_model),
        },
        LLMTask.RAG_QUERY_REWRITE: {
            "provider": getattr(settings, "RAG_PROVIDER", default_provider),
            "model": getattr(settings, "RAG_MODEL", settings.OPENAI_FAST_MODEL),
        },
        LLMTask.GUIDELINE_REASONING: {
            "provider": getattr(settings, "RAG_PROVIDER", default_provider),
            "model": getattr(settings, "RAG_MODEL", default_model),
        },
        LLMTask.REVIEWER: {
            "provider": getattr(settings, "REVIEWER_PROVIDER", default_provider),
            "model": getattr(settings, "REVIEWER_MODEL", default_model),
        },
        LLMTask.VISUALIZATION: {
            "provider": getattr(settings, "FAST_PROVIDER", default_provider),
            "model": getattr(settings, "FAST_MODEL", settings.OPENAI_FAST_MODEL),
        },
        LLMTask.SUMMARY: {
            "provider": default_provider,
            "model": default_model,
        },
        LLMTask.FAST_SUMMARY: {
            "provider": getattr(settings, "FAST_PROVIDER", default_provider),
            "model": getattr(settings, "FAST_MODEL", settings.OPENAI_FAST_MODEL),
        },
        LLMTask.GENERAL: {
            "provider": default_provider,
            "model": default_model,
        },
    }


# ── Provider Factory ──────────────────────────────────────────────────────────

def _build_provider(provider_name: str, model: Optional[str] = None) -> LLMProvider:
    """
    Instantiate a provider from config.
    Lazy import of SDKs to avoid hard dependency failures.
    """
    pname = provider_name.lower()

    if pname == ProviderName.OPENAI:
        from app.providers.openai_provider import OpenAIProvider
        return OpenAIProvider(
            api_key=settings.OPENAI_API_KEY,
            model=model or settings.DEFAULT_LLM_MODEL,
        )

    elif pname == ProviderName.ANTHROPIC:
        from app.providers.anthropic_provider import AnthropicProvider
        return AnthropicProvider(
            api_key=settings.ANTHROPIC_API_KEY,
            model=model or settings.ANTHROPIC_DEFAULT_MODEL,
        )

    elif pname == ProviderName.GEMINI:
        from app.providers.gemini_provider import GeminiProvider
        api_key = settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        return GeminiProvider(
            api_key=api_key,
            model=model or settings.GEMINI_DEFAULT_MODEL,
        )

    elif pname == ProviderName.GROK:
        from app.providers.grok_provider import GrokProvider
        return GrokProvider(
            api_key=settings.XAI_API_KEY,
            model=model or settings.GROK_DEFAULT_MODEL,
        )

    elif pname == ProviderName.BEDROCK:
        from app.providers.bedrock_provider import BedrockProvider
        return BedrockProvider(
            access_key_id=settings.AWS_ACCESS_KEY_ID,
            secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region=settings.AWS_REGION,
            model=model or settings.BEDROCK_MODEL_ID,
        )

    else:
        raise ValueError(f"Unknown provider: {provider_name}")


# ── Model Router ──────────────────────────────────────────────────────────────

class ModelRouter:
    """
    Routes LLM calls to the configured provider per task.

    Fallback strategy:
      1. Primary provider for task (from config)
      2. On failure: try each provider in fallback_chain
      3. If all fail: raise RuntimeError with last error

    All attempts are logged. API keys are never logged.
    """

    def __init__(self) -> None:
        self._provider_cache: Dict[str, LLMProvider] = {}
        self._task_config = _get_task_config()

    def _get_provider(self, provider_name: str, model: Optional[str] = None) -> LLMProvider:
        cache_key = f"{provider_name}:{model or 'default'}"
        if cache_key not in self._provider_cache:
            self._provider_cache[cache_key] = _build_provider(provider_name, model)
        return self._provider_cache[cache_key]

    def _get_fallback_chain(self) -> List[str]:
        """Return configured fallback provider chain (excluding primary already tried)."""
        chain_str = getattr(settings, "LLM_FALLBACK_CHAIN", "")
        if chain_str:
            return [p.strip() for p in chain_str.split(",") if p.strip()]
        # Default fallback chain
        return [settings.LLM_FALLBACK_PROVIDER] if settings.LLM_FALLBACK_PROVIDER else []

    async def generate(
        self,
        task: LLMTask,
        messages: List[Dict[str, Any]],
        temperature: float = 0.1,
        max_tokens: int = 2048,
        response_format: Optional[Dict[str, Any]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        retries: int = 1,
    ) -> LLMResponse:
        """
        Primary interface for all LLM calls.
        Routes by task, applies fallback chain on failure.
        """
        task_cfg = self._task_config.get(task, {
            "provider": settings.DEFAULT_LLM_PROVIDER,
            "model": settings.DEFAULT_LLM_MODEL,
        })
        primary_provider = task_cfg["provider"]
        primary_model = task_cfg["model"]

        request = LLMRequest(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            tools=tools,
        )

        # Attempt primary provider (with retries)
        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                provider = self._get_provider(primary_provider, primary_model)
                start = time.perf_counter()
                response = await provider.generate(request)
                total_ms = (time.perf_counter() - start) * 1000

                logger.info(
                    "model_router_success",
                    task=task.value,
                    provider=primary_provider,
                    model=primary_model,
                    attempt=attempt,
                    latency_ms=round(total_ms, 1),
                    fallback_used=False,
                )
                return response
            except Exception as e:
                last_error = e
                logger.warning(
                    "model_router_attempt_failed",
                    task=task.value,
                    provider=primary_provider,
                    model=primary_model,
                    attempt=attempt,
                    failure_reason=str(e),
                )

        # Fallback chain
        fallback_chain = self._get_fallback_chain()
        tried = {primary_provider}

        for fallback_provider_name in fallback_chain:
            if fallback_provider_name in tried:
                continue
            tried.add(fallback_provider_name)

            try:
                # Use fallback provider's default model
                fallback_provider = self._get_provider(fallback_provider_name)
                start = time.perf_counter()
                response = await fallback_provider.generate(request)
                total_ms = (time.perf_counter() - start) * 1000

                logger.warning(
                    "model_router_fallback_success",
                    task=task.value,
                    primary_provider=primary_provider,
                    fallback_provider=fallback_provider_name,
                    latency_ms=round(total_ms, 1),
                    fallback_used=True,
                    original_failure=str(last_error),
                )
                return response
            except Exception as e:
                last_error = e
                logger.error(
                    "model_router_fallback_failed",
                    task=task.value,
                    fallback_provider=fallback_provider_name,
                    failure_reason=str(e),
                )

        raise RuntimeError(
            f"All LLM providers failed for task={task.value}. "
            f"Last error: {last_error}"
        ) from last_error

    async def complete(
        self,
        task: LLMTask,
        messages: List[Dict[str, Any]],
        response_format: Optional[Dict[str, Any]] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        retries: int = 1,
    ) -> LLMResponse:
        """Backward-compatible complete() alias for generate()."""
        return await self.generate(
            task=task,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            response_format=response_format,
            retries=retries,
        )

    async def get_all_health(self) -> Dict[str, ProviderHealth]:
        """
        Return health status for all configured providers.
        Does NOT make real API calls unless health_check_enabled.
        Checks configuration only.
        """
        results: Dict[str, ProviderHealth] = {}

        provider_configs = [
            ("openai", settings.OPENAI_API_KEY, settings.DEFAULT_LLM_MODEL),
            ("anthropic", settings.ANTHROPIC_API_KEY, settings.ANTHROPIC_DEFAULT_MODEL),
            ("gemini", settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY, settings.GEMINI_DEFAULT_MODEL),
            ("grok", settings.XAI_API_KEY, settings.GROK_DEFAULT_MODEL),
            ("bedrock", settings.AWS_ACCESS_KEY_ID, settings.BEDROCK_MODEL_ID),
        ]

        for pname, api_key, model in provider_configs:
            try:
                provider = self._get_provider(pname, model)
                health = await provider.health()
                results[pname] = health
            except Exception as e:
                results[pname] = ProviderHealth(
                    provider=ProviderName(pname),
                    status="error",
                    error=str(e),
                )

        return results


# ── Singleton ─────────────────────────────────────────────────────────────────

_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
