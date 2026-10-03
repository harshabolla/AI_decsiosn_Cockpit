"""
Agent Types & Typed Shared State
=================================
The central communication contract between all agents.
Agents communicate exclusively by updating this typed state.
No agent directly invokes another agent.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, TypedDict
from pydantic import BaseModel, Field


class IntentType(str, Enum):
    ANALYTICS = "analytics"
    RAG = "rag"
    HYBRID = "hybrid"
    OPERATIONS = "operations"
    CLARIFICATION_NEEDED = "clarification_needed"
    OFF_TOPIC = "off_topic"
    INJECTION_ATTEMPT = "injection_attempt"


class SecurityAction(str, Enum):
    ALLOW = "allow"
    BLOCK = "block"
    SANITIZE = "sanitize"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PIIEntity(BaseModel):
    entity_type: str
    original: str
    token: str
    start: int
    end: int


class PIIResult(BaseModel):
    detected: bool = False
    entities: List[PIIEntity] = Field(default_factory=list)
    sanitized_text: str = ""
    token_map: Dict[str, str] = Field(default_factory=dict)


class InjectionResult(BaseModel):
    detected: bool = False
    risk: RiskLevel = RiskLevel.LOW
    patterns_matched: List[str] = Field(default_factory=list)
    action: SecurityAction = SecurityAction.ALLOW
    reason: str = ""


class SecurityResult(BaseModel):
    allowed: bool = True
    action: SecurityAction = SecurityAction.ALLOW
    pii: PIIResult = Field(default_factory=PIIResult)
    injection: InjectionResult = Field(default_factory=InjectionResult)
    sanitized_input: str = ""
    policy_notes: List[str] = Field(default_factory=list)


class Entity(BaseModel):
    entity_type: str  # product, region, date, metric
    name: str
    confidence: float = 1.0


class IntentResult(BaseModel):
    intent_type: IntentType = IntentType.ANALYTICS
    metrics: List[str] = Field(default_factory=list)
    dimensions: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    entities: List[Entity] = Field(default_factory=list)
    confidence: float = 1.0
    requires_rag: bool = False
    requires_guidelines: bool = False
    requires_operations: bool = False
    clarification_prompt: Optional[str] = None


class SemanticContext(BaseModel):
    resolved_metrics: List[str] = Field(default_factory=list)
    resolved_dimensions: List[str] = Field(default_factory=list)
    schema_context: str = ""
    tables_involved: List[str] = Field(default_factory=list)
    join_conditions: List[str] = Field(default_factory=list)
    metric_formulas: Dict[str, str] = Field(default_factory=dict)


class SQLPlan(BaseModel):
    tables: List[str] = Field(default_factory=list)
    columns: List[str] = Field(default_factory=list)
    filters: List[str] = Field(default_factory=list)
    aggregations: List[str] = Field(default_factory=list)
    group_by: List[str] = Field(default_factory=list)
    order_by: List[str] = Field(default_factory=list)
    limit: int = 1000
    assumptions: List[str] = Field(default_factory=list)


class SQLValidationResult(BaseModel):
    valid: bool = True
    status: str = "valid"  # valid | invalid | warning
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    is_read_only: bool = True
    forbidden_clauses: List[str] = Field(default_factory=list)


class QueryResult(BaseModel):
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    adapter: str = "LOCAL_DEMO"
    error: Optional[str] = None


class RetrievedDocument(BaseModel):
    document_id: str
    document_name: str
    version: str = "1.0"
    domain: str
    country: Optional[str] = None
    product: Optional[str] = None
    section: Optional[str] = None
    content: str
    score: float = 1.0
    effective_from: Optional[str] = None
    effective_to: Optional[str] = None
    is_active: bool = True


class BusinessRuleResult(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    details: str
    severity: str = "info"  # info | warning | violation


class GuidelineContext(BaseModel):
    applicable_guidelines: List[RetrievedDocument] = Field(default_factory=list)
    rule_evaluations: List[BusinessRuleResult] = Field(default_factory=list)
    conflict_detected: bool = False
    conflict_notes: List[str] = Field(default_factory=list)


class ApprovalStatus(str, Enum):
    PROPOSED = "proposed"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTED = "executed"


class ProposedAction(BaseModel):
    action_id: str
    action_type: str
    title: str
    description: str
    target_system: str = "ServiceNow"
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    requires_human_approval: bool = True
    status: ApprovalStatus = ApprovalStatus.PROPOSED
    ticket_id: Optional[str] = None
    audit_notes: Optional[str] = None


class ServiceNowContext(BaseModel):
    actions_proposed: List[ProposedAction] = Field(default_factory=list)
    active_incidents: List[Dict[str, Any]] = Field(default_factory=list)
    last_ticket_id: Optional[str] = None


class VisualizationSpec(BaseModel):
    type: str = "bar"  # bar | line | area | donut | table | kpi
    title: str
    x: Optional[str] = None
    y: Optional[str] = None
    data: List[Dict[str, Any]] = Field(default_factory=list)
    config: Dict[str, Any] = Field(default_factory=dict)
    columns: Optional[List[str]] = None


class Evidence(BaseModel):
    source_type: str  # snowflake | rag | servicenow | semantic | guideline
    source_name: str
    summary: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    citation: Optional[str] = None


class ReviewResult(BaseModel):
    approved: bool = True
    semantic_accuracy: float = 1.0
    sql_consistency: float = 1.0
    hallucination_detected: bool = False
    unsupported_claims: List[str] = Field(default_factory=list)
    review_notes: List[str] = Field(default_factory=list)
    retry_needed: bool = False
    replan_target: Optional[str] = None


class FinalResponse(BaseModel):
    answer: str = ""
    summary_bullets: List[str] = Field(default_factory=list)
    kpis: List[Dict[str, Any]] = Field(default_factory=list)
    confidence: float = 1.0
    confidence_label: str = "high"
    adapter_disclaimer: Optional[str] = None


class ExecutionEvent(BaseModel):
    node: str
    status: str  # waiting | running | success | failed | skipped
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    duration_ms: Optional[float] = None
    summary: str = ""
    error: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)


class AgentError(BaseModel):
    agent_name: str
    error_message: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recoverable: bool = False


# ── The Typed State Contract ──────────────────────────────────────────────────

class AgentState(TypedDict, total=False):
    # Tracing & User Context
    trace_id: str
    user_id: str
    conversation_id: str
    user_input: str
    normalized_input: str

    # Security
    security_result: SecurityResult

    # Intent
    intent: IntentResult
    entities: List[Entity]

    # Semantic Layer
    semantic_context: SemanticContext

    # SQL Analytics
    sql_plan: SQLPlan
    generated_sql: str
    sql_validation: SQLValidationResult
    query_result: QueryResult

    # Knowledge RAG
    retrieved_documents: List[RetrievedDocument]

    # Guidelines & Business Rules
    guideline_context: GuidelineContext
    business_rule_results: List[BusinessRuleResult]

    # Operations / ServiceNow
    service_now_context: ServiceNowContext
    proposed_actions: List[ProposedAction]

    # Visualizations & KPIs
    visualization: Optional[VisualizationSpec]
    kpis: List[Dict[str, Any]]

    # Evidence & Audit
    evidence: List[Evidence]

    # Reviewer & Guardrail
    reviewer_result: ReviewResult

    # Output & Response
    final_response: FinalResponse
    warnings: List[str]

    # Execution telemetry (for SSE streaming)
    execution_events: List[ExecutionEvent]
    errors: List[AgentError]
    tracer: Any
