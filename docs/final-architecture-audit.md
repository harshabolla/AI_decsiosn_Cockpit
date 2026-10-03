# Final Architecture Audit — Opella AI Decision Cockpit

**Audited:** 2026-10-03  
**Methodology:** Every file read; runtime path traced; no assumptions.

---

## Audit Classification Key

| Label | Meaning |
|---|---|
| **REAL** | Participates in actual runtime path with no fabricated data |
| **PARTIAL** | Core structure exists but with critical gaps |
| **MOCK** | Returns hard-coded/fabricated data instead of real system calls |
| **DEMO** | Working demonstration but with embedded fake data |
| **NOT IMPLEMENTED** | File or feature entirely absent |

---

## 1. Overall Architecture

| Capability | Classification | Evidence |
|---|---|---|
| FastAPI backend | **REAL** | app/main.py, app/api/chat.py real HTTP server |
| SSE streaming | **REAL** | chat.py _stream_events() actual asyncio queue to SSE |
| LangGraph multi-agent graph | **REAL** | supervisor_agent.py 10-node StateGraph compiled |
| Next.js frontend | **REAL** | Production build passes; real SSE client |
| Docker Compose | **REAL** | docker-compose.yml wires frontend + backend |

---

## 2. Agent Architecture

| Agent | Classification | Evidence |
|---|---|---|
| BaseAgent (ABC) | **REAL** | agents/base.py execute/validate_input/process/metadata |
| SecurityAgent | **REAL** | security_agent.py calls SecurityGateway.process() |
| IntentAgent | **REAL** | intent_agent.py LLM call + deterministic fallback |
| SemanticAgent | **REAL** | semantic_agent.py calls SemanticLayer |
| AnalyticsAgent | **REAL** | analytics_agent.py LLM SQL gen + warehouse exec |
| RAGAgent | **REAL** | rag_agent.py calls EnterpriseKnowledgeStore.search() |
| GuidelineAgent | **REAL** | guideline_agent.py policy applicability |
| OperationsAgent | **REAL** | operations_agent.py ServiceNow tool calls |
| ReviewerAgent | **PARTIAL** | reviewer_agent.py LLM call but no structured schema output enforcement |
| VisualizationAgent | **REAL** | visualization_agent.py calls viz_builder deterministically |
| SummaryAgent | **REAL** | summary_agent.py LLM synthesis |
| SqlPlannerAgent | **NOT IMPLEMENTED** | No dedicated planner. Logic embedded in AnalyticsAgent |

---

## 3. State Architecture

| Feature | Classification | Evidence |
|---|---|---|
| Typed AgentState (TypedDict) | **REAL** | agents/types.py 25+ typed fields |
| Pydantic models for all sub-types | **REAL** | IntentResult, SQLPlan, QueryResult, etc. |
| Agents communicate via state only | **REAL** | Confirmed no agent calls another directly |
| ExecutionEvent recorded per agent | **REAL** | base.py:execute() appends events |
| Multi-turn conversation memory | **NOT IMPLEMENTED** | app/memory/__init__.py is empty |

---

## 4. LangGraph

| Feature | Classification | Evidence |
|---|---|---|
| StateGraph with 10 nodes | **REAL** | supervisor_agent.py build_supervisor_graph() |
| Conditional routing (security, intent) | **REAL** | route_after_security, route_after_intent |
| Analytics path (Semantic->Analytics->Guideline) | **REAL** | add_edge() calls confirmed |
| RAG path | **REAL** | rag -> guideline edge |
| Operations path | **REAL** | operations -> reviewer edge |
| Graph singleton | **REAL** | get_compiled_graph() |

---

## 5. SQL Generation

