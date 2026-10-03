"""
Security Agent
==============
Responsible for input sanitization, PII detection/masking, and prompt injection defense.
Deterministic security boundaries ensure LLMs are not the security deciders.
"""
from __future__ import annotations

from typing import Any
from app.agents.base import BaseAgent
from app.agents.types import (
    AgentState, SecurityResult, SecurityAction, RiskLevel, PIIResult, InjectionResult
)
from app.security.gateway import get_security_gateway


class SecurityAgent(BaseAgent[AgentState]):
    name = "security"
    version = "1.0.0"

    def __init__(self, security_gateway: Any = None, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.gateway = security_gateway or get_security_gateway()

    def validate_input(self, state: AgentState) -> None:
        if "user_input" not in state or not state["user_input"]:
            raise ValueError("SecurityAgent requires 'user_input' in state.")

    async def process(self, state: AgentState) -> AgentState:
        raw_input = state["user_input"]
        res = self.gateway.process(raw_input)

        sec_result = SecurityResult(
            allowed=res.allowed,
            action=SecurityAction(res.action),
            pii=PIIResult(
                detected=res.pii.detected,
                sanitized_text=res.pii.sanitized_text,
                token_map=res.pii.token_map,
            ),
            injection=InjectionResult(
                detected=res.injection.detected,
                risk=RiskLevel(res.injection.risk),
                patterns_matched=res.injection.patterns_matched,
                action=SecurityAction(res.injection.action),
                reason=res.injection.reason,
            ),
            sanitized_input=res.sanitized_input,
            policy_notes=res.policy_notes,
        )

        state["security_result"] = sec_result
        state["normalized_input"] = res.sanitized_input

        if not sec_result.allowed:
            state["warnings"] = state.get("warnings", []) + [
                f"Security policy triggered: {sec_result.injection.reason or 'Unauthorized input pattern'}"
            ]

        return state

    def summarize_execution(self, state: AgentState) -> str:
        res = state.get("security_result")
        if not res or not res.allowed:
            return "Security Gateway: Request blocked by security policy."
        pii_str = f"PII={'detected' if res.pii.detected else 'none'}"
        inj_str = f"Injection={res.injection.risk.value}"
        return f"Security Gateway: Allowed ({pii_str}, {inj_str})"
