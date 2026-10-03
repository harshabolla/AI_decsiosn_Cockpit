"""
Intent Agent
============
Responsible exclusively for intent classification and entity extraction.
Does not generate SQL, query databases, or retrieve documents.
"""
from __future__ import annotations

import json
from typing import Any
import structlog

from app.agents.base import BaseAgent
from app.agents.types import AgentState, IntentResult, IntentType, Entity
from app.llm.model_router import get_model_router, LLMTask, ModelRouter
from app.llm.prompt_registry import get_prompt_registry, PromptRegistry

logger = structlog.get_logger(__name__)


class IntentAgent(BaseAgent[AgentState]):
    name = "intent"
    version = "1.0.0"

    def __init__(
        self,
        router: ModelRouter | None = None,
        registry: PromptRegistry | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.router = router or get_model_router()
        self.registry = registry or get_prompt_registry()

    def validate_input(self, state: AgentState) -> None:
        if "normalized_input" not in state and "user_input" not in state:
            raise ValueError("IntentAgent requires 'normalized_input' or 'user_input'.")

    async def process(self, state: AgentState) -> AgentState:
        text = state.get("normalized_input") or state.get("user_input", "")

        try:
            messages = self.registry.build_messages(
                "intent",
                {"question": text},
                version="v1",
            )
            resp = await self.router.complete(
                task=LLMTask.INTENT,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            data = json.loads(resp.content)
            intent = self._parse_llm_intent(data)

        except Exception as e:
            logger.warning("intent_llm_failed_using_deterministic_fallback", error=str(e))
            intent = self._deterministic_fallback(text)

        state["intent"] = intent
        state["entities"] = intent.entities
        return state

    def _parse_llm_intent(self, data: dict[str, Any]) -> IntentResult:
        intent_str = data.get("intent_type", "analytics").lower()
        try:
            intent_type = IntentType(intent_str)
        except ValueError:
            intent_type = IntentType.ANALYTICS

        entities_list: list[Entity] = []
        raw_entities = data.get("entities", {})
        if isinstance(raw_entities, dict):
            for etype, items in raw_entities.items():
                if isinstance(items, list):
                    for item in items:
                        entities_list.append(Entity(entity_type=etype, name=str(item)))

        return IntentResult(
            intent_type=intent_type,
            metrics=data.get("metrics", []),
            dimensions=data.get("dimensions", []),
            filters=data.get("filters", {}),
            entities=entities_list,
            confidence=float(data.get("confidence", 0.9)),
            requires_rag=bool(data.get("requires_rag", False)),
            requires_guidelines=bool(data.get("requires_guideline", False)),
            requires_operations=bool(data.get("requires_servicenow", False)),
            clarification_prompt=data.get("clarification_needed"),
        )

    def _deterministic_fallback(self, text: str) -> IntentResult:
        """Deterministic keyword parser ensuring zero-crash runtime."""
        lower = text.lower()

        # Check injection
        if any(w in lower for w in ["drop table", "ignore instructions", "bypass policy", "system prompt"]):
            return IntentResult(intent_type=IntentType.INJECTION_ATTEMPT, confidence=1.0)

        # Check operations / tickets
        if any(w in lower for w in ["incident", "ticket", "servicenow", "create incident", "approve"]):
            return IntentResult(
                intent_type=IntentType.OPERATIONS,
                requires_operations=True,
                confidence=0.9,
            )

        # Check knowledge / policy / guidelines
        if any(w in lower for w in ["policy", "guideline", "sop", "document", "contract", "rule"]):
            return IntentResult(
                intent_type=IntentType.RAG,
                requires_rag=True,
                requires_guidelines=True,
                confidence=0.88,
            )

        # Extract known entities & metrics
        metrics = []
        if any(w in lower for w in ["sales", "revenue", "turnover", "income"]):
            metrics.append("net_sales")
        if any(w in lower for w in ["gross", "invoice"]):
            metrics.append("gross_revenue")
        if any(w in lower for w in ["stock", "inventory", "on hand"]):
            metrics.append("stock_on_hand")
        if any(w in lower for w in ["days of supply", "dos", "supply"]):
            metrics.append("days_of_supply")
        if not metrics:
            metrics.append("net_sales")

        dimensions = []
        if any(w in lower for w in ["product", "brand", "doliprane", "buscopan", "allegra", "dulcolax", "mucosolvan"]):
            dimensions.append("product")
        if any(w in lower for w in ["country", "region", "market", "india", "france", "germany", "uk"]):
            dimensions.append("region")
        if any(w in lower for w in ["channel", "retail", "hospital", "online", "wholesale"]):
            dimensions.append("channel")
        if any(w in lower for w in ["month", "quarter", "year", "trend", "2024"]):
            dimensions.append("month")
        if not dimensions:
            dimensions = ["product"]

        # Entity extraction
        entities: list[Entity] = []
        for p in ["Doliprane", "Buscopan", "Allegra", "Dulcolax", "Mucosolvan"]:
            if p.lower() in lower:
                entities.append(Entity(entity_type="product", name=p))
        for r in ["India", "France", "Germany", "UK"]:
            if r.lower() in lower:
                entities.append(Entity(entity_type="region", name=r))

        return IntentResult(
            intent_type=IntentType.ANALYTICS,
            metrics=metrics,
            dimensions=dimensions,
            entities=entities,
            confidence=0.85,
            requires_rag=len(entities) > 0 and "decline" in lower,
            requires_guidelines="decline" in lower or "threshold" in lower,
        )

    def summarize_execution(self, state: AgentState) -> str:
        intent = state.get("intent")
        if not intent:
            return "Intent: Unknown"
        return f"Intent: {intent.intent_type.value} | Metrics: {intent.metrics} | Dimensions: {intent.dimensions}"
