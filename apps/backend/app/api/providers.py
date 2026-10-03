"""
Providers Health API
=====================
GET /api/providers/health
  Returns configuration status for all LLM providers.
  Does NOT make real API calls.
  Does NOT expose credentials.
"""
from __future__ import annotations

from typing import Any, Dict

import structlog
from fastapi import APIRouter

from app.core.config import settings
from app.providers.router import get_model_router

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["providers"])


@router.get("/providers/health")
async def providers_health() -> Dict[str, Any]:
    """
    GET /api/providers/health

    Returns configuration status for each provider.
    Status values:
      "configured"     — API key is present in environment
      "not_configured" — API key is missing
      "error"          — Provider failed to instantiate

    Credentials are NEVER returned or logged.
    """
    model_router = get_model_router()
    all_health = await model_router.get_all_health()

    result: Dict[str, Any] = {}
    for provider_name, health in all_health.items():
        result[provider_name] = {
            "status": health.status,
            "model": health.model,
            # Do NOT include error details that might hint at credentials
            "error": health.error if health.status not in ("configured",) else None,
        }

    return {
        "default_provider": settings.DEFAULT_LLM_PROVIDER,
        "providers": result,
        "note": "Status reflects environment configuration only. No real API calls made.",
    }