| Feature | Classification | Evidence |
|---|---|---|
| Intent to SQL pipeline | **PARTIAL** | No dedicated SQLPlanner; logic in AnalyticsAgent.process() |
| SQL generation via LLM | **REAL** | AnalyticsAgent calls model_router.complete(task=SQL) |
| Deterministic SQL fallback | **DEMO** | Keyword-based fallback with hard-coded queries |
| SQL validation | **REAL** | security/sql_validator.py sqlparse + forbidden keyword check |
| Structured SQL output schema | **PARTIAL** | Requests json_object but no Pydantic schema enforcement |
| Allowed table check | **PARTIAL** | Only 5 demo tables; warns but does not block |
| SQLPlanner service | **NOT IMPLEMENTED** | app/services/sql_planner.py does not exist |
| SQLGenerator service | **NOT IMPLEMENTED** | app/services/sql_generator.py does not exist |

---

## 6. Semantic Layer

| Feature | Classification | Evidence |
|---|---|---|
| Business-to-physical metric mapping | **REAL** | semantic_layer.py YAML with 5 metrics, 4 dimensions |
| Alias resolution | **REAL** | _aliases dict in YAML |
| Schema context builder | **REAL** | get_schema_context() builds SQL prompt context |
| Dynamic YAML loading from file | **NOT IMPLEMENTED** | YAML is hard-coded string |
| Snowflake Semantic Views | **NOT IMPLEMENTED** | Documented as Phase 2 in comments |

---

## 7. Snowflake

| Feature | Classification | Evidence |
|---|---|---|
| WarehouseClient interface | **REAL** | warehouse_client.py abstract base |
| SnowflakeWarehouseAdapter | **REAL** | snowflake_adapter.py real snowflake.connector calls |
| LocalWarehouseAdapter (DuckDB) | **REAL** | local_warehouse.py real DuckDB with in-memory data |
| Credential-aware status reporting | **REAL** | Returns UNAVAILABLE if no credentials; no fake success |
| Read-only enforcement in adapter | **REAL** | Forbidden keyword check before execution |
| make snowflake-test | **NOT IMPLEMENTED** | Makefile has no snowflake-test target |

---

## 8. MCP

| Feature | Classification | Evidence |
|---|---|---|
| MCPClient | **PARTIAL** | mcp/client.py Python module import NOT MCP protocol |
| Snowflake MCP server | **MOCK** | Returns hard-coded rows |
| ServiceNow MCP server | **MOCK** | Generates random UUID tickets |
| dbt MCP server | **MOCK** | Same pattern |
| Authorization enforcement in MCP | **PARTIAL** | Read-only check; no token/authz framework |
| Real MCP protocol (stdio/HTTP) | **NOT IMPLEMENTED** | Python direct import not MCP protocol |
| MCP tool call audit logging | **PARTIAL** | logger.info calls present no structured audit log |

---

## 9. RAG

| Feature | Classification | Evidence |
|---|---|---|
| Document loading (.md files) | **REAL** | vector_store.py:load_documents() reads from rag/documents/ |
| Markdown section chunking | **REAL** | _parse_and_chunk() splits on ## headers |
| Metadata tagging (domain, product) | **REAL** | Keyword-based extraction per chunk |
| Cosine TF similarity | **REAL** | _compute_vector() + _cosine_similarity() |
| Metadata pre-filtering | **REAL** | domain/product filters applied before scoring |
| Conflict detection | **REAL** | Multi-version detection in search() |
| Reranker | **NOT IMPLEMENTED** | No cross-encoder or LLM-based reranker |
| Real embeddings (dense vectors) | **NOT IMPLEMENTED** | TF bag-of-words only |
| FAISS / ChromaDB integration | **NOT IMPLEMENTED** | ChromaDB in requirements but not used |
| Indirect injection detection in docs | **NOT IMPLEMENTED** | No sanitization of retrieved chunks |

---

## 10. Security

| Feature | Classification | Evidence |
|---|---|---|
| SecurityGateway | **REAL** | security/gateway.py deterministic pipeline |
| PII detection (regex) | **REAL** | 4 PII patterns: EMAIL, PHONE, PERSON, GOV_ID |
| PII masking/tokenization | **REAL** | Tokens replace originals; map never sent to LLM |
| Direct prompt injection detection | **REAL** | 8 injection patterns with risk scoring |
| Critical injection blocking | **REAL** | risk=critical -> action=block -> pipeline halted |
| Indirect injection (RAG documents) | **NOT IMPLEMENTED** | Retrieved content not isolated |
| Output validation/DLP | **NOT IMPLEMENTED** | DLP_ENABLED config exists but no runtime |

