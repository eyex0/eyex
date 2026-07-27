# πX Adaptive Intelligence Architecture

## Overview

πX uses the Intelligence Profile as the central context layer for all cognitive engines. No engine uses hardcoded entity types, KPIs, or terminology — everything reads from the organization's profile.

## Architecture

```
                    ┌─────────────────────────────────┐
                    │   Intelligence Profile           │
                    │   (JSONB, tenant-isolated)       │
                    │                                  │
                    │   • Industry & Business Model    │
                    │   • Custom Ontology (entities)   │
                    │   • KPIs (formulas, targets)     │
                    │   • Glossary (terminology)        │
                    │   • Data Sources & Mappings      │
                    │   • AI Policies & Agent Configs  │
                    └──────────────┬───────────────────┘
                                   │
                    ┌──────────────┼──────────────────┐
                    │              │                  │
                    ▼              ▼                  ▼
         ┌─────────────┐ ┌──────────────┐ ┌────────────────┐
         │ ProfileContext │ │  Memory     │ │  Knowledge    │
         │ Provider       │ │  Engine     │ │  Graph        │
         │ (get_context)  │ │             │ │               │
         └───────┬───────┘ │  Profile-   │ │  Profile-     │
                 │         │  Aware     │ │  Aware       │
                 ├────────►│  Ingestion │ │  Extractor   │
                 │         │  Pipeline  │ │               │
                 │         └────────────┘ └──────────────┘
                 │
                 ├────────►┌──────────────┐
                 │         │  Decision    │
                 │         │  Engine      │
                 │         │  Profile-    │
                 │         │  Aware       │
                 │         └──────────────┘
                 │
                 ├────────►┌──────────────┐
                 │         │  AI Gateway  │
                 │         │  Profile-    │
                 │         │  Aware       │
                 │         │  (privacy,   │
                 │         │   budget)    │
                 │         └──────────────┘
                 │
                 └────────►┌──────────────┐
                           │  Agent       │
                           │  Runtime     │
                           │  AgentFactory│
                           │  (profile-   │
                           │   generated) │
                           └──────────────┘
```

## Data Flow

### 1. Profile-Aware Ingestion (Memory Engine)
```
Upload → Profile Context Injection → Semantic Understanding → Entity Detection
       → Chunking → Embedding → Vector Storage
       (each chunk stores: profile_id, semantic_entities, business_context, confidence_score)
```

### 2. Profile-Aware Entity Extraction (Knowledge Graph)
```
Text → Load Profile Ontology → Build LLM Prompt from Company Entities
     → Extract → Validate Against Ontology → Store in Knowledge Graph
     (Retail: Store, Product, Customer | Manufacturing: Machine, WorkOrder, Supplier)
```

### 3. Profile-Aware Decision Engine
```
Question → Load Profile Context → Resolve Terminology → Identify Relevant KPIs
         → Reason with Company Context → Analyze Industry-Specific Risks
         → Recommend referencing Company KPIs
         (Generic: "Improve sales" | πX: "Increase Sell-out KPI by 15% in Region North")
```

### 4. Profile-Aware AI Gateway
```
AI Request → Load Org AI Policy → Check Privacy Level → Check Budget
           → Route to Appropriate Model → Generate
           (Financial: private model only | SaaS: cheapest/fastest)
```

### 5. Profile-Generated Agents (Agent Runtime)
```
Intelligence Profile → Read recommended_agents → Build Agent Configs
                     → Generate System Prompts with Company Context
                     → Assign Profile-Specific Tools
                     (Retail: Sales Agent, Inventory Agent | Manufacturing: Production Agent, Quality Agent)
```

## Security Boundaries

- **Tenant isolation**: Every table has `organization_id` — ProfileTenantGuard enforces on all operations
- **AI privacy**: Organizations can enforce private/local models for sensitive data
- **Data sensitivity**: High-sensitivity data never leaves the organization's infrastructure
- **Audit trail**: 20 event types track all profile lifecycle changes
- **Version control**: Full snapshots + diffs enable rollback to any previous state

## Integration Files

| Component | File | Purpose |
|-----------|------|---------|
| Context Provider | `intelligence_profile/context_provider.py` | Unified `get_context(org_id)` |
| Memory Engine | `ingestion/profile_aware_pipeline.py` | Profile-aware ingestion |
| Knowledge Graph | `knowledge_graph/profile_aware_extractor.py` | Ontology-driven extraction |
| Decision Engine | `decision_engine/profile_aware_decision.py` | KPI-aware reasoning |
| AI Gateway | `ai_gateway/profile_aware_gateway.py` | Policy-based routing |
| Agent Runtime | `agent_runtime/agent_factory.py` | Profile-generated agents |
