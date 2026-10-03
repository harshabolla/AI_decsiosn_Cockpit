"""
Analytics Agent
===============
Responsible for analytical planning, SQL generation, validation, and query execution.
Enforces read-only execution against Snowflake / DuckDB via WarehouseClient.
"""
from __future__ import annotations

import json
from typing import Any
import structlog

from app.agents.base import BaseAgent
from app.agents.types import (
    AgentState, SQLPlan, SQLValidationResult, QueryResult, Evidence
)
from app.data import get_warehouse_client, WarehouseClient
from app.llm.model_router import get_model_router, ModelRouter, LLMTask
from app.llm.prompt_registry import get_prompt_registry, PromptRegistry
from app.security.sql_validator import validate_sql
from app.services.sql_planner import SQLPlanner, get_sql_planner
from app.services.sql_generator import SQLGenerator, get_sql_generator

logger = structlog.get_logger(__name__)


class AnalyticsAgent(BaseAgent[AgentState]):
    name = "analytics"
    version = "1.0.0"

    def __init__(
        self,
        warehouse: WarehouseClient | None = None,
        router: ModelRouter | None = None,
        registry: PromptRegistry | None = None,
        planner: SQLPlanner | None = None,
        generator: SQLGenerator | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self.warehouse = warehouse or get_warehouse_client()
        self.router = router or get_model_router()
        self.registry = registry or get_prompt_registry()
        self.planner = planner or get_sql_planner()
        self.generator = generator or get_sql_generator()

    def validate_input(self, state: AgentState) -> None:
        if "semantic_context" not in state and "intent" not in state:
            raise ValueError("AnalyticsAgent requires 'semantic_context' or 'intent' in state.")

    async def process(self, state: AgentState) -> AgentState:
        # 1. Analytical Query Planning
        plan = await self.planner.create_plan(state)
        state["sql_plan"] = plan

        # 2. Governed Query Generation & Strict Validation
        sql, val_res = await self.generator.generate_and_validate(plan, state)
        state["generated_sql"] = sql
        state["sql_validation"] = val_res

        if not val_res.valid:
            state["warnings"] = state.get("warnings", []) + [f"SQL validation error: {val_res.errors}"]
            state["query_result"] = QueryResult(error="; ".join(val_res.errors))
            return state

        # 3. Warehouse Execution
        try:
            exec_res = await self.warehouse.execute_query(sql, max_rows=1000)
            q_res = QueryResult(
                columns=exec_res.get("columns", []),
                rows=exec_res.get("rows", []),
                row_count=exec_res.get("row_count", 0),
                execution_time_ms=exec_res.get("execution_time_ms", 0.0),
                adapter=exec_res.get("adapter", "LOCAL_DEMO"),
            )
            state["query_result"] = q_res

            # Record Evidence
            evidence = state.get("evidence") or []
            evidence.append(
                Evidence(
                    source_type="snowflake",
                    source_name=f"Analytical Warehouse ({q_res.adapter})",
                    summary=f"Query returned {q_res.row_count} rows in {q_res.execution_time_ms:.1f}ms",
                    citation=f"Tables: {', '.join(state['sql_plan'].tables or ['fact_sales'])}",
                )
            )
            state["evidence"] = evidence

        except Exception as e:
            logger.error("warehouse_query_execution_error", error=str(e))
            state["query_result"] = QueryResult(error=str(e))
            state["warnings"] = state.get("warnings", []) + [f"Warehouse execution failed: {str(e)}"]

        return state

    def _build_deterministic_sql(self, state: AgentState) -> str:
        intent = state.get("intent")
        metrics = intent.metrics if intent and intent.metrics else ["net_sales"]
        dims = intent.dimensions if intent and intent.dimensions else ["product"]
        q = state.get("user_input", "").lower()

        # India sales decline query
        if "india" in q and "product" in q:
            return (
                "SELECT p.product_name, SUM(s.net_sales) AS total_net_sales "
                "FROM fact_sales s "
                "JOIN dim_product p ON s.product_key = p.product_key "
                "JOIN dim_region r ON s.region_key = r.region_key "
                "WHERE LOWER(r.region_name) = 'india' "
                "GROUP BY p.product_name ORDER BY total_net_sales ASC LIMIT 10;"
            )
        if "india" in q:
            return (
                "SELECT d.month_name, SUM(s.net_sales) AS total_net_sales "
                "FROM fact_sales s "
                "JOIN dim_region r ON s.region_key = r.region_key "
                "JOIN dim_date d ON s.date_key = d.date_key "
                "WHERE LOWER(r.region_name) = 'india' "
                "GROUP BY d.month_name, d.month ORDER BY d.month ASC;"
            )
        if "stock" in q or "days of supply" in q or "dos" in q:
            return (
                "SELECT p.product_name, r.region_name, i.stock_on_hand, i.days_of_supply "
                "FROM fact_inventory i "
                "JOIN dim_product p ON i.product_key = p.product_key "
                "JOIN dim_region r ON i.region_key = r.region_key "
                "WHERE LOWER(p.product_name) LIKE '%doliprane%' OR LOWER(r.region_name) LIKE '%france%' "
                "LIMIT 10;"
            )
        if "gross" in q or "channel" in q:
            return (
                "SELECT s.channel, SUM(s.gross_revenue) AS total_gross_revenue, SUM(s.net_sales) AS total_net_sales "
                "FROM fact_sales s "
                "GROUP BY s.channel ORDER BY total_net_sales DESC;"
            )
        return (
            "SELECT p.product_name, SUM(s.net_sales) AS total_net_sales "
            "FROM fact_sales s JOIN dim_product p ON s.product_key = p.product_key "
            "GROUP BY p.product_name ORDER BY total_net_sales DESC LIMIT 10;"
        )

    def summarize_execution(self, state: AgentState) -> str:
        q_res = state.get("query_result")
        if not q_res or q_res.error:
            return f"Analytics: Execution failed ({q_res.error if q_res else 'No result'})"
        return f"Analytics: Returned {q_res.row_count} rows ({q_res.execution_time_ms:.1f}ms) via {q_res.adapter}"
