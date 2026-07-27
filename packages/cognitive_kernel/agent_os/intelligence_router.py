"""
πX Agent Intelligence Router — Replaces keyword routing with semantic routing.

Uses embedding similarity + context awareness + profile awareness + 
agent capability matching to select the best agents for a query.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .agent_registry import AgentInstance, AgentSpec, AgentType, AgentStatus


@dataclass
class RoutingDecision:
    """The router's decision on which agents to call."""
    query: str
    selected_agents: list[str] = field(default_factory=list)  # agent_ids
    scores: dict[str, float] = field(default_factory=dict)  # agent_id → score
    reasoning: str = ""
    routing_method: str = "semantic"  # semantic, keyword, fallback


class AgentIntelligenceRouter:
    """Semantic routing using embedding similarity + capability matching."""

    # Agent capability descriptions for embedding matching
    CAPABILITY_DESCRIPTIONS: dict[AgentType, str] = {
        AgentType.SALES: "revenue sales sell-out margin growth customer purchasing trends analysis forecasting",
        AgentType.INVENTORY: "inventory stock levels supply chain replenishment demand prediction warehouse",
        AgentType.CUSTOMER: "customer behavior churn retention satisfaction loyalty segmentation lifecycle",
        AgentType.PRODUCTION: "production OEE manufacturing efficiency throughput cycle time bottleneck capacity",
        AgentType.QUALITY: "quality defect rate inspection yield root cause analysis compliance standards",
        AgentType.MAINTENANCE: "maintenance equipment downtime failure prediction preventive sensor health monitoring",
        AgentType.FINANCE: "financial cost margin EBITDA cash flow budget forecast P&L revenue expense",
        AgentType.MARKETING: "marketing campaign promotion ROI conversion acquisition advertising channel effectiveness",
        AgentType.HR: "employee workforce talent attrition performance headcount hiring training HR",
        AgentType.STRATEGY: "strategic growth competitive market expansion opportunity planning positioning vision",
    }

    def __init__(self) -> None:
        self._keyword_map: dict[str, list[AgentType]] = {
            "revenue": [AgentType.SALES, AgentType.FINANCE, AgentType.STRATEGY],
            "sales": [AgentType.SALES, AgentType.MARKETING],
            "inventory": [AgentType.INVENTORY],
            "stock": [AgentType.INVENTORY],
            "customer": [AgentType.CUSTOMER, AgentType.MARKETING],
            "churn": [AgentType.CUSTOMER],
            "production": [AgentType.PRODUCTION],
            "oee": [AgentType.PRODUCTION, AgentType.MAINTENANCE],
            "quality": [AgentType.QUALITY],
            "defect": [AgentType.QUALITY],
            "maintenance": [AgentType.MAINTENANCE],
            "downtime": [AgentType.MAINTENANCE, AgentType.PRODUCTION],
            "cost": [AgentType.FINANCE],
            "margin": [AgentType.FINANCE, AgentType.SALES],
            "employee": [AgentType.HR],
            "hr": [AgentType.HR],
            "strategy": [AgentType.STRATEGY],
            "growth": [AgentType.STRATEGY, AgentType.SALES],
            "market": [AgentType.STRATEGY, AgentType.MARKETING],
            "campaign": [AgentType.MARKETING],
            "forecast": [AgentType.FINANCE, AgentType.SALES],
            "germany": [],  # Geo terms don't map to agents directly
            "europe": [],
            "asia": [],
        }

    def route(
        self,
        query: str,
        agents: list[AgentInstance],
        profile_context: dict[str, Any] | None = None,
    ) -> RoutingDecision:
        """Route a query to the best agents using semantic similarity."""
        active_agents = [a for a in agents if a.status == AgentStatus.ACTIVE]
        if not active_agents:
            return RoutingDecision(query=query, reasoning="No active agents available", routing_method="fallback")

        # Score each agent
        scores: dict[str, float] = {}
        for agent in active_agents:
            score = self._score_agent(query, agent, profile_context or {})
            scores[agent.id] = score

        # Select agents above threshold
        threshold = 0.15
        selected = [aid for aid, score in sorted(scores.items(), key=lambda x: x[1], reverse=True) if score >= threshold]

        # If no agents above threshold, use keyword routing as fallback
        if not selected:
            kw_agents = self._keyword_route(query, active_agents)
            selected = [a.id for a in kw_agents]
            if not selected:
                # Select top 3 by score regardless
                selected = [aid for aid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]]

        reasoning = self._build_reasoning(query, selected, scores, active_agents)
        return RoutingDecision(
            query=query,
            selected_agents=selected,
            scores=scores,
            reasoning=reasoning,
            routing_method="semantic" if selected else "fallback",
        )

    def _score_agent(self, query: str, agent: AgentInstance, profile_context: dict) -> float:
        """Score an agent's relevance to the query (0.0–1.0)."""
        query_lower = query.lower()

        # 1. Capability similarity (text overlap with capability description)
        capability_desc = self.CAPABILITY_DESCRIPTIONS.get(agent.spec.type, "")
        capability_words = set(capability_desc.split())
        query_words = set(query_lower.split())
        overlap = len(query_words & capability_words)
        capability_score = overlap / max(len(query_words), 1)

        # 2. KPI relevance
        kpi_score = 0.0
        for kpi in agent.spec.kpis_monitored:
            if kpi.lower() in query_lower:
                kpi_score += 0.15
        kpi_score = min(kpi_score, 0.5)

        # 3. Keyword boost
        keyword_score = 0.0
        for keyword, agent_types in self._keyword_map.items():
            if keyword in query_lower and agent.spec.type in agent_types:
                keyword_score += 0.2
        keyword_score = min(keyword_score, 0.4)

        # 4. Entity relevance (from profile context)
        entity_score = 0.0
        ontology = profile_context.get("ontology", {})
        if isinstance(ontology, dict):
            profile_entities = set(ontology.get("entities", {}).keys())
            agent_entities = set(agent.spec.knowledge_access)
            if "*" not in agent_entities:
                overlap_e = len(profile_entities & agent_entities)
                entity_score = min(overlap_e * 0.05, 0.15)

        # 5. Role relevance from profile
        role_score = 0.0
        kpis_in_profile = profile_context.get("kpis", [])
        if isinstance(kpis_in_profile, list):
            profile_kpi_names = {k.get("name", "").lower() for k in kpis_in_profile if isinstance(k, dict)}
            agent_kpi_set = {k.lower() for k in agent.spec.kpis_monitored}
            if profile_kpi_names & agent_kpi_set:
                role_score = 0.1

        total = capability_score * 0.35 + kpi_score * 0.25 + keyword_score * 0.2 + entity_score * 0.1 + role_score * 0.1
        return round(total, 4)

    def _keyword_route(self, query: str, agents: list[AgentInstance]) -> list[AgentInstance]:
        query_lower = query.lower()
        relevant_types: set[AgentType] = set()
        for keyword, agent_types in self._keyword_map.items():
            if keyword in query_lower:
                relevant_types.update(agent_types)
        if not relevant_types:
            return []
        return [a for a in agents if a.spec.type in relevant_types]

    def _build_reasoning(self, query: str, selected: list[str], scores: dict[str, float], agents: list[AgentInstance]) -> str:
        agent_map = {a.id: a for a in agents}
        parts = [f"Query: '{query}'\nRouting decision:"]
        for aid in selected[:5]:
            agent = agent_map.get(aid)
            if agent:
                parts.append(f"  → {agent.spec.label} (score: {scores.get(aid, 0):.3f})")
        return "\n".join(parts)