---

## 11. Model Providers

| Provider | Classification | Evidence |
|---|---|---|
| OpenAI | **REAL** | model_router.py AsyncOpenAI client real SDK call |
| Anthropic | **NOT IMPLEMENTED** | ANTHROPIC_API_KEY in config but router only calls OpenAI |
| AWS Bedrock | **NOT IMPLEMENTED** | Config keys present no Bedrock SDK usage |
| Google Gemini | **NOT IMPLEMENTED** | No SDK; no provider file |
| xAI Grok | **NOT IMPLEMENTED** | No SDK; no provider file |
| app/providers/ directory | **NOT IMPLEMENTED** | Does not exist |
| Provider fallback chain | **NOT IMPLEMENTED** | Router retries same provider |
| Task-specific provider routing | **NOT IMPLEMENTED** | All tasks go to single provider |
| /api/providers/health endpoint | **NOT IMPLEMENTED** | No such endpoint |

---

## 12. Memory

| Feature | Classification | Evidence |
|---|---|---|
| ConversationMemory | **NOT IMPLEMENTED** | app/memory/__init__.py is empty |
| Context carry-over (multi-turn) | **NOT IMPLEMENTED** | Each request starts fresh state |

---

## 13. Observability

| Feature | Classification | Evidence |
|---|---|---|
| RequestTracer | **REAL** | observability/tracer.py per-request trace with events |
| trace_id per request | **REAL** | 8-char UUID assigned at request start |
| Agent-level duration tracking | **REAL** | node_start/success/failed with perf_counter |
| SSE streaming of trace events | **REAL** | Callback -> queue -> SSE |
| Structured logging (structlog) | **REAL** | All modules use structlog.get_logger() |
| OpenTelemetry / distributed tracing | **NOT IMPLEMENTED** | No OTEL spans |
| Token usage tracking | **PARTIAL** | LLMResponse.usage captured but not aggregated |

---

## 14. Testing

| Test File | Classification | Coverage |
|---|---|---|
| test_health.py | **REAL** | Basic health endpoint |
| test_agents.py | **REAL** | Unit tests for agent logic |
| test_pipeline_e2e.py | **REAL** | Full SSE pipeline, approval workflow |
| test_security_deep.py | **REAL** | Injection, PII, policy tests |
| test_semantic_layer.py | **REAL** | Metric/dimension resolution |
| test_tools_and_mcp.py | **REAL** | MCP tool schema and calls |
| test_local_warehouse.py | **REAL** | DuckDB execution |
| Provider unit tests | **NOT IMPLEMENTED** | No tests for Anthropic, Gemini, Grok, Bedrock |
| Routing/fallback tests | **NOT IMPLEMENTED** | |
| Indirect injection tests | **NOT IMPLEMENTED** | |

---

## 15. Evaluation Dataset

| Feature | Classification | Evidence |
|---|---|---|
| Golden benchmark | **DEMO** | Only 5 cases |
| Coverage categories | **PARTIAL** | Missing: PII, ambiguous, multi-turn, visualization |
| Groundedness scoring | **NOT IMPLEMENTED** | |

---

## 16. Production Gaps Summary

### CRITICAL
1. Multi-model provider architecture: only OpenAI works
2. Provider fallback chain: single provider no resilience
3. SQL Planner/Generator: no intermediate plan, SQL from intent directly
4. Indirect prompt injection: RAG content not isolated
5. Multi-turn conversation memory: every request fresh
6. Real embeddings for RAG: TF bag-of-words only

### HIGH
7. MCP is not MCP protocol: direct Python import
8. Provider health endpoint missing
9. DLP output validation: config flag only no runtime
10. ServiceNow real adapter: mock only
11. Evaluation dataset: 5 cases insufficient

### MEDIUM
12. SQLPlanner service not separate from agent
13. Reranker missing from RAG pipeline
14. Voice/multimodal abstraction not scaffolded
15. dbt not connected to real database
