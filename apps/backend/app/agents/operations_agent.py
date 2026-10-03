"""
Operations Agent (ServiceNow & Human-in-the-Loop)
=================================================
Responsible for ServiceNow operational ticket inspection, incident creation,
and executive approval proposals.
Enforces the mandatory rule:
  AI proposes action -> Policy check -> Human approval -> Tool execution.
The LLM never directly executes a ticket write operation without human sign-off.
"""
from __future__ import annotations

import uuid
from typing import Any, List
import structlog

from app.agents.base import BaseAgent
from app.agents.types import (
    AgentState, ServiceNowContext, ProposedAction, ApprovalStatus, RiskLevel, Evidence
)
from app.tools.servicenow_tools import SearchIncidentsTool

logger = structlog.get_logger(__name__)


class OperationsAgent(BaseAgent[AgentState]):
    name = "operations"
    version = "1.0.0"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.search_tool = SearchIncidentsTool()

    def validate_input(self, state: AgentState) -> None:
        pass

    async def process(self, state: AgentState) -> AgentState:
        q = state.get("user_input", "").lower()
        rule_evals = state.get("business_rule_results") or []
        proposed_actions: List[ProposedAction] = state.get("proposed_actions") or []
        active_incidents: List[dict] = []

        # 1. Check for existing active incidents related to the query
        search_kw = "doliprane" if "doliprane" in q else ("india" if "india" in q else "")
        if search_kw or "incident" in q or "ticket" in q:
            search_res = await self.search_tool.execute(query=search_kw or "india")
            active_incidents = search_res.get("incidents", [])

        # 2. Check if a new incident needs to be PROPOSED
        has_critical_shortage = any(r.rule_id == "RULE-SC-01" for r in rule_evals)
        has_investigation_trigger = any(r.rule_id == "RULE-COM-02" for r in rule_evals)
        user_wants_incident = (
            any(w in q for w in ["create incident", "create a ticket", "raise ticket", "open incident"])
            or ("create" in q and "incident" in q)
            or ("supply chain" in q and any(w in q for w in ["delay", "shortage", "disruption", "issue"]))
        )

        if user_wants_incident or has_critical_shortage:
            action_id = f"ACT-{uuid.uuid4().hex[:6].upper()}"
            title = "Open ServiceNow Priority-2 Supply Chain Incident"
            desc = (
                "Automated escalation: Critical shortage alert for Doliprane (Days of Supply < 21 days). "
                "Expedited inventory redistribution required."
            )
            if "india" in q or has_investigation_trigger:
                title = "Open ServiceNow Commercial Investigation Incident"
                desc = "Commercial Policy v2.3 investigation: Sales decline in India megabrand requires operational review."

            action = ProposedAction(
                action_id=action_id,
                action_type="create_incident",
                title=title,
                description=desc,
                target_system="ServiceNow",
                parameters={
                    "short_description": title,
                    "urgency": "2 - Medium" if not has_critical_shortage else "1 - High",
                    "assignment_group": "APAC Supply Chain Operations" if "india" in q else "Supply Chain Ops",
                    "details": desc,
                },
                risk_level=RiskLevel.HIGH if has_critical_shortage else RiskLevel.MEDIUM,
                requires_human_approval=True,
                status=ApprovalStatus.PROPOSED,
            )
            proposed_actions.append(action)

        # 3. Check if discounting approval is requested
        if "discount" in q and any(w in q for w in ["approve", "override", "request", "over"]):
            action_id = f"REQ-{uuid.uuid4().hex[:6].upper()}"
            action = ProposedAction(
                action_id=action_id,
                action_type="request_approval",
                title="Request Regional CFO Discount Authorization (10.5%)",
                description="Commercial Policy v2.3 discount override (> 8.5% cap) requested for hospital tender.",
                target_system="ServiceNow",
                parameters={
                    "action_type": "discount_override",
                    "approver_role": "Regional CFO",
                    "amount": 10.5,
                    "justification": "Volume rebate for Q4 Strategic Hospital Network tender.",
                },
                risk_level=RiskLevel.HIGH,
                requires_human_approval=True,
                status=ApprovalStatus.PROPOSED,
            )
            proposed_actions.append(action)

        state["proposed_actions"] = proposed_actions
        state["service_now_context"] = ServiceNowContext(
            actions_proposed=proposed_actions,
            active_incidents=active_incidents,
            last_ticket_id=active_incidents[0]["ticket_id"] if active_incidents else None,
        )

        if active_incidents:
            evidence_list = state.get("evidence") or []
            evidence_list.append(
                Evidence(
                    source_type="servicenow",
                    source_name="ServiceNow ITOM / Incident Management",
                    summary=f"Found {len(active_incidents)} matching incident(s)",
                    citation=f"Latest Ticket: {active_incidents[0]['ticket_id']}",
                )
            )
            state["evidence"] = evidence_list

        return state

    def summarize_execution(self, state: AgentState) -> str:
        ctx = state.get("service_now_context")
        proposed = len(state.get("proposed_actions", []))
        inc_count = len(ctx.active_incidents) if ctx else 0
        return f"Operations Agent: {inc_count} active tickets found | {proposed} action(s) proposed (pending human approval)"
