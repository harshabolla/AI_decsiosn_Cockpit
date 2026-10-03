"""
ServiceNow MCP Server
Exposes tools for human-in-the-loop approval, incident creation,
and operational ticket workflows.
"""
from typing import Any, Dict
import structlog
import uuid
from datetime import datetime

logger = structlog.get_logger(__name__)

TOOLS = [
    {
        "name": "servicenow_create_incident",
        "description": "Create an automated incident ticket in ServiceNow for supply chain or data anomalies.",
        "parameters": {
            "type": "object",
            "properties": {
                "short_description": {"type": "string"},
                "urgency": {"type": "string", "enum": ["1 - High", "2 - Medium", "3 - Low"]},
                "assignment_group": {"type": "string"},
                "details": {"type": "string"}
            },
            "required": ["short_description", "urgency"]
        }
    },
    {
        "name": "servicenow_request_approval",
        "description": "Trigger an executive approval request (e.g. discount override > 10%).",
        "parameters": {
            "type": "object",
            "properties": {
                "action_type": {"type": "string"},
                "approver_role": {"type": "string"},
                "justification": {"type": "string"},
                "amount": {"type": "number"}
            },
            "required": ["action_type", "approver_role", "justification"]
        }
    }
]


async def handle_tool_call(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    logger.info("mcp_servicenow_call", tool=tool_name, args=arguments)
    if tool_name == "servicenow_create_incident":
        ticket_id = f"INC{uuid.uuid4().hex[:7].upper()}"
        return {
            "status": "created",
            "ticket_id": ticket_id,
            "urgency": arguments.get("urgency", "2 - Medium"),
            "assigned_to": arguments.get("assignment_group", "Supply Chain Ops"),
            "created_at": datetime.utcnow().isoformat(),
            "short_description": arguments.get("short_description")
        }
    elif tool_name == "servicenow_request_approval":
        approval_id = f"REQ{uuid.uuid4().hex[:7].upper()}"
        return {
            "status": "pending_approval",
            "approval_id": approval_id,
            "approver_role": arguments.get("approver_role"),
            "action_type": arguments.get("action_type"),
            "requires_human_confirmation": True
        }
    return {"error": f"Unknown tool: {tool_name}"}
