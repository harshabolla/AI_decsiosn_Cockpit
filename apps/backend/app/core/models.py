"""
Shared Pydantic models for API request/response contracts.
"""
from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Execution Trace ───────────────────────────────────────────────────────────

class NodeStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


class TraceNode(BaseModel):
    node: str
    status: NodeStatus
    timestamp: str
    duration_ms: float | None = None
    summary: str = ""
    error: str | None = None


# ── KPI ───────────────────────────────────────────────────────────────────────

class KPI(BaseModel):
    label: str
    value: str
    trend: float | None = None  # % change
    trend_direction: str | None = None  # "up" | "down" | "neutral"
    unit: str = ""


# ── Visualization ─────────────────────────────────────────────────────────────

class VisualizationSpec(BaseModel):
    type: str  # bar | line | area | donut | scatter | table | kpi
    title: str
    x: str | None = None
    y: str | None = None
    data: list[dict[str, Any]] = []
    config: dict[str, Any] = {}


# ── SQL ───────────────────────────────────────────────────────────────────────

class SQLResult(BaseModel):
    sql: str
    tables: list[str] = []
    columns: list[str] = []
    filters: list[str] = []
    assumptions: list[str] = []
    execution_time_ms: float | None = None
    rows_returned: int | None = None
    validation_status: str = "unknown"  # valid | invalid | warning


# ── Evidence ──────────────────────────────────────────────────────────────────

class EvidenceItem(BaseModel):
    source_type: str  # snowflake | rag | servicenow | semantic | guideline
    source_name: str
    summary: str
    timestamp: str | None = None
    citation: str | None = None


# ── Action ───────────────────────────────────────────────────────────────────

class ActionStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class ProposedAction(BaseModel):
    action_id: str
    action_type: str  # create_incident | update_record | ...
    title: str
    description: str
    status: ActionStatus = ActionStatus.PENDING_APPROVAL
    payload: dict[str, Any] = {}


# ── Confidence ────────────────────────────────────────────────────────────────

class Confidence(BaseModel):
    overall: float = 0.0  # 0..1
    data_confidence: float = 0.0
    reasoning_confidence: float = 0.0
    label: str = "low"  # low | medium | high


# ── Main Response ─────────────────────────────────────────────────────────────

class ChatResponse(BaseModel):
    trace_id: str
    answer: str
    kpis: list[KPI] = []
    visualizations: list[VisualizationSpec] = []
    sources: list[EvidenceItem] = []
    sql: SQLResult | None = None
    guidelines: list[dict[str, Any]] = []
    actions: list[ProposedAction] = []
    confidence: Confidence = Field(default_factory=Confidence)
    execution_trace: list[TraceNode] = []
    warnings: list[str] = []
    adapter_note: str | None = None  # "DEMO / LOCAL ADAPTER — not real Snowflake"


# ── Chat Request ──────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: str | None = None
    session_id: str | None = None
