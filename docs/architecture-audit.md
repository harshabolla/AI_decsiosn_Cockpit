# Opella AI Decision Cockpit — Master Architecture Audit

**Date**: 2026-10-02  
**Role**: Principal AI Architect + Senior Python Engineer + Data Engineer + Agentic AI Engineer + Security Engineer + Code Reviewer  
**Workspace**: `c:\Users\admin\Desktop\opella`  
**Evaluation Standard**: Reality-First / Zero Assumptions — A component is complete ONLY if it participates in the live runtime path.

---

## 1. Executive Summary & Verification Findings

An exhaustive, line-by-line inspection of all directories, runtime pipelines, and tests was conducted.
While the project has created foundational components (local DuckDB database, initial PII regex checks, Next.js dashboard shell), **major gaps exist between the claimed architecture and the actual source code**:

1. **Agent Architecture (Phase 2)**: Only `base.py`, `types.py`, `registry.py`, `security_agent.py`, `intent_agent.py`, and `semantic_agent.py` exist. Missing: `analytics_agent.py`, `rag_agent.py`, `guideline_agent.py`, `operations_agent.py`, `visualization_agent.py`, `reviewer_agent.py`, and `supervisor_agent.py`.
2. **LangGraph Pipeline (Phase 4)**: Currently runs 6 procedural step functions directly inside `langgraph_supervisor.py`. The actual agent classes are NOT invoked by LangGraph. The RAG, Guideline, Reviewer, and Operations nodes are omitted from the graph.
3. **Tool Architecture (Phase 5)**: `apps/backend/app/tools/` does NOT exist. Tool interfaces and tool registries are missing.
4. **Snowflake Warehouse Client (Phase 6)**: `apps/backend/app/data/` contains only `local_warehouse.py` (DuckDB). No abstract `WarehouseClient` exists, and no `SnowflakeWarehouseAdapter` with connection pooling, credentials management, or circuit breaker is implemented.
5. **Model Context Protocol (MCP) (Phase 7)**: MCP servers exist in `mcp/` as separate scripts (`snowflake_server`, `dbt_server`, `servicenow_server`), but the backend has ZERO MCP clients. No agent can call any MCP tool.
6. **RAG Architecture (Phase 8)**: `rag/documents/` contains only two static markdown files. There is no vector store, chunking engine, metadata filter, retriever, or reranker.
7. **Human-in-the-Loop Operations (Phase 11)**: No approval state machine exists in backend or frontend for ServiceNow incident creation or discounting override approvals.
8. **Reviewer / Guardrail (Phase 10)**: The reviewer node is completely missing. Numerical calculations and factual claims are unverified.
9. **Observability (Phase 12)**: The frontend only ever receives 6 SSE node transitions; 4 nodes remain permanently greyed out.

---

## 2. Component Audit Matrix

| Component | Claimed | Actually Implemented | Runtime Connected | Test Coverage | Architectural Gap |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Base Agent & Registry** | Reusable OOP Agent base class & dynamic registry | `BaseAgent`, `AgentRegistry` defined | ❌ Partially (Agents not wired to graph) | Unit test needed | Need all 8 specialized agents inheriting from `BaseAgent`. |
| **Specialized Agents** | 8 modular agents (Intent, Semantic, Analytics, RAG, Guideline, Operations, Viz, Reviewer) | 3 agents drafted in `app/agents/` | ❌ No (Graph uses procedural functions) | 0% | Create missing 6 agents, register them, and invoke them via Graph nodes. |
| **LangGraph Supervisor** | Multi-agent state graph orchestrating 10 nodes with conditional routing | Single file with 6 hardcoded step functions | ⚠️ Partial (6 steps only) | Eval script (5 cases) | Rewire Graph to invoke agents via `AgentRegistry` and add RAG, Guideline, Ops, Reviewer. |
| **Typed Shared State** | Formal typed state (`AgentState`) as communication contract | Comprehensive `AgentState` typed dict in `app/agents/types.py` | ⚠️ Partial | Partial | Migrate `CockpitState` in `langgraph_supervisor.py` to `AgentState`. |
| **Tool Architecture** | Controlled tool layer (`app/tools/`) with strict parameter schemas | Missing directory `app/tools/` | ❌ No | 0% | Create `app/tools/base.py`, `registry.py`, `snowflake_tools.py`, `servicenow_tools.py`, `rag_tools.py`. |
| **Warehouse Client & Snowflake** | Governed dual-mode warehouse (Snowflake / DuckDB) | DuckDB local demo adapter only | ⚠️ DuckDB Only | 1 unit test | Create `WarehouseClient` ABC, `SnowflakeWarehouseAdapter`, query timeout, and read-only checks. |
| **MCP Integration** | Live MCP client talking to Snowflake, dbt, ServiceNow | Standalone scripts in `mcp/` | ❌ Disconnected | 0% | Implement `MCPClient` in backend to execute tools against MCP servers. |
| **RAG Pipeline** | Vector store + chunking + metadata filtering + reranking | 2 markdown files in `rag/documents/` | ❌ No | 0% | Implement document chunker, metadata parser, ChromaDB / In-Memory vector store, and RAG agent. |
| **Guideline Engine** | Applicability rules, conflict detection, threshold checks | Static policy text | ❌ No | 0% | Build deterministic rule engine evaluating discount caps, brand margins, safety stock buffers. |
| **Reviewer & Guardrail** | Numerical verification, evidence auditing, hallucination check | None; summary LLM generates unverified text | ❌ No | 0% | Build `ReviewerAgent` verifying retrieved data against final assertions. |
| **Security & PII** | Multi-layer input/output DLP, prompt injection defense | Regex checks in `gateway.py` | ⚠️ Inbound Only | Basic regex tests | Add indirect prompt injection defense, output guardrails, PII tokenization/masking. |
| **ServiceNow / Approvals** | Human-in-the-loop action proposals & ServiceNow tickets | Standalone mock in `mcp/servicenow_server` | ❌ No | 0% | Build approval state machine (`proposed` → `pending_approval` → `executed`), UI approval card, audit trail. |
| **Observability & Trace** | Real-time SSE streaming of all 10 pipeline nodes | 6 nodes emitted via SSE | ⚠️ Partial | Manual verification | Emit SSE for all nodes: security, intent, semantic, analytics, rag, guideline, operations, reviewer, viz, summary. |
| **Model Router & Fallback** | Multi-provider router (OpenAI, Anthropic, Bedrock, Mock) | Hardcoded AsyncOpenAI with no fallback | ⚠️ OpenAI only | None | Add pluggable `LLMProvider` interface with offline deterministic fallback for test runs. |
| **Evaluation Suite** | 30+ golden evaluation cases across 8 domains | 5 cases in `golden_benchmark.json` | ✅ Yes | 5/5 passed | Expand to 30+ comprehensive golden evaluation cases covering security, RAG, finance, etc. |

