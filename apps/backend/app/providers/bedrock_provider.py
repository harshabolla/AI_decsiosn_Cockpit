"""
AWS Bedrock Provider Implementation
=====================================
Wraps boto3 for AWS Bedrock Claude/Titan/Llama models.
SDK objects are NEVER exposed outside this module.
"""
from __future__ import annotations

import json
import time
from typing import Any, AsyncGenerator

import structlog

from app.providers.base import LLMProvider
from app.providers.types import (
    LLMRequest, LLMResponse, ProviderHealth, ProviderName, TokenUsage
)

logger = structlog.get_logger(__name__)


class BedrockProvider(LLMProvider):
    """
    AWS Bedrock provider using boto3.
    Supports Claude models via Bedrock:
      anthropic.claude-3-5-sonnet-20241022-v2:0
      anthropic.claude-3-haiku-20240307-v1:0
    """

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        region: str = "us-east-1",
        model: str = "anthropic.claude-3-5-sonnet-20241022-v2:0",
    ) -> None:
        self._access_key_id = access_key_id
        self._secret_access_key = secret_access_key
        self._region = region
        self._model = model
        self._client: Any | None = None

    @property
    def name(self) -> ProviderName:
        return ProviderName.BEDROCK

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import boto3
                self._client = boto3.client(
                    service_name="bedrock-runtime",
                    region_name=self._region,
                    aws_access_key_id=self._access_key_id,
                    aws_secret_access_key=self._secret_access_key,
                )
            except ImportError:
                raise RuntimeError(
                    "boto3 not installed. Run: pip install boto3"
                )
        return self._client

    def _build_claude_body(self, request: LLMRequest) -> dict[str, Any]:
        """Build Anthropic-format body for Claude on Bedrock."""
        system_msg = ""
        messages = []
        for m in request.messages:
            if m.get("role") == "system":
                system_msg = m.get("content", "")
            else:
                messages.append({"role": m["role"], "content": m["content"]})

        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": request.max_tokens,
            "messages": messages,
            "temperature": request.temperature,
        }
        if system_msg:
            body["system"] = system_msg
        return body

    async def generate(self, request: LLMRequest) -> LLMResponse:
        import asyncio
        client = self._get_client()
        start = time.perf_counter()

        body = self._build_claude_body(request)

        try:
            def _invoke():
                return client.invoke_model(
                    modelId=self._model,
                    body=json.dumps(body),
                    contentType="application/json",
                    accept="application/json",
                )

            resp = await asyncio.get_event_loop().run_in_executor(None, _invoke)
            latency_ms = (time.perf_counter() - start) * 1000

            body_resp = json.loads(resp["body"].read())
            content = body_resp.get("content", [{}])[0].get("text", "")
            usage = body_resp.get("usage", {})

            logger.info(
                "bedrock_generate_success",
                model=self._model,
                latency_ms=round(latency_ms, 1),
                input_tokens=usage.get("input_tokens", 0),
            )

            return LLMResponse(
                content=content,
                model=self._model,
                provider=self.name,
                usage=TokenUsage(
                    prompt_tokens=usage.get("input_tokens", 0),
                    completion_tokens=usage.get("output_tokens", 0),
                    total_tokens=usage.get("input_tokens", 0) + usage.get("output_tokens", 0),
                ),
                latency_ms=round(latency_ms, 1),
                finish_reason=body_resp.get("stop_reason", "stop"),
            )
        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error("bedrock_generate_failed", model=self._model, error=str(e))
            raise

    async def stream(self, request: LLMRequest) -> AsyncGenerator[str, None]:
        import asyncio
        client = self._get_client()
        body = self._build_claude_body(request)

        def _stream_invoke():
            return client.invoke_model_with_response_stream(
                modelId=self._model,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )

        resp = await asyncio.get_event_loop().run_in_executor(None, _stream_invoke)
        for event in resp.get("body", []):
            chunk = event.get("chunk", {})
            chunk_data = json.loads(chunk.get("bytes", b"{}"))
            if chunk_data.get("type") == "content_block_delta":
                delta = chunk_data.get("delta", {}).get("text", "")
                if delta:
                    yield delta

    async def health(self) -> ProviderHealth:
        if not self._access_key_id or not self._secret_access_key:
            return ProviderHealth(
                provider=self.name,
                status="not_configured",
                error="AWS_ACCESS_KEY_ID or AWS_SECRET_ACCESS_KEY not set",
            )
        return ProviderHealth(
            provider=self.name,
            status="configured",
            model=self._model,
        )
