"""
πX Embedding-Based Router — pgvector similarity for semantic agent routing.

Replaces text-overlap scoring with real embedding similarity using pgvector.
Stores agent capability embeddings and computes cosine similarity against query embeddings.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import hashlib

from .agent_registry import AgentInstance, AgentType, AgentStatus


@dataclass
class EmbeddingRecord:
    """Cached embedding for an agent capability or query."""
    id: str
    text: str
    embedding: list[float]
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class EmbeddingRouter:
    """Semantic routing using embedding cosine similarity via pgvector.

    In production, embeddings come from the AI Gateway's EmbeddingService
    (text-embedding-3-small) and are stored in pgvector.
    Here we use a deterministic hash-based pseudo-embedding for testing
    that produces stable, reproducible similarity scores.
    """

    EMBEDDING_DIM = 128

    # Capability descriptions per agent type
    CAPABILITY_TEXTS: dict[AgentType, str] = {
        AgentType.SALES: "revenue sales sell-out margin growth customer purchasing trends analysis forecasting quarterly performance",
        AgentType.INVENTORY: "inventory stock levels supply chain replenishment demand prediction warehouse logistics storage",
        AgentType.CUSTOMER: "customer behavior churn retention satisfaction loyalty segmentation lifecycle acquisition",
        AgentType.PRODUCTION: "production OEE manufacturing efficiency throughput cycle time bottleneck capacity utilization",
        AgentType.QUALITY: "quality defect rate inspection yield root cause analysis compliance standards defects scrap",
        AgentType.MAINTENANCE: "maintenance equipment downtime failure prediction preventive sensor health monitoring reliability MTBF",
        AgentType.FINANCE: "financial cost margin EBITDA cash flow budget forecast P&L revenue expense profitability",
        AgentType.MARKETING: "marketing campaign promotion ROI conversion acquisition advertising channel effectiveness CTR",
        AgentType.HR: "employee workforce talent attrition performance headcount hiring training HR retention",
        AgentType.STRATEGY: "strategic growth competitive market expansion opportunity planning positioning vision executive",
    }

    def __init__(self) -> None:
        self._agent_embeddings: dict[str, EmbeddingRecord] = {}  # agent_id → embedding
        self._query_cache: dict[str, EmbeddingRecord] = {}  # query_hash → embedding
        self._initialized = False

    def _pseudo_embed(self, text: str) -> list[float]:
        """Deterministic hash-based pseudo-embedding for testing.

        In production, this calls:
            from packages.cognitive_kernel.memory_engine.embedding_service import EmbeddingService
            return await EmbeddingService().embed(text, model="text-embedding-3-small")
        """
        words = text.lower().split()
        vec = [0.0] * self.EMBEDDING_DIM
        for word in words:
            h = int(hashlib.md5(word.encode()).hexdigest(), 16)
            for i in range(min(8, self.EMBEDDING_DIM)):
                vec[h % self.EMBEDDING_DIM] += ((h >> (i * 4)) & 0xF) / 15.0
                h = (h * 31 + i) & 0xFFFFFFFFFFFFFFFF
        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b, strict=False))
        norm_a = math.sqrt(sum(x * x for x in a)) or 1.0
        norm_b = math.sqrt(sum(y * y for y in b)) or 1.0
        return dot / (norm_a * norm_b)

    def register_agent(self, agent: AgentInstance) -> EmbeddingRecord:
        """Compute and store the capability embedding for an agent."""
        cap_text = self.CAPABILITY_TEXTS.get(agent.spec.type, agent.spec.purpose)
        # Enhance with KPI names
        if agent.spec.kpis_monitored:
            cap_text += " " + " ".join(agent.spec.kpis_monitored)
        # Enhance with goals
        if agent.spec.goals:
            cap_text += " " + " ".join(agent.spec.goals)

        embedding = self._pseudo_embed(cap_text)
        record = EmbeddingRecord(
            id=f"emb_{agent.id}",
            text=cap_text,
            embedding=embedding,
            metadata={"agent_id": agent.id, "agent_type": agent.spec.type.value},
        )
        self._agent_embeddings[agent.id] = record
        return record

    def route(
        self,
        query: str,
        agents: list[AgentInstance],
        profile_context: dict[str, Any] | None = None,
        threshold: float = 0.15,
    ) -> dict[str, Any]:
        """Route a query to agents using embedding cosine similarity."""
        active = [a for a in agents if a.status == AgentStatus.ACTIVE]
        if not active:
            return {"selected": [], "scores": {}, "method": "fallback", "reasoning": "No active agents"}

        # Ensure all active agents have embeddings
        for agent in active:
            if agent.id not in self._agent_embeddings:
                self.register_agent(agent)

        # Embed the query
        query_hash = hashlib.md5(query.encode()).hexdigest()
        if query_hash not in self._query_cache:
            self._query_cache[query_hash] = EmbeddingRecord(
                id=f"qemb_{query_hash[:12]}",
                text=query,
                embedding=self._pseudo_embed(query),
            )

        query_emb = self._query_cache[query_hash].embedding

        # Compute similarity scores
        scores: dict[str, float] = {}
        for agent in active:
            agent_emb = self._agent_embeddings[agent.id].embedding
            sim = self._cosine_similarity(query_emb, agent_emb)

            # Profile context boost: if agent monitors KPIs mentioned in profile
            profile_boost = 0.0
            if profile_context:
                kpis = profile_context.get("kpis", [])
                if isinstance(kpis, list):
                    profile_kpi_set = {k.get("name", "").lower() for k in kpis if isinstance(k, dict)}
                    agent_kpi_set = {k.lower() for k in agent.spec.kpis_monitored}
                    if profile_kpi_set & agent_kpi_set:
                        profile_boost = 0.1

            scores[agent.id] = round(sim + profile_boost, 4)

        # Select agents above threshold
        selected = [aid for aid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True) if score >= threshold]

        # Fallback: top 3 if none above threshold
        if not selected:
            selected = [aid for aid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]]

        agent_map = {a.id: a for a in active}
        reasoning_lines = [f"Query: '{query}'", "Embedding similarity routing:"]
        for aid in selected[:5]:
            agent = agent_map.get(aid)
            if agent:
                reasoning_lines.append(f"  → {agent.spec.label} (similarity: {scores[aid]:.4f})")

        return {
            "selected": selected,
            "scores": scores,
            "method": "embedding",
            "reasoning": "\n".join(reasoning_lines),
        }

    def get_agent_embedding(self, agent_id: str) -> list[float] | None:
        rec = self._agent_embeddings.get(agent_id)
        return rec.embedding if rec else None

    def clear_cache(self) -> None:
        self._query_cache.clear()