---

## 3. Actual Runtime Path Trace (As Discovered)

```text
HTTP POST /api/chat/stream
  │
  ▼
FastAPI chat_stream() in app/api/chat.py
  │
  ▼
RequestTracer initialized (SSE event queue wired)
  │
  ▼
LangGraph get_graph().ainvoke(initial_state)
  │
  ├── [1] security_node: SecurityGateway.process(raw_input) [Regex PII & Injection]
  │        └─ If blocked: short-circuits directly to summary_node
  │
  ├── [2] intent_node: ModelRouter -> LLM (OpenAI) with prompts/intent/v1.yaml
  │        └─ Classifies intent into JSON; crashes if OPENAI_API_KEY missing
  │
  ├── [3] semantic_node: SemanticLayer.resolve_metric() & resolve_dimension()
  │        └─ Resolves metrics/dimensions from yaml catalogue
  │
  ├── [4] analytics_node: ModelRouter -> LLM (OpenAI) with prompts/sql/v1.yaml
  │        ├─ validate_sql() [Regex read-only check]
  │        └─ LocalWarehouseAdapter.execute_query() [In-Memory DuckDB]
  │
  ├── [5] visualization_node: viz_builder.py [Deterministic JSON chart spec]
  │        └─ Chooses bar/line/table based on dimensions
  │
  └── [6] summary_node: ModelRouter -> LLM (OpenAI)
           └─ Produces conversational summary text
  │
  ▼
FastAPI emits SSE events ("trace" + "response" + "done")
  │
  ▼
React UI (useChat hook) in apps/frontend/
  ├─ Updates message history
  ├─ Renders SQLPanel & ChartPanel
  └─ Updates ExecutionTrace (only 6 nodes ever turn green; 4 stay grey)
```

---

## 4. Remediation Architecture & Target Pipeline

The target architecture replaces procedural step functions with registered `BaseAgent` instances communicating through typed `AgentState`:

```text
[HTTP Request]
       │
       ▼
 [SecurityAgent]  ──(Blocked)──┐
       │                       │
       ▼                       │
  [IntentAgent]                │
       │                       │
       ▼                       │
    [Router]                   │
   ┌───┼───┐                   │
   │   │   │                   │
   ▼   │   ▼                   │
[Semantic] [RAGAgent]          │
   │   │   │                   │
   ▼   │   ▼                   │
[Analytics] [GuidelineAgent]   │
   │   │   │                   │
   │   ▼   │                   │
   │ [OperationsAgent]         │
   │   │   │                   │
   └───┼───┘                   │
       ▼                       │
[ReviewerAgent]                │
       │                       │
       ▼                       │
[VisualizationAgent]           │
       │                       │
       ▼                       │
 [SummaryAgent] ◄──────────────┘
       │
       ▼
 [OutputGuardrail]
       │
       ▼
[SSE Response Stream]
```

---

## 5. Sequential Execution Roadmap

- **Phase 2**: Complete Reusable Agent Architecture (`BaseAgent`, `AgentRegistry`, all 8 agents).
- **Phase 3**: Unify Typed Shared State (`AgentState`) across all agent inputs/outputs.
- **Phase 4**: Rebuild LangGraph Supervisor to route dynamically through all registered agents.
- **Phase 5**: Create controlled Tool Architecture (`app/tools/`).
- **Phase 6**: Build dual `WarehouseClient` (`SnowflakeWarehouseAdapter` + `DuckDBWarehouseAdapter`).
- **Phase 7**: Implement MCP Client connecting to Snowflake, dbt, and ServiceNow MCP servers.
- **Phase 8**: Implement in-memory vector store & RAG document retrieval engine.
- **Phase 9**: Implement multi-layer Security Gateway (PII masking, direct & indirect injection defense).
- **Phase 10**: Implement Reviewer Agent with numerical cross-verification.
- **Phase 11**: Implement ServiceNow approval workflow state machine and UI card.
- **Phase 12**: Wire 10-node Observability & SSE streaming.
- **Phase 13**: Verify Frontend Live Trace & approval interactions.
- **Phase 14**: Expand Unit, Integration, and Security Test Suites.
- **Phase 15**: Expand Evaluation Suite to 30+ golden benchmarks.
- **Phase 16**: Deliver Production Documentation and Readiness Report.
