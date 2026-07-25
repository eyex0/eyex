# EyeX Technologies — Enterprise Pilot Documentation

## Table of Contents

1. [Product Overview](#product-overview)
2. [Architecture](#architecture)
3. [Core Features](#core-features)
4. [AI Executive Team](#ai-executive-team)
5. [Enterprise API Reference](#enterprise-api-reference)
6. [Data Connectors](#data-connectors)
7. [Deployment Guide](#deployment-guide)
8. [Customer Demo Script](#customer-demo-script)

---

## Product Overview

EyeX Technologies is an **AI-powered enterprise decision intelligence platform** that acts as a virtual executive team. It analyzes company data, detects risks and opportunities, and produces executive-level strategic recommendations — all through natural language interaction.

**Target customers:** Startups and scale-ups needing fractional executive analysis without hiring full-time C-suite.

### Key Differentiators

- **Multi-agent AI executive team** (CEO, CFO, COO, Risk) that collaborates through LangGraph
- **Company memory system** with vector embeddings and knowledge graph relationships
- **Proactive intelligence** that automatically detects risks and opportunities
- **Enterprise data isolation** per organization
- **Multi-source data connectors** for files, APIs, and databases

---

## Architecture

### System Overview

```
┌──────────────────────────────────────────────────────────┐
│                    Frontend (React/Vite)                   │
│  Intelligence Hub · Enterprise Dashboard · Data Sources    │
└────────────────────────┬─────────────────────────────────┘
                         │ HTTP / WebSocket
┌────────────────────────▼─────────────────────────────────┐
│                    API Layer (FastAPI)                     │
│  /api/v1/enterprise · /api/v1/intelligence · /api/v1/*    │
└────────────────────────┬─────────────────────────────────┘
                         │
┌────────────────────────▼─────────────────────────────────┐
│                  LangGraph Agent System                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Supervisor│  │   CEO    │  │   CFO    │  │   COO    │  │
│  │  Router   │→ │  Agent   │→ │  Agent   │→ │  Agent   │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│                                   │                       │
│                ┌──────────┐      ▼                       │
│                │   Risk   │  ┌──────────┐                │
│                │  Agent   │← │ Responder│                │
│                └──────────┘  └──────────┘                │
│                                                           │
│  Also: Analyst → Strategist → Decision (Intelligence)     │
│        Planner → Researcher → Coder → ...  (Engineering)  │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                   Services Layer                          │
│  ┌─────────────┐  ┌────────────┐  ┌────────────────┐    │
│  │  Proactive   │  │ Connectors │  │  Reliability    │    │
│  │ Intelligence │  │  Registry  │  │   Manager       │    │
│  └─────────────┘  └────────────┘  └────────────────┘    │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│                    Data Layer                              │
│  ┌──────────┐  ┌──────────────┐  ┌──────────────────┐    │
│  │PostgreSQL│  │    Redis     │  │ Vector Memory    │    │
│  │  (持久)  │  │  (短时存储)   │  │ (语义搜索)        │    │
│  └──────────┘  └──────────────┘  └──────────────────┘    │
│  ┌──────────────────────────────────────────────────┐    │
│  │         Knowledge Graph (company context)        │    │
│  └──────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────┘
```

### Agent Pipeline Flow

```
                   ┌──────────────┐
                   │  Supervisor  │
                   └──────┬───────┘
                          │
        ┌─────────────────┼────────────────────┐
        │                 │                    │
   ┌────▼────┐     ┌──────▼──────┐     ┌──────▼──────┐
   │ Executive│    │ Intelligence│     │ Engineering │
   │ Pipeline │    │  Pipeline   │     │  Pipeline   │
   └────┬────┘    └──────┬──────┘     └──────┬──────┘
        │                │                    │
   ┌────▼────┐     ┌─────▼─────┐       ┌─────▼──────┐
   │   CEO   │     │  Analyst   │       │  Planner    │
   └────┬────┘     └─────┬─────┘       └─────┬──────┘
        │                │                    │
   ┌────▼────┐     ┌─────▼─────┐       ┌─────▼──────┐
   │   CFO   │     │ Strategist│       │ Researcher  │
   └────┬────┘     └─────┬─────┘       └─────┬──────┘
        │                │                    │
   ┌────▼────┐     ┌─────▼─────┐       ┌─────▼──────┐
   │   COO   │     │  Decision │       │   Coder     │
   └────┬────┘     └─────┬─────┘       └─────┬──────┘
        │                │              ┌─────┴──────┐
   ┌────▼────┐     ┌─────▼─────┐       │            │
   │  Risk   │     │ Responder │   ┌───▼──┐    ┌───▼──┐
   └────┬────┘     └───────────┘   │Review│   │Tester│
        │                          └───┬──┘    └───┬──┘
   ┌────▼────┐                          │           │
   │Responder│                     ┌────▼────┐      │
   └─────────┘                     │Quality  │◄─────┘
                                   │  Gate   │
                                   └────┬────┘
                                   ┌────▼────┐
                                   │Document.│
                                   └────┬────┘
                                   ┌────▼────┐
                                   │ DevOps  │
                                   └────┬────┘
                                   ┌────▼────┐
                                   │Responder│
                                   └─────────┘
```

---

## Core Features

### 1. Company Intelligence Core

- **vector_memory.py** — Sentence-transformer based semantic search across company data
- **knowledge_graph.py** — Typed, relation-weighted graph with 12 relationship types
- **Enhanced PersistentMemory** — 5-layer architecture with org-scoped access

### 2. Enterprise Workspace

- Organization-scoped data isolation (org_id on every record)
- Organization knowledge store (`OrganizationKnowledge` model)
- Proactive alerts (`ProactiveAlert` model)
- Per-organization AI memory separation

### 3. AI Executive Team

| Agent          | Role                   | Key Outputs                                                                    |
| -------------- | ---------------------- | ------------------------------------------------------------------------------ |
| **CEO Agent**  | Strategic vision       | Vision, priorities, resource allocation, growth initiatives                    |
| **CFO Agent**  | Financial analysis     | Revenue analysis, cost optimization, cash flow insights, investment priorities |
| **COO Agent**  | Operational excellence | Process improvements, scalability, resource optimization, team structure       |
| **Risk Agent** | Risk management        | Risk scoring, compliance gaps, mitigation strategies, early warnings           |

### 4. Proactive Intelligence

- Automatic metric monitoring (revenue, cash, churn, growth)
- Risk detection with severity scoring
- Opportunity detection with confidence scoring
- Knowledge gap analysis

### 5. Data Connectors

| Connector   | Type     | Description                                  |
| ----------- | -------- | -------------------------------------------- |
| File Upload | file     | CSV, JSON, TXT, MD with chunking             |
| REST API    | api      | Generic HTTP connector with auth headers     |
| Database    | database | SQLAlchemy-based (PostgreSQL, MySQL, SQLite) |

### 6. Reliability System

- Exponential backoff retry (up to 3 attempts)
- Daily rotating log files
- Execution record tracking (success/fail/retry)
- Performance monitoring (avg duration, success rate)

---

## Enterprise API Reference

### Executive Team

```http
POST /api/v1/enterprise/execute-team
Content-Type: application/x-www-form-urlencoded

query=Analyze our company direction and provide executive recommendations
context=Revenue: $5M, Team: 25 people, Market: B2B SaaS
org_id=company_abc
```

**Response:**

```json
{
  "status": "completed",
  "ceo": {
    "strategic_vision": "Focus on enterprise segment expansion...",
    "key_priorities": ["Enterprise sales hiring", "Product scalability", "Customer success automation"],
    "confidence_score": 0.85
  },
  "cfo": {
    "financial_health_assessment": "Strong revenue growth with need for cost optimization...",
    "cost_optimization": ["Reduce cloud infrastructure costs", "Optimize SaaS subscriptions"]
  },
  "coo": {
    "operational_efficiency": "Good but scaling challenges ahead...",
    "process_improvements": ["Automate onboarding", "Implement OKR tracking"]
  },
  "risk": {
    "overall_risk_score": 0.35,
    "identified_risks": [
      {"severity": "high", "description": "Customer concentration risk"},
      {"severity": "medium", "description": "Talent retention in competitive market"}
    ],
    "early_warnings": ["Cash burn rate accelerating"]
  },
  "steps": [...]
}
```

### Proactive Intelligence

```http
GET /api/v1/enterprise/proactive-insights/{org_id}
```

**Response:**

```json
{
  "total": 5,
  "by_type": {"risk": 2, "opportunity": 1, "recommendation": 2},
  "by_severity": {"critical": 0, "high": 1, "medium": 2, "low": 2},
  "critical_count": 0,
  "high_count": 1,
  "insights": [...]
}
```

### Data Connectors

```http
POST /api/v1/enterprise/connectors/file/fetch
Content-Type: application/x-www-form-urlencoded

source=financials.csv
org_id=company_abc
```

```http
GET /api/v1/enterprise/connectors
```

### Knowledge Graph

```http
GET /api/v1/enterprise/knowledge-graph/{org_id}
```

### Vector Memory Search

```http
GET /api/v1/enterprise/vector-memory/search/{org_id}?query=revenue+growth+2024&top_k=5
```

---

## Data Connectors Guide

### File Upload

Upload CSV, JSON, TXT, or Markdown files. The system automatically:

1. Parses structured formats (CSV → rows, JSON → formatted)
2. Chunks text into 500-word segments
3. Stores chunks in vector memory for semantic search
4. Creates knowledge graph nodes for each document

### API Connector

Connect to any REST API:

```python
POST /api/v1/enterprise/connectors/api/fetch
source=https://api.eyex.tech/v1/metrics
headers={"Authorization": "Bearer token123"}
org_id=company_abc
```

### Database Connector

Connect to business databases using SQLAlchemy connection strings:

```python
POST /api/v1/enterprise/connectors/database/fetch
source=postgresql://user:pass@host:5432/dbname
query=SELECT * FROM revenue WHERE year = 2024
org_id=company_abc
```

---

## Deployment Guide

### Prerequisites

- Python 3.12+
- PostgreSQL 16+
- Redis 7+
- Node.js 20+ (for frontend)

### Backend Setup

```bash
cd eyex-backend
pip install -r requirements.txt
# Configure .env with database URLs
python -m app.main
# API at http://localhost:8000
# Swagger docs at http://localhost:8000/docs
```

### Environment Variables

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/eyex
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4
SECRET_KEY=your-secret-key
```

### Frontend Setup

```bash
npm install
npm run dev
# Dashboard at http://localhost:5173
```

### Testing

```bash
cd eyex-backend
python -m pytest tests/ -q
# Expected: 201+ tests passing
```

---

## Customer Demo Script

### Demo Flow (15 minutes)

**1. Introduction (2 min)**
"EyeX is an AI executive team that analyzes your company data and provides C-suite level recommendations — without hiring a full executive team."

**2. Company Knowledge Upload (3 min)**

- Upload a CSV with company metrics
- Add knowledge facts: "Annual revenue: $5M", "Team size: 25", "Churn rate: 8%"
- Show knowledge graph building

**3. Executive Team Analysis (5 min)**

- Query: "Analyze our company and provide executive recommendations"
- Watch the LangGraph pipeline sequentially execute CEO → CFO → COO → Risk
- Show each agent's structured output
- Highlight the risk score and early warnings

**4. Proactive Intelligence (2 min)**

- Navigate to proactive insights dashboard
- Show automatically detected risks (e.g., "Elevated Churn Rate")
- Demonstrate opportunity detection

**5. Semantic Memory Search (2 min)**

- Query: "What are our financial risks?"
- Show vector search returning relevant knowledge

**6. Data Connectors (1 min)**

- Brief mention of API and database connectors
- Show connector registry

---

## Test Suite Summary

```
201 passed, 0 failed
- test_graph.py:      ✓ Executive routing, supervisor routing, quality gate
- test_mission.py:    ✓ 17 named nodes, executive pipeline, CEO→CFO→COO→Risk
- test_supervisor.py: ✓ 6 categories including executive classification
- test_analyst.py:    ✓ Business analysis output
- test_strategist.py: ✓ Strategic recommendations
- test_decision.py:   ✓ Decision synthesis
- All agent fallbacks: ✓ 7 agent fallback tests passing
```

---

## Version History

| Version | Date      | Changes                                                                                          |
| ------- | --------- | ------------------------------------------------------------------------------------------------ |
| 1.0.0   | July 2026 | Initial MVP — Hub71 launch                                                                       |
| 1.1.0   | July 2026 | Enterprise upgrade — Executive team, proactive intelligence, data connectors, reliability system |
