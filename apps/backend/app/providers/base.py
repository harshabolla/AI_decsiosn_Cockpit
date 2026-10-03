"""
Base LLM Provider Interface
============================
All providers implement this ABC.
Agents NEVER import provider SDKs directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.providers.types import LLMRequest, LLMResponse, ProviderHealth, ProviderName


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    Contract:
      - generate() is the primary interface for single-response calls
      - stream() yields response tokens incrementally
      - health() returns configuration status WITHOUT making real API calls
      - Provider SDK objects NEVER leak into return values
    """

    @property
    @abstractmethod
    def name(self) -> ProviderName:
        ...

    @abstractmethod
    async def generate(
        self,
        request: LLMRequest,
    ) -> LLMResponse:
        """
        Execute a chat completion.
        Returns LLMResponse — never provider-specific objects.
        """
        ...

    @abstractmethod
    async def stream(
        self,
        request: LLMRequest,
    ) -> AsyncGenerator[str, None]:
        """
        Stream response tokens.
        Yields string chunks. Never provider-specific objects.
        """
        ...

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """
        Return configuration/health status.
        MUST NOT make real API calls unless explicitly configured for health checks.
        Check environment variables only.
        """
        ...

    def _make_error_response(self, error: str, model: str) -> LLMResponse:
        """Helper: build a structured error response."""
        from app.providers.types import TokenUsage
        return LLMResponse(
            content="",
            model=model,
            provider=self.name,
            usage=TokenUsage(),
            latency_ms=0.0,
            finish_reason="error",
        )
