# πX Core Intelligence Layer

The intelligence infrastructure that powers πX — connecting enterprise data, memory, knowledge, reasoning, and autonomous AI.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    πX Intelligence Pipeline                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Enterprise Sources (PDF, DOCX, XLSX, CSV, TXT, Images)         │
│         │                                                        │
│         ▼                                                        │
│  ┌─────────────────┐    ┌──────────────────┐                     │
│  │  Ingestion       │───▶│  Memory Engine    │                    │
│  │  Pipeline        │    │  - Chunker        │                    │
│  │  - Parse         │    │  - Normalizer     │                    │
│  │  - Normalize     │    │  - Embedding Svc  │                    │
│  │  - Chunk         │    │  - Vector Store   │                    │
│  │  - Embed         │    │  - Version History│                    │
│  │  - Store         │    └────────┬─────────┘                     │
│  └─────────────────┘             │                               │
│                                  ▼                               │
│                         ┌──────────────────┐                     │
│                         │  Knowledge Graph │                     │
│                         │  - Entity Extract│                     │
│                         │  - Graph Store   │                     │
│                         │  - Graph Builder │                     │
│                         │  - Traversal     │                     │
│                         └────────┬─────────┘                     │
│                                  │                               │
│                                  ▼                               │
│  ┌─────────────────┐    ┌──────────────────┐                     │
│  │  AI Control      │    │  Decision Engine │                    │
│  │  Plane           │    │  - Risk Analysis │                    │
│  │  - 12 Providers  │    │  - Confidence    │                    │
│  │  - Model Router  │    │  - Alternatives  │                    │
│  │  - Cost Tracker  │    │  - Decision Store│                    │
│  │  - Semantic Cache│    └────────┬─────────┘                     │
│  └────────┬────────┘             │                               │
│           │                      ▼                               │
│           └──────────────▶  Business Action                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Phase 1 — AI Control Plane

### AIGateway (`packages/cognitive_kernel/ai_gateway/main.py`)
- Unified entry point for all AI calls
- Retry with exponential backoff (3 attempts: 1s, 2s, 4s)
- Fallback chains: if primary provider fails, tries secondary providers
- Semantic caching (embedding-based, 1h TTL)
- Cost/token/latency tracking per request

### Providers (`packages/cognitive_kernel/ai_gateway/providers/`)
| Provider | Models | Capabilities |
|----------|--------|-------------|
| OpenAI | GPT-4o, GPT-4o-mini | generation, streaming, embedding, classification |
| Anthropic | Claude 3 Opus, Sonnet | generation, streaming, summarization |
| Google | Gemini Pro, Flash | generation, streaming, embedding |
| DeepSeek | DeepSeek Chat | generation |
| OpenRouter | Multi-provider routing | generation |
| Ollama | Local models (Llama3, etc.) | generation, embedding |

### ModelRouter (`packages/cognitive_kernel/ai_gateway/router.py`)
- Routing strategies: cheapest, fastest, highest_quality, balanced
- Task type routing: generation, embedding, classification, complex_reasoning
- Fallback chains per provider

## Phase 2 — Memory Engine

### IngestionPipeline (`packages/cognitive_kernel/ingestion/pipeline.py`)
```
File → Parse → Normalize → Chunk → Embed → Store → Metadata
```
- Supported formats: PDF, DOCX, XLSX, CSV, TXT, Images
- Chunking strategies: semantic (default), fixed-size, sliding window, recursive

### VectorStore (`packages/cognitive_kernel/memory_engine/vector_store.py`)
- pgvector-backed (PostgreSQL extension)
- Semantic search (cosine similarity)
- Hybrid search (keyword + vector, weighted 0.7/0.3)
- Metadata filtering with JSONB

### EmbeddingService (`packages/cognitive_kernel/memory_engine/embedding_service.py`)
- Batch embedding (100 per batch)
- Redis caching (24h TTL)
- Rate limiting

## Phase 3 — Knowledge Graph

### GraphStore (`packages/cognitive_kernel/knowledge_graph/graph_store.py`)
- PostgreSQL-backed (nodes + edges tables)
- BFS traversal with depth limit
- Shortest path (BFS)
- Degree centrality
- Multi-tenant (org_id filtering)

### EntityExtractor (`packages/cognitive_kernel/knowledge_graph/entity_extractor.py`)
- LLM-based entity extraction (11 entity types)
- LLM-based relationship extraction (10 relation types)
- Confidence scoring for extractions
- Entity resolution (fuzzy matching)

### API Endpoints (`/api/v1/knowledge/*`)
| Method | Path | Description |
|--------|------|-------------|
| GET | /nodes | List nodes (filter by type, search) |
| POST | /nodes | Create node |
| GET | /nodes/{id} | Get node with neighbors |
| DELETE | /nodes/{id} | Delete node |
| POST | /relations | Create relation |
| GET | /graph | Get full graph (paginated) |
| POST | /extract | Extract entities from text |
| POST | /build | Build graph from document |
| GET | /stats | Graph statistics |

## Phase 4 — Decision Engine

### DecisionEngine (`packages/cognitive_kernel/decision_engine/decision_engine.py`)
```
Question → Context Retrieval → Evidence Collection → Reasoning → Risk Analysis → Recommendation
```
- Integrates with Memory Engine (context retrieval)
- Integrates with Knowledge Graph (evidence collection)
- Uses AI Gateway for reasoning and recommendation generation

### ConfidenceScorer (`packages/cognitive_kernel/decision_engine/confidence_scorer.py`)
Weighted scoring:
- Evidence count: 20%
- Evidence confidence: 20%
- Reasoning depth: 15%
- Risk level (inverse): 25%
- Source diversity: 20%

### API Endpoints (`/api/v1/decisions/*`)
| Method | Path | Description |
|--------|------|-------------|
| POST | / | Create decision (runs full pipeline) |
| GET | / | List decisions (filter by status, category) |
| GET | /{id} | Get decision detail |
| PATCH | /{id}/status | Update status (approve/reject/review) |
| GET | /analytics/summary | Decision analytics |

## Database Migrations
| Migration | Description |
|-----------|-------------|
| 0006 | pgvector extension, memory_chunks, memory_versions |
| 0007 | knowledge_nodes, knowledge_edges |
| 0008 | decisions |

## Frontend Integration
| Service | File | Endpoints |
|---------|------|-----------|
| KnowledgeGraphService | `src/services/knowledge-graph.service.ts` | /knowledge/* |
| DecisionsService | `src/services/decisions.service.ts` | /decisions/* |
| MemoryIntelligenceService | `src/services/memory-intelligence.service.ts` | /intelligence/* |

## Tests
```bash
cd pix-backend && pytest tests/cognitive_kernel/ -v
```
| Test Suite | Tests |
|------------|-------|
| test_chunker | 7 |
| test_normalizer | 5 |
| test_confidence_scorer | 5 |
| test_model_router | 10 |
| test_entities | 5 |
| test_ai_gateway | 7 |
| test_decision_engine | 5 |
| **Total** | **44** |
