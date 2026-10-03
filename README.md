
# AI Decision Cockpit

> **Enterprise Multimodal AI & Data Engineering Platform**  
> Conversational analytics, governed text-to-SQL, multi-agent orchestration, and decision support for Commercial, Finance, and Supply Chain intelligence.

---

## 🌟 Overview

The ** AI Decision Cockpit** is an enterprise-grade AI and data platform designed to bridge executive decision-makers with complex enterprise data warehouses (Snowflake, Databricks, DuckDB) and unstructured organizational knowledge (RAG).

Rather than serving as a black-box chatbot, the Cockpit provides **full governance, transparency, and traceability** at every step:
- **Governed Semantic Layer**: Maps business questions to vetted definitions, dimensions, and metric formulas.
- **Auditable Text-to-SQL**: Generates, validates, and runs secure read-only SQL, with human-readable explanations and schema validation badges.
- **Interactive Visualizations**: Declarative chart specifications (bar, line, KPI, table) rendered natively via Recharts.
- **AI Execution Trace**: Real-time server-sent events (SSE) displaying multi-agent state progression with millisecond latency metrics.
- **Local Warehouse Demo Mode**: Ships with pre-loaded synthetic datasets for Doliprane, Essentiale, Buscopan, and Allegra, allowing immediate local evaluation without external cloud dependencies.

---

## 🏗️ Architecture

```
User Query (Text / Voice)
       │
       ▼
Next.js 14 Cockpit UI (Tailwind CSS, Recharts)
       │ (SSE Stream)
       ▼
FastAPI Gateway & Security Scrubber (PII Redaction, Prompt Injection Defense)
       │
       ▼
LangGraph Supervisor Workflow
 ├── Intent & Entity Extractor
 ├── Governed Semantic Layer Resolver
 ├── SQL Generator & Query Validator
 ├── Analytical Warehouse (DuckDB / Snowflake)
 ├── Knowledge RAG Agent (Guidelines & Policies)
 ├── Visualization Agent (Declarative Chart Specs)
 └── Reviewer & Guardrail Agent (Numerical Consistency Check)
       │
       ▼
Synthesized Answer + KPIs + Interactive Charts + SQL Viewer + Trace Pipeline
```

---

## 🚀 Quick Start

### Prerequisites
- Node.js 18+ & npm
- Python 3.11+
- (Optional) Docker & Docker Compose

### 1. Environment Setup

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Add your `OPENAI_API_KEY` (if testing LLM calls), or run with local warehouse adapter defaults.

### 2. Running Locally (Without Docker)

**Backend:**
```bash
cd apps/backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd apps/frontend
npm install
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) to access the Cockpit.

### 3. Running with Docker Compose

```bash
docker compose up --build
```
Both the FastAPI backend (`:8000`) and the Next.js frontend (`:3000`) will spin up automatically.

---

## 🧪 Testing

Run backend unit and integration test suite:
```bash
cd apps/backend
pytest tests/
```

---

## 📚 Documentation
- [Architecture & Technical Specifications](docs/architecture.md)
- [Prompts Registry](prompts/)
- [Semantic Layer Configuration](apps/backend/app/semantic/)
- [DBT Transformation Models](dbt/)
=======
# AI_decsiosn_Cockpit


