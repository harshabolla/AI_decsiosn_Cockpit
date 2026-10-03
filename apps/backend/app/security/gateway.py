"""
Security Gateway — Phase 1
==========================
Pipeline:
  Authentication → Authorization → PII Detection → PII Transformation
  → Prompt Injection Detection → DLP → Policy Engine → ALLOW/BLOCK/SANITIZE

Phase 1 implements deterministic layers (regex PII, pattern injection detection).
LLM-based classification is an optional enhancement in Phase 2.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Literal

import structlog

logger = structlog.get_logger(__name__)

# ── PII Patterns ─────────────────────────────────────────────────────────────

_PII_PATTERNS: list[tuple[str, str, re.Pattern]] = [
    ("EMAIL", "EMAIL", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("PHONE", "PHONE", re.compile(r"\b(\+?[\d\s\-().]{7,15})\b")),
    ("PERSON", "PERSON", re.compile(
        r"\b(Mr\.|Mrs\.|Ms\.|Dr\.)?\s?[A-Z][a-z]{1,20}\s[A-Z][a-z]{1,20}\b"
    )),
    ("GOV_ID", "GOV_ID", re.compile(
        r"\b([A-Z]{5}[0-9]{4}[A-Z]{1}|[0-9]{3}-[0-9]{2}-[0-9]{4}|[0-9]{12})\b"
    )),
]

# ── Injection Patterns ────────────────────────────────────────────────────────

_INJECTION_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ignore_instruction", re.compile(
        r"\b(ignore|disregard|forget|override|bypass)\b.{0,30}\b(instruction|prompt|rule|policy|system|previous)\b",
        re.IGNORECASE,
    )),
    ("reveal_secret", re.compile(
        r"\b(reveal|show|print|display|output|return|expose)\b.{0,30}\b(system prompt|credentials|api key|secret|password|token)\b",
        re.IGNORECASE,
    )),
    ("destructive_sql_injection", re.compile(
        r"\b(drop\s+table|delete\s+from|truncate\s+table|alter\s+table|grant\s+all)\b",
        re.IGNORECASE,
    )),
    ("data_exfiltration", re.compile(
        r"\b(send\s+me\s+all|dump\s+all|exfiltrate|leak|steal)\b.{0,25}\b(data|customers|users|passwords|records)\b",
        re.IGNORECASE,
    )),
    ("role_impersonation", re.compile(
        r"\b(you are now|act as|pretend to be|roleplay as|you must now)\b",
        re.IGNORECASE,
    )),
    ("jailbreak", re.compile(
        r"\b(DAN|do anything now|developer mode|jailbreak|unrestricted)\b",
        re.IGNORECASE,
    )),
    ("bypass_policy", re.compile(
        r"\b(bypass|circumvent|evade|skirt)\b.{0,40}\b(guideline|rule|policy|compliance|governance|restriction|control)\b",
        re.IGNORECASE,
    )),
    ("leak_confidential", re.compile(
        r"\b(leak|disclose|expose|reveal|share|send)\b.{0,40}\b(confidential|proprietary|internal|margin|agreement|pricing|contract|secret)\b",
        re.IGNORECASE,
    )),
]

PolicyAction = Literal["allow", "block", "sanitize"]


@dataclass
class PIIEntity:
    entity_type: str
    original: str
    token: str
    start: int
    end: int


@dataclass
class PIIResult:
    detected: bool
    entities: list[PIIEntity] = field(default_factory=list)
    sanitized_text: str = ""
    token_map: dict[str, str] = field(default_factory=dict)  # token → original (never sent to LLM)


@dataclass
class InjectionResult:
    detected: bool
    risk: Literal["low", "medium", "high", "critical"]
    patterns_matched: list[str] = field(default_factory=list)
    action: PolicyAction = "allow"
    reason: str = ""


@dataclass
class SecurityResult:
    allowed: bool
    action: PolicyAction
    pii: PIIResult
    injection: InjectionResult
    sanitized_input: str
    policy_notes: list[str] = field(default_factory=list)


class SecurityGateway:
    """
    Deterministic security pipeline.
    LLMs are NOT the security boundary.
    """

    def __init__(self, pii_enabled: bool = True, injection_enabled: bool = True) -> None:
        self.pii_enabled = pii_enabled
        self.injection_enabled = injection_enabled
        self._counters: dict[str, int] = {}  # token counters per type

    def process(self, text: str) -> SecurityResult:
        """Run the full security pipeline on input text."""
        # Step 1: Injection check (before PII to catch injections first)
        injection = self._detect_injection(text)

        if injection.detected and injection.risk == "critical":
            return SecurityResult(
                allowed=False,
                action="block",
                pii=PIIResult(detected=False, sanitized_text=text),
                injection=injection,
                sanitized_input="[BLOCKED]",
                policy_notes=["Request blocked: critical prompt injection detected."],
            )

        # Step 2: PII detection and masking
        pii = self._detect_and_mask_pii(text) if self.pii_enabled else PIIResult(detected=False, sanitized_text=text)

        sanitized = pii.sanitized_text if self.pii_enabled else text

        policy_notes: list[str] = []
        if pii.detected:
            policy_notes.append(f"PII masked: {[e.entity_type for e in pii.entities]}")
        if injection.detected:
            policy_notes.append(f"Injection patterns detected (risk={injection.risk}): {injection.patterns_matched}")

        action: PolicyAction = "allow"
        if injection.detected and injection.risk in ("high", "critical"):
            action = "block"
        elif pii.detected:
            action = "sanitize"

        logger.info(
            "security_gateway",
            pii_detected=pii.detected,
            injection_detected=injection.detected,
            injection_risk=injection.risk,
            action=action,
        )

        return SecurityResult(
            allowed=action != "block",
            action=action,
            pii=pii,
            injection=injection,
            sanitized_input=sanitized,
            policy_notes=policy_notes,
        )

    def _detect_and_mask_pii(self, text: str) -> PIIResult:
        entities: list[PIIEntity] = []
        token_map: dict[str, str] = {}
        result_text = text

        for entity_type, prefix, pattern in _PII_PATTERNS:
            for match in pattern.finditer(text):
                original = match.group()
                counter = self._counters.get(prefix, 0) + 1
                self._counters[prefix] = counter
                token = f"[{prefix}_{counter:03d}]"
                entities.append(PIIEntity(
                    entity_type=entity_type,
                    original=original,
                    token=token,
                    start=match.start(),
                    end=match.end(),
                ))
                token_map[token] = original  # stored securely, not sent to LLM

        # Apply masking (replace originals in order to avoid offset issues)
        for entity in entities:
            result_text = result_text.replace(entity.original, entity.token, 1)

        return PIIResult(
            detected=len(entities) > 0,
            entities=entities,
            sanitized_text=result_text,
            token_map=token_map,
        )

    def _detect_injection(self, text: str) -> InjectionResult:
        if not self.injection_enabled:
            return InjectionResult(detected=False, risk="low", action="allow")

        matched: list[str] = []
        for name, pattern in _INJECTION_PATTERNS:
            if pattern.search(text):
                matched.append(name)

        if not matched:
            return InjectionResult(detected=False, risk="low", action="allow", reason="No injection patterns detected.")

        # Risk scoring
        if any(p in matched for p in [
            "reveal_secret", "jailbreak", "destructive_sql_injection",
            "data_exfiltration", "bypass_policy", "leak_confidential",
        ]):
            risk = "critical"
            action = "block"
        elif len(matched) >= 2 or "ignore_instruction" in matched:
            risk = "high"
            action = "block"
        else:
            risk = "medium"
            action = "sanitize"

        return InjectionResult(
            detected=True,
            risk=risk,
            patterns_matched=matched,
            action=action,
            reason=f"Matched injection patterns: {matched}",
        )


_gateway: SecurityGateway | None = None


def get_security_gateway() -> SecurityGateway:
    from app.core.config import settings
    global _gateway
    if _gateway is None:
        _gateway = SecurityGateway(
            pii_enabled=settings.PII_DETECTION_ENABLED,
            injection_enabled=settings.PROMPT_INJECTION_DETECTION_ENABLED,
        )
    return _gateway
