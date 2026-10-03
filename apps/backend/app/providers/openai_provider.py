"""
OpenAI Provider Implementation
================================
Wraps the official openai SDK.
SDK objects are NEVER exposed outside this module.
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator

import structlog
from openai import AsyncOpenAI

from app.providers.base import LLMProvider
from app.providers.types import (
    LLMRequest, LLMResponse, ProviderHealth, ProviderName, TokenUsage
)

logger = structlog.get_logger(__name__)


class OpenAIProvider(LLMProvider):
    """
    OpenAI ChatCompletion provider.
    Supports: gpt-4o, gpt-4o-mini, o1-preview, o1-mini.
    """

    def __init__(self, api_key: str, model: str = "gpt-4o") -> None:
        self._api_key = api_key
        self._model = model
        self._client: AsyncOpenAI | None = None

    @property
    def name(self) -> ProviderName:
        return ProviderName.OPENAI

    def _get_client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if (
            not self._api_key
            or self._api_key.startswith("sk-placeholder")
            or self._api_key.startswith("your-")
            or self._api_key in ("test", "dummy")
        ):
            raise RuntimeError("OPENAI_API_KEY is not configured or is a placeholder.")

        client = self._get_client()
        start = time.perf_counter()

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        if request.response_format:
            kwargs["response_format"] = request.response_format
        if request.tools:
            kwargs["tools"] = request.tools

        try:
            resp = await client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            content = resp.choices[0].message.content or ""
            usage = resp.usage

            logger.info(
                "openai_generate_success",
                model=self._model,
                latency_ms=round(latency_ms, 1),
                prompt_tokens=usage.prompt_tokens if usage else 0,
            )

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.name,
                usage=TokenUsage(
                    prompt_tokens=usage.prompt_tokens if usage else 0,
                    completion_tokens=usage.completion_tokens if usage else 0,
                    total_tokens=usage.total_tokens if usage else 0,
                ),
                latency_ms=round(latency_ms, 1),
                finish_reason=resp.choices[0].finish_reason,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("openai_generate_failed", model=self._model, error=str(e), latency_ms=round(latency_ms, 1))
            raise

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        client = self._get_client()
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": request.messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
        }

        async with client.chat.completions.stream(**kwargs) as stream:
            async for chunk in stream:
                delta = chunk.choices[0].delta.content if chunk.choices else None
                if delta:
                    yield delta

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(
                provider=self.name,
                status="not_configured",
                error="OPENAI_API_KEY not set",
            )
        return ProviderHealth(
            provider=self.name,
            status="configured",
            model=self._model,
        )
