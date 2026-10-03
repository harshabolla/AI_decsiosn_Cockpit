"""
ServiceNow Operational Tools
============================
Enforces Human-in-the-Loop approval workflows for incident creation and override requests.
Read actions are automated; write actions require human authorization.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List
import structlog
from app.tools.base import BaseTool

logger = structlog.get_logger(__name__)

# In-memory ticket mock database
_INCIDENTS_DB: List[Dict[str, Any]] = [
    {
        "ticket_id": "INC0049210",
        "short_description": "India Doliprane supply chain delay — Mumbai distribution hub",
        "urgency": "1 - High",
        "state": "In Progress",
        "assignment_group": "APAC Supply Chain Operations",
        "created_at": "2026-09-15T08:30:00Z",
    },
    {
        "ticket_id": "INC0048102",
        "short_description": "France Allegra inventory buffer reconciliation",
        "urgency": "2 - Medium",
        "state": "Resolved",
        "assignment_group": "EMEA Logistics",
        "created_at": "2026-08-10T11:15:00Z",
    },
]


class SearchIncidentsTool(BaseTool):
    name = "servicenow_search_incidents"
    description = "Search active or historical ServiceNow incident tickets by keyword or product."
    target_system = "ServiceNow"
    risk_level = "low"
    requires_approval = False

    parameters = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Keywords to match against incident descriptions (e.g. Doliprane, India).",
            },
        },
        "required": ["query"],
    }

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        q = kwargs.get("query", "").lower()
        matches = [
            inc for inc in _INCIDENTS_DB
            if q in inc["short_description"].lower() or q in inc.get("assignment_group", "").lower()
        ]
        return {
            "status": "success",
            "count": len(matches),
            "incidents": matches,
        }


class CreateIncidentTool(BaseTool):
    name = "servicenow_create_incident"
    description = "Create an incident in ServiceNow. Requires explicit human confirmation."
    target_system = "ServiceNow"
    risk_level = "medium"
    requires_approval = True  # Strict gate: Cannot execute without human consent

    parameters = {
        "type": "object",
        "properties": {
            "short_description": {"type": "string", "description": "Brief summary of the issue."},
            "urgency": {"type": "string", "enum": ["1 - High", "2 - Medium", "3 - Low"]},
            "assignment_group": {"type": "string", "description": "Responsible team."},
            "details": {"type": "string", "description": "Detailed explanation of root cause or evidence."},
        },
        "required": ["short_description", "urgency"],
    }

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        ticket_id = f"INC{uuid.uuid4().hex[:7].upper()}"
        new_inc = {
            "ticket_id": ticket_id,
            "short_description": kwargs.get("short_description"),
            "urgency": kwargs.get("urgency", "2 - Medium"),
            "state": "New",
            "assignment_group": kwargs.get("assignment_group", "Supply Chain Ops"),
            "details": kwargs.get("details", ""),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        _INCIDENTS_DB.append(new_inc)
        logger.info("servicenow_incident_created", ticket_id=ticket_id, urgency=new_inc["urgency"])
        return {
            "status": "created",
            "ticket_id": ticket_id,
            "incident": new_inc,
            "message": f"Incident {ticket_id} opened successfully.",
        }


class RequestApprovalTool(BaseTool):
    name = "servicenow_request_approval"
    description = "Propose an executive authorization request (e.g., discounting override > 8.5%)."
    target_system = "ServiceNow"
    risk_level = "high"
    requires_approval = True

    parameters = {
        "type": "object",
        "properties": {
            "action_type": {"type": "string", "description": "Type of override (e.g. discount_override, safety_stock_deviation)."},
            "approver_role": {"type": "string", "description": "Authorized role (e.g. Regional CFO, GCC)."},
            "justification": {"type": "string", "description": "Business justification for policy exception."},
            "amount": {"type": "number", "description": "Percentage or monetary exception amount."},
        },
        "required": ["action_type", "approver_role", "justification"],
    }

    async def execute(self, **kwargs: Any) -> Dict[str, Any]:
        approval_id = f"REQ{uuid.uuid4().hex[:7].upper()}"
        return {
            "status": "pending_approval",
            "approval_id": approval_id,
            "approver_role": kwargs.get("approver_role"),
            "action_type": kwargs.get("action_type"),
            "amount": kwargs.get("amount"),
            "requires_human_confirmation": True,
            "message": f"Approval request {approval_id} submitted to {kwargs.get('approver_role')}.",
        }
