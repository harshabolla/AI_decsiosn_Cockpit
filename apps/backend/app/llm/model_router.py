"""
Model Router — Provider-Agnostic LLM Interface
===============================================
Application code must NEVER call provider APIs directly.
All LLM calls go through this router.

Supported providers: openai | anthropic | bedrock
Task-based routing: intent, sql, rag_query_rewrite, summary, visualization, reviewer
"""
from __future__ import annotations

import time
from enum import Enum
from typing import Any

import structlog
from openai import AsyncOpenAI

from app.core.config import settings

logger = structlog.get_logger(__name__)


class LLMTask(str, Enum):
    INTENT = "intent"
    SQL = "sql"
    RAG_QUERY_REWRITE = "rag_query_rewrite"
    GUIDELINE_REASONING = "guideline_reasoning"
    SUMMARY = "summary"
    VISUALIZATION = "visualization"
    REVIEWER = "reviewer"


# Task → model size preference
_TASK_MODEL_MAP: dict[LLMTask, str] = {
    LLMTask.INTENT: "fast",          # cheaper, faster
    LLMTask.SQL: "default",          # needs reasoning
    LLMTask.RAG_QUERY_REWRITE: "fast",
    LLMTask.GUIDELINE_REASONING: "default",
    LLMTask.SUMMARY: "fast",
    LLMTask.VISUALIZATION: "fast",
    LLMTask.REVIEWER: "default",
}


class LLMResponse:
    def __init__(self, content: str, model: str, usage: dict[str, int], latency_ms: float) -> None:
        self.content = content
        self.model = model
        self.usage = usage
        self.latency_ms = latency_ms


class ModelRouter:
    """
    Routes LLM calls to the configured provider with:
    - task-based model selection
    - retry on failure
    - latency + token tracking
    - fallback provider
    """

    def __init__(self) -> None:
        self._openai: AsyncOpenAI | None = None

    def _get_openai(self) -> AsyncOpenAI:
        if self._openai is None:
            self._openai = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        return self._openai

    def _select_model(self, task: LLMTask, provider: str) -> str:
        size = _TASK_MODEL_MAP.get(task, "default")
        if provider == "openai":
            return settings.OPENAI_DEFAULT_MODEL if size == "default" else settings.OPENAI_FAST_MODEL
        return settings.OPENAI_DEFAULT_MODEL  # fallback

    async def complete(
        self,
        task: LLMTask,
        messages: list[dict[str, str]],
        response_format: dict[str, Any] | None = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
        retries: int = 2,
    ) -> LLMResponse:
        """
        Execute a chat completion with the configured provider.
        Returns an LLMResponse with content, model, usage, and latency.
        """
        provider = settings.LLM_PRIMARY_PROVIDER
        model = self._select_model(task, provider)

        last_error: Exception | None = None
        for attempt in range(retries + 1):
            try:
                start = time.perf_counter()
                resp = await self._call_openai(
                    model=model,
                    messages=messages,
                    response_format=response_format,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                latency_ms = (time.perf_counter() - start) * 1000
                logger.info(
                    "llm_call_success",
                    task=task,
                    model=model,
                    latency_ms=round(latency_ms, 1),
                    prompt_tokens=resp.usage.prompt_tokens,
                    completion_tokens=resp.usage.completion_tokens,
                )
                return LLMResponse(
                    content=resp.choices[0].message.content or "",
                    model=model,
                    usage={
                        "prompt_tokens": resp.usage.prompt_tokens,
                        "completion_tokens": resp.usage.completion_tokens,
                        "total_tokens": resp.usage.total_tokens,
                    },
                    latency_ms=latency_ms,
                )
            except Exception as e:
                last_error = e
                logger.warning("llm_call_failed", attempt=attempt, error=str(e), task=task)
                if attempt == retries:
                    break

        raise RuntimeError(f"LLM call failed after {retries + 1} attempts: {last_error}") from last_error

    async def _call_openai(self, model: str, messages: list, response_format: dict | None, temperature: float, max_tokens: int):
        client = self._get_openai()
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            kwargs["response_format"] = response_format
        return await client.chat.completions.create(**kwargs)


# Singleton
_router: ModelRouter | None = None


def get_model_router() -> ModelRouter:
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router
