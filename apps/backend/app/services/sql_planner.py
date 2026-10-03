"""
SQL Planner — Analytical Query Planning Service
===============================================
Decouples query intent interpretation and relational schema planning
from SQL syntax generation.

Responsibilities:
  - Resolves required star-schema tables and join paths
  - Maps metrics and dimensions to schema expressions
  - Ingests entity filters (regions, products, dates)
  - Formulates structured SQLPlan with explicit assumptions
"""
from __future__ import annotations

import json
from typing import Any, Dict, List, Optional
import structlog

from app.agents.types import AgentState, SQLPlan, IntentResult
from app.providers.router import ModelRouter, get_model_router
from app.providers.types import LLMTask

logger = structlog.get_logger(__name__)


# Known star-schema relationships in Opella Data Warehouse
JOIN_PATHS: Dict[str, Dict[str, str]] = {
    "dim_product": "ON fact_sales.product_key = dim_product.product_key",
    "dim_region": "ON fact_sales.region_key = dim_region.region_key",
    "dim_date": "ON fact_sales.date_key = dim_date.date_key",
    "fact_inventory_product": "ON fact_inventory.product_key = dim_product.product_key",
    "fact_inventory_region": "ON fact_inventory.region_key = dim_region.region_key",
}


class SQLPlanner:
    """Analytical planner generating relational query plans from intent and semantics."""

    def __init__(self, router: Optional[ModelRouter] = None) -> None:
        self.router = router or get_model_router()

    async def create_plan(self, state: AgentState) -> SQLPlan:
        """
        Produce a structured SQLPlan.
        Attempts LLM-assisted planning first, falling back to deterministic planning.
        """
        intent = state.get("intent")
        sem_ctx = state.get("semantic_context")
        user_input = state.get("user_input", "")

        try:
            plan = await self._plan_via_llm(user_input, intent, sem_ctx)
            if plan:
                logger.info("sql_planner_llm_success", tables=plan.tables)
                return plan
        except Exception as e:
            logger.warning("sql_planner_llm_fallback", error=str(e))

        plan = self._deterministic_plan(state)
        logger.info("sql_planner_deterministic_plan_built", tables=plan.tables)
        return plan

    async def _plan_via_llm(
        self,
        question: str,
        intent: Optional[IntentResult],
        sem_ctx: Any,
    ) -> Optional[SQLPlan]:
        intent_info = intent.model_dump() if intent else {}
        schema_context = getattr(sem_ctx, "schema_context", "") if sem_ctx else ""

        system_msg = (
            "You are an expert Data Warehouse Architect and SQL Planner for Opella Healthcare. "
            "Given a question and warehouse schema, produce a JSON object with: "
            "tables (list[str]), columns (list[str]), filters (list[str]), "
            "aggregations (list[str]), and assumptions (list[str]). "
            "Only return valid JSON."
        )
        user_msg = (
            f"Question: {question}\n"
            f"Schema Context:\n{schema_context}\n"
            f"Intent: {json.dumps(intent_info)}"
        )

        resp = await self.router.generate(
            task=LLMTask.SQL_PLAN,
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=512,
        )

        data = json.loads(resp.content)
        if "tables" in data and isinstance(data["tables"], list):
            return SQLPlan(
                tables=data.get("tables", ["fact_sales"]),
                columns=data.get("columns", ["product_name", "net_sales"]),
                filters=data.get("filters", []),
                aggregations=data.get("aggregations", ["SUM(net_sales)"]),
                assumptions=data.get("assumptions", ["Aggregated from warehouse"]),
            )
        return None

    def _deterministic_plan(self, state: AgentState) -> SQLPlan:
        """Deterministic rule-based planner guaranteeing 100% offline reliability."""
        intent = state.get("intent")
        q = state.get("user_input", "").lower()

        metrics = intent.metrics if intent and intent.metrics else ["net_sales"]
        dims = intent.dimensions if intent and intent.dimensions else ["product"]
        entities = intent.entities if intent and intent.entities else []

        tables = ["fact_sales"]
        columns: List[str] = []
        filters: List[str] = []
        aggregations: List[str] = []
        assumptions: List[str] = []

        # Check inventory domain
        if any(w in q for w in ["stock", "inventory", "days of supply", "dos", "on hand"]):
            tables = ["fact_inventory", "dim_product", "dim_region"]
            columns = ["product_name", "region_name", "stock_on_hand", "days_of_supply"]
            assumptions.append("Queried latest inventory snapshot by SKU and distribution center")
            return SQLPlan(
                tables=tables,
                columns=columns,
                filters=filters,
                aggregations=["AVG(days_of_supply)", "SUM(stock_on_hand)"],
                assumptions=assumptions,
            )

        # Dimension mapping
        if "product" in dims or any(e.entity_type == "product" for e in entities) or any(
            p in q for p in ["doliprane", "buscopan", "allegra", "dulcolax", "mucosolvan"]
        ):
            if "dim_product" not in tables:
                tables.append("dim_product")
            columns.append("p.product_name")

        if "region" in dims or any(e.entity_type == "region" for e in entities) or any(
            r in q for r in ["india", "france", "germany", "uk"]
        ):
            if "dim_region" not in tables:
                tables.append("dim_region")
            columns.append("r.region_name")

        if "month" in dims or any(w in q for w in ["month", "trend", "quarter", "year", "2024"]):
            if "dim_date" not in tables:
                tables.append("dim_date")
            columns.append("d.month_name")

        if "channel" in dims or "channel" in q:
            columns.append("s.channel")

        # Entity filters
        for e in entities:
            if e.entity_type == "product":
                filters.append(f"LOWER(p.product_name) = '{e.name.lower()}'")
            elif e.entity_type == "region":
                filters.append(f"LOWER(r.region_name) = '{e.name.lower()}'")

        if "india" in q and not any("india" in f for f in filters):
            filters.append("LOWER(r.region_name) = 'india'")
            if "dim_region" not in tables:
                tables.append("dim_region")

        if "france" in q and not any("france" in f for f in filters):
            filters.append("LOWER(r.region_name) = 'france'")
            if "dim_region" not in tables:
                tables.append("dim_region")

        # Metrics & Aggregations
        if "gross_revenue" in metrics or "gross" in q:
            aggregations.append("SUM(s.gross_revenue) AS total_gross_revenue")
        if "net_sales" in metrics or not aggregations:
            aggregations.append("SUM(s.net_sales) AS total_net_sales")

        assumptions.append("Read-only star-schema aggregation with governed metric formulas")

        return SQLPlan(
            tables=tables,
            columns=columns or ["p.product_name"],
            filters=filters,
            aggregations=aggregations,
            assumptions=assumptions,
        )


_sql_planner: Optional[SQLPlanner] = None


def get_sql_planner() -> SQLPlanner:
    global _sql_planner
    if _sql_planner is None:
        _sql_planner = SQLPlanner()
    return _sql_planner
