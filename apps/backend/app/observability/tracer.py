"""
Observability — Execution Tracer
=================================
Every request gets a trace ID. Each agent node reports its status.
Emits structured events that are streamed to the frontend via SSE.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Awaitable

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class TraceEvent:
    trace_id: str
    node: str
    status: str  # waiting | running | success | failed | skipped
    timestamp: str
    duration_ms: float | None = None
    summary: str = ""
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "node": self.node,
            "status": self.status,
            "timestamp": self.timestamp,
            "duration_ms": self.duration_ms,
            "summary": self.summary,
            "error": self.error,
            # metadata excluded — may contain internal details
        }


class RequestTracer:
    """
    Tracks execution across all pipeline nodes for a single request.
    """

    def __init__(self) -> None:
        self.trace_id: str = str(uuid.uuid4())[:8].upper()
        self._events: list[TraceEvent] = []
        self._callbacks: list[Callable[[TraceEvent], Awaitable[None]]] = []
        self._start_times: dict[str, float] = {}
        self._total_tokens: int = 0
        self._total_latency_ms: float = 0.0

    def add_callback(self, cb: Callable[[TraceEvent], Awaitable[None]]) -> None:
        self._callbacks.append(cb)

    async def _emit(self, event: TraceEvent) -> None:
        self._events.append(event)
        logger.info("trace_event", trace_id=self.trace_id, node=event.node, status=event.status)
        for cb in self._callbacks:
            try:
                await cb(event)
            except Exception:
                pass

    async def node_start(self, node: str, summary: str = "") -> None:
        self._start_times[node] = time.perf_counter()
        ts = _iso_now()
        await self._emit(TraceEvent(
            trace_id=self.trace_id,
            node=node,
            status="running",
            timestamp=ts,
            summary=summary,
        ))

    async def node_success(self, node: str, summary: str = "", metadata: dict | None = None) -> None:
        duration = self._calc_duration(node)
        self._total_latency_ms += duration or 0
        await self._emit(TraceEvent(
            trace_id=self.trace_id,
            node=node,
            status="success",
            timestamp=_iso_now(),
            duration_ms=duration,
            summary=summary,
            metadata=metadata or {},
        ))

    async def node_failed(self, node: str, error: str, summary: str = "") -> None:
        duration = self._calc_duration(node)
        await self._emit(TraceEvent(
            trace_id=self.trace_id,
            node=node,
            status="failed",
            timestamp=_iso_now(),
            duration_ms=duration,
            summary=summary,
            error=error,
        ))

    async def node_skipped(self, node: str, reason: str = "") -> None:
        await self._emit(TraceEvent(
            trace_id=self.trace_id,
            node=node,
            status="skipped",
            timestamp=_iso_now(),
            summary=reason,
        ))

    def _calc_duration(self, node: str) -> float | None:
        start = self._start_times.pop(node, None)
        if start is None:
            return None
        return round((time.perf_counter() - start) * 1000, 1)

    def record_tokens(self, tokens: int) -> None:
        self._total_tokens += tokens

    def get_summary(self) -> dict[str, Any]:
        return {
            "trace_id": self.trace_id,
            "total_tokens": self._total_tokens,
            "total_latency_ms": round(self._total_latency_ms, 1),
            "nodes_executed": len(self._events),
        }

    def get_events(self) -> list[dict[str, Any]]:
        return [e.to_dict() for e in self._events]


def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
