"""
Google Gemini Provider Implementation
=======================================
Wraps the official google-generativeai SDK.
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


class GeminiProvider(LLMProvider):
    """
    Google Gemini provider.
    Supports: gemini-1.5-pro, gemini-1.5-flash, gemini-2.0-flash-exp.
    Uses GOOGLE_API_KEY or GEMINI_API_KEY.
    """

    def __init__(self, api_key: str, model: str = "gemini-1.5-flash") -> None:
        self._api_key = api_key
        self._model = model
        self._genai: Any | None = None

    @property
    def name(self) -> ProviderName:
        return ProviderName.GEMINI

    def _get_genai(self) -> Any:
        if self._genai is None:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self._api_key)
                self._genai = genai
            except ImportError:
                raise RuntimeError(
                    "google-generativeai not installed. Run: pip install google-generativeai"
                )
        return self._genai

    def _convert_to_gemini_format(self, messages: list[dict]) -> tuple[str, list[dict]]:
        """
        Convert OpenAI-style messages to Gemini format.
        Gemini uses 'user'/'model' roles and extracts system instructions.
        """
        system_instruction = ""
        gemini_messages: list[dict] = []

        for m in messages:
            role = m.get("role", "user")
            content = m.get("content", "")
            if role == "system":
                system_instruction = content
            elif role == "user":
                gemini_messages.append({"role": "user", "parts": [content]})
            elif role == "assistant":
                gemini_messages.append({"role": "model", "parts": [content]})

        return system_instruction, gemini_messages

    async def generate(self, request: LLMRequest) -> LLMResponse:
        import asyncio
        genai = self._get_genai()
        start = time.perf_counter()

        system_instruction, gemini_msgs = self._convert_to_gemini_format(request.messages)

        try:
            model_kwargs: dict[str, Any] = {"model_name": self._model}
            if system_instruction:
                model_kwargs["system_instruction"] = system_instruction

            model = genai.GenerativeModel(**model_kwargs)

            generation_config = genai.types.GenerationConfig(
                temperature=request.temperature,
                max_output_tokens=request.max_tokens,
            )

            # Build content from last message for simple case
            # For full conversation, use chat
            if len(gemini_msgs) == 1:
                prompt = gemini_msgs[0]["parts"][0]
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: model.generate_content(
                        prompt,
                        generation_config=generation_config,
                    )
                )
            else:
                chat = model.start_chat(history=gemini_msgs[:-1])
                last_msg = gemini_msgs[-1]["parts"][0] if gemini_msgs else ""
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: chat.send_message(last_msg, generation_config=generation_config)
                )

            latency_ms = (time.perf_counter() - start) * 1000
            content = resp.text if hasattr(resp, "text") else ""

            usage_meta = getattr(resp, "usage_metadata", None)
            prompt_tokens = getattr(usage_meta, "prompt_token_count", 0) or 0
            completion_tokens = getattr(usage_meta, "candidates_token_count", 0) or 0

            logger.info(
                "gemini_generate_success",
                model=self._model,
                latency_ms=round(latency_ms, 1),
                prompt_tokens=prompt_tokens,
            )

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.name,
                usage=TokenUsage(
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=prompt_tokens + completion_tokens,
                ),
                latency_ms=round(latency_ms, 1),
                finish_reason="stop",
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("gemini_generate_failed", model=self._model, error=str(e))
            raise

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        import asyncio
        genai = self._get_genai()
        _, gemini_msgs = self._convert_to_gemini_format(request.messages)

        model = genai.GenerativeModel(model_name=self._model)
        generation_config = genai.types.GenerationConfig(
            temperature=request.temperature,
            max_output_tokens=request.max_tokens,
        )

        last_msg = gemini_msgs[-1]["parts"][0] if gemini_msgs else ""

        def _sync_stream():
            return model.generate_content(
                last_msg,
                generation_config=generation_config,
                stream=True,
            )

        resp_stream = await asyncio.get_event_loop().run_in_executor(None, _sync_stream)
        for chunk in resp_stream:
            if hasattr(chunk, "text") and chunk.text:
                yield chunk.text

    async def health(self) -> ProviderHealth:
        if not self._api_key:
            return ProviderHealth(
                provider=self.name,
                status="not_configured",
                error="GOOGLE_API_KEY or GEMINI_API_KEY not set",
            )
        return ProviderHealth(
            provider=self.name,
            status="configured",
            model=self._model,
        )
