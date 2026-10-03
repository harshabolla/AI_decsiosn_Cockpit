"""
Comprehensive tests for newly added enterprise features:
- SQLPlanner & SQLGenerator services
- ConversationMemoryStore & memory API
- ModelRouter multi-provider abstraction
- Hybrid dense+sparse RAG retrieval
"""
import pytest
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.agents.types import AgentState, IntentResult, IntentType, Entity
from app.services.sql_planner import SQLPlanner, get_sql_planner
from app.services.sql_generator import SQLGenerator, get_sql_generator
from app.memory.store import ConversationMemoryStore, get_conversation_memory
from app.providers.router import get_model_router
from app.providers.types import LLMTask
from app.rag.vector_store import get_knowledge_store


@pytest.mark.asyncio
async def test_sql_planner():
    planner = get_sql_planner()
    state: AgentState = {
        "user_input": "Show net sales for Doliprane in France",
        "intent": IntentResult(
            intent_type=IntentType.ANALYTICS,
            metrics=["net_sales"],
            dimensions=["product", "region"],
            entities=[
                Entity(entity_type="product", name="Doliprane"),
                Entity(entity_type="region", name="France"),
            ],
        ),
    }

    plan = await planner.create_plan(state)
    assert plan is not None
    assert "fact_sales" in plan.tables
    assert any("dim_product" in t or "p.product_name" in c for t in plan.tables for c in plan.columns)
    assert len(plan.aggregations) > 0
    assert len(plan.assumptions) > 0


@pytest.mark.asyncio
async def test_sql_generator():
    planner = get_sql_planner()
    generator = get_sql_generator()

    state: AgentState = {
        "user_input": "Show sales by product",
        "intent": IntentResult(
            intent_type=IntentType.ANALYTICS,
            metrics=["net_sales"],
            dimensions=["product"],
        ),
    }

    plan = await planner.create_plan(state)
    sql, val_res = await generator.generate_and_validate(plan, state)

    assert sql.strip().upper().startswith("SELECT")
    assert val_res.valid is True
    assert val_res.is_read_only is True


@pytest.mark.asyncio
async def test_conversation_memory_store():
    mem = ConversationMemoryStore(max_turns_per_session=5)
    sid = "test-session-123"

    turn1 = await mem.add_turn(
        session_id=sid,
        user_input="What were the top selling products?",
        assistant_answer="Doliprane was #1 with $12M net sales.",
        intent_type="analytics",
        sql_executed="SELECT * FROM fact_sales",
    )
    assert turn1.turn_id is not None

    turn2 = await mem.add_turn(
        session_id=sid,
        user_input="What about in France?",
        assistant_answer="In France, Doliprane had $8M net sales.",
        intent_type="analytics",
    )
    assert turn2.turn_id is not None

    context = await mem.get_context_turns(sid, limit=5)
    assert len(context) == 2
    assert context[0].user_input == "What were the top selling products?"
    assert context[1].user_input == "What about in France?"

    sessions = await mem.list_sessions()
    assert any(s["session_id"] == sid for s in sessions)

    cleared = await mem.clear_session(sid)
    assert cleared is True
    assert await mem.get_session(sid) is None


@pytest.mark.asyncio
async def test_memory_api_endpoints():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Pre-seed a turn
        mem = get_conversation_memory()
        await mem.add_turn(
            session_id="api-test-session",
            user_input="Hello",
            assistant_answer="Hi, how can I help you?",
        )

        # List sessions
        res = await client.get("/api/memory/sessions")
        assert res.status_code == 200
        data = res.json()
        assert any(s["session_id"] == "api-test-session" for s in data)

        # Get session
        res_get = await client.get("/api/memory/sessions/api-test-session")
        assert res_get.status_code == 200
        sess_data = res_get.json()
        assert sess_data["session_id"] == "api-test-session"
        assert len(sess_data["turns"]) >= 1

        # Delete session
        res_del = await client.delete("/api/memory/sessions/api-test-session")
        assert res_del.status_code == 200
        assert res_del.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_providers_health_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/providers/health")
        assert res.status_code == 200
        data = res.json()
        assert "default_provider" in data
        assert "providers" in data
        assert "openai" in data["providers"]
        assert "anthropic" in data["providers"]
        assert "gemini" in data["providers"]


@pytest.mark.asyncio
async def test_hybrid_rag_search():
    store = get_knowledge_store()
    res = store.search(
        query="commercial discounting policy threshold",
        domain_filter="commercial",
        top_k=2,
    )
    assert len(res.chunks) > 0
    assert any("commercial" in c.domain for c in res.chunks)
    assert res.chunks[0].score > 0
