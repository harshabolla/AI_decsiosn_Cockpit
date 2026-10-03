"""
xAI Grok Provider Implementation
==================================
xAI Grok is compatible with the OpenAI API spec.
Uses base_url override on the OpenAI SDK.
SDK objects are NEVER exposed outside this module.
"""
from __future__ import annotations

import time
from typing import Any, AsyncGenerator

import structlog

from app.providers.base import LLMProvider
from app.providers.types import (
    LLMRequest, LLMResponse, ProviderHealth, ProviderName, TokenUsage
)

logger = structlog.get_logger(__name__)

_GROK_BASE_URL = "https://api.x.ai/v1"


class GrokProvider(LLMProvider):
    """
    xAI Grok provider.
    Grok is OpenAI-API-compatible, so we reuse the OpenAI SDK
    with a different base URL and API key.
    Supports: grok-beta, grok-2.
    """

    def __init__(self, api_key: str, model: str = "grok-beta") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None

    @property
    def name(self) -> ProviderName:
        return ProviderName.GROK

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(
                    api_key=self._api_key,
                    base_url=_GROK_BASE_URL,
                )
            except ImportError:
                raise RuntimeError("openai package required for Grok provider")
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if (
            not self._api_key
            or self._api_key.startswith("xai-placeholder")
            or self._api_key.startswith("your-")
            or self._api_key in ("test", "dummy")
        ):
            raise RuntimeError("XAI_API_KEY is not configured or is a placeholder.")

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

        try:
            resp = await client.chat.completions.create(**kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            content = resp.choices[0].message.content or ""
            usage = resp.usage

            logger.info(
                "grok_generate_success",
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
            logger.error("grok_generate_failed", model=self._model, error=str(e))
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
                error="XAI_API_KEY not set",
            )
        return ProviderHealth(
            provider=self.name,
            status="configured",
            model=self._model,
        )
