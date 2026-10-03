"""
Anthropic Provider Implementation
===================================
Wraps the official anthropic SDK.
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


class AnthropicProvider(LLMProvider):
    """
    Anthropic Claude provider.
    Supports: claude-3-5-sonnet, claude-3-opus, claude-3-haiku.
    """

    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022") -> None:
        self._api_key = api_key
        self._model = model
        self._client: Any | None = None

    @property
    def name(self) -> ProviderName:
        return ProviderName.ANTHROPIC

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=self._api_key)
            except ImportError:
                raise RuntimeError(
                    "anthropic package not installed. Run: pip install anthropic"
                )
        return self._client

    def _convert_messages(self, messages: list[dict]) -> tuple[str | None, list[dict]]:
        """
        Anthropic separates system prompt from messages.
        Extract system message and convert remaining messages.
        """
        system: str | None = None
        converted: list[dict] = []
        for m in messages:
            if m.get("role") == "system":
                system = m.get("content", "")
            else:
                converted.append({"role": m["role"], "content": m["content"]})
        return system, converted

    async def generate(self, request: LLMRequest) -> LLMResponse:
        if (
            not self._api_key
            or self._api_key.startswith("sk-ant-placeholder")
            or self._api_key.startswith("your-")
            or self._api_key in ("test", "dummy")
        ):
            raise RuntimeError("ANTHROPIC_API_KEY is not configured or is a placeholder.")

        client = self._get_client()
        start = time.perf_counter()

        system, msgs = self._convert_messages(request.messages)
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": msgs,
            "max_tokens": request.max_tokens,
        }
        if system:
            kwargs["system"] = system
        # Anthropic uses temperature differently — only if not None
        if request.temperature is not None:
            kwargs["temperature"] = request.temperature

        try:
            resp = await client.messages.create(**kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            content = resp.content[0].text if resp.content else ""
            usage = resp.usage

            logger.info(
                "anthropic_generate_success",
                model=self._model,
                latency_ms=round(latency_ms, 1),
                input_tokens=usage.input_tokens if usage else 0,
            )

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.name,
                usage=TokenUsage(
                    prompt_tokens=usage.input_tokens if usage else 0,
                    completion_tokens=usage.output_tokens if usage else 0,
                    total_tokens=(usage.input_tokens + usage.output_tokens) if usage else 0,
                ),
                latency_ms=round(latency_ms, 1),
                finish_reason=resp.stop_reason,
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("anthropic_generate_failed", model=self._model, error=str(e))
            raise

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        client = self._get_client()
        system, msgs = self._convert_messages(request.messages)

        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": msgs,
            "max_tokens": request.max_tokens,
        }
        if system:
            kwargs["system"] = system

        async with client.messages.stream(**kwargs) as stream:
            async for text in stream.text_stream:
                yield text

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(
                provider=self.name,
                status="not_configured",
                error="ANTHROPIC_API_KEY not set",
            )
        return ProviderHealth(
            provider=self.name,
            status="configured",
            model=self._model,
        )
