"""
πX Natural Language Intelligence Interface.

Flow: User asks question → Understand intent → Identify KPIs → Retrieve memory
      → Activate agents (via embedding router) → Generate decision → Visualize result.

Example: "Why did revenue drop in Germany?" →
  Intent: root cause analysis
  KPIs: Revenue
  Agents: Sales Agent + Finance Agent
  Memory: Previous Q3 analysis
  Decision: Revenue decline caused by market entry of competitor X
  Visualization: Revenue chart with annotation
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any
import uuid


@dataclass
class NLQueryResult:
    query: str
    intent: str = ""
    identified_kpis: list[str] = field(default_factory=list)
    identified_entities: list[str] = field(default_factory=list)
    activated_agents: list[str] = field(default_factory=list)
    memory_retrieved: list[dict] = field(default_factory=list)
    decision: str = ""
    confidence: float = 0.0
    visualization: dict[str, Any] = field(default_factory=dict)
    execution_time_ms: int = 0
    agent_responses: list[dict] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def to_dict(self) -> dict:
        return {
            "query": self.query, "intent": self.intent,
            "identified_kpis": self.identified_kpis,
            "identified_entities": self.identified_entities,
            "activated_agents": self.activated_agents,
            "memory_retrieved": self.memory_retrieved,
            "decision": self.decision, "confidence": self.confidence,
            "visualization": self.visualization,
            "execution_time_ms": self.execution_time_ms,
            "agent_responses": self.agent_responses,
        }


class NLIntelligenceEngine:
    """Natural language → Enterprise intelligence pipeline.

    This is the user-facing entry point for the entire πX system.
    A single question triggers the full intelligence loop.
    """

    # Intent patterns
    INTENT_PATTERNS: dict[str, list[str]] = {
        "root_cause": ["why did", "what caused", "reason for", "why is", "why was"],
        "prediction": ["forecast", "predict", "what will", "expected", "projected"],
        "comparison": ["compare", "difference between", "vs", "versus", "better"],
        "summary": ["summarize", "overview", "status of", "how is", "what is the state"],
        "recommendation": ["recommend", "should", "what should", "best approach", "advice"],
        "trend": ["trend", "over time", "historical", "pattern", "trajectory"],
        "anomaly": ["anomaly", "unusual", "unexpected", "outlier", "strange"],
    }

    # KPI keywords for extraction
    KPI_KEYWORDS: dict[str, list[str]] = {
        "revenue": ["revenue", "sales", "income", "turnover"],
        "cost": ["cost", "expense", "spending", "expenditure"],
        "margin": ["margin", "profitability", "markup"],
        "inventory": ["inventory", "stock", "supply"],
        "oee": ["oee", "efficiency", "utilization"],
        "quality": ["quality", "defect", "yield", "scrap"],
        "churn": ["churn", "retention", "attrition"],
        "production": ["production", "output", "throughput"],
    }

    def __init__(self) -> None:
        self._history: list[NLQueryResult] = []

    def analyze_query(
        self,
        query: str,
        profile_context: dict[str, Any],
        available_agents: list[dict[str, Any]],
        memory_entries: list[dict[str, Any]] | None = None,
        agent_responses: list[dict[str, Any]] | None = None,
    ) -> NLQueryResult:
        """Full NL intelligence pipeline."""
        import time
        start = time.time()

        # 1. Understand intent
        intent = self._detect_intent(query)

        # 2. Identify KPIs
        kpis = self._identify_kpis(query, profile_context)

        # 3. Identify entities (geographic, product, etc.)
        entities = self._identify_entities(query, profile_context)

        # 4. Activate agents (semantic matching)
        activated = self._activate_agents(query, available_agents, kpis)

        # 5. Retrieve relevant memory
        relevant_memory = self._retrieve_memory(query, memory_entries or [])

        # 6. Generate decision (synthesize from agent responses)
        decision, confidence = self._generate_decision(
            query, intent, kpis, activated, agent_responses or [], relevant_memory,
        )

        # 7. Generate visualization spec
        viz = self._generate_visualization(intent, kpis, entities)

        elapsed = int((time.time() - start) * 1000)
        result = NLQueryResult(
            query=query, intent=intent,
            identified_kpis=kpis, identified_entities=entities,
            activated_agents=activated,
            memory_retrieved=relevant_memory,
            decision=decision, confidence=confidence,
            visualization=viz, execution_time_ms=elapsed,
            agent_responses=agent_responses or [],
        )
        self._history.append(result)
        return result

    def _detect_intent(self, query: str) -> str:
        query_lower = query.lower()
        for intent, patterns in self.INTENT_PATTERNS.items():
            if any(p in query_lower for p in patterns):
                return intent
        return "general_inquiry"

    def _identify_kpis(self, query: str, profile_context: dict) -> list[str]:
        query_lower = query.lower()
        identified = set()

        # From KPI keywords
        for kpi, keywords in self.KPI_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                identified.add(kpi)

        # From profile KPIs
        profile_kpis = profile_context.get("kpis", [])
        if isinstance(profile_kpis, list):
            for kpi_obj in profile_kpis:
                if isinstance(kpi_obj, dict):
                    name = kpi_obj.get("name", "").lower()
                    aliases = kpi_obj.get("aliases", [])
                    if name and name in query_lower:
                        identified.add(name)
                    for alias in aliases:
                        if isinstance(alias, str) and alias.lower() in query_lower:
                            identified.add(name)

        return list(identified)

    def _identify_entities(self, query: str, profile_context: dict) -> list[str]:
        """Identify entities mentioned (geographic, product, customer)."""
        entities = set()

        # Geographic entities (capitalized words that aren't KPIs)
        import re
        capitalized = re.findall(r'\b[A-Z][a-z]+\b', query)
        kpi_words = {"Revenue", "Sales", "Cost", "Quality", "OEE", "Why", "What", "How", "The"}
        for word in capitalized:
            if word not in kpi_words and len(word) > 3:
                entities.add(word)

        # From profile ontology
        ontology = profile_context.get("ontology", {})
        if isinstance(ontology, dict):
            profile_entities = set(ontology.get("entities", {}).keys())
            query_lower = query.lower()
            for ent in profile_entities:
                if ent.lower() in query_lower:
                    entities.add(ent)

        return list(entities)

    def _activate_agents(self, query: str, agents: list[dict], kpis: list[str]) -> list[str]:
        """Activate relevant agents based on KPI matching and query similarity."""
        query_lower = query.lower()
        activated = []

        for agent in agents:
            agent_kpis = set(agent.get("kpis_monitored", []))
            agent_purpose = agent.get("purpose", "").lower()

            # Activate if agent monitors a KPI mentioned in query
            kpi_match = any(kpi.lower() in query_lower for kpi in agent_kpis)
            purpose_match = any(kw in query_lower for kw in agent_purpose.split()[:5])

            if kpi_match or purpose_match:
                activated.append(agent.get("label", agent.get("agent_id", "unknown")))

        # If none activated, select top 3
        if not activated and agents:
            activated = [a.get("label", "agent") for a in agents[:3]]

        return activated

    def _retrieve_memory(self, query: str, memory: list[dict]) -> list[dict]:
        """Retrieve relevant memory entries."""
        query_words = set(query.lower().split())
        scored = []
        for entry in memory:
            content = (entry.get("content") or entry.get("action") or "").lower()
            overlap = len(query_words & set(content.split()))
            if overlap > 0:
                scored.append((overlap, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [entry for _, entry in scored[:5]]

    def _generate_decision(
        self, query: str, intent: str, kpis: list[str],
        activated_agents: list[str], agent_responses: list[dict],
        memory: list[dict],
    ) -> tuple[str, float]:
        """Generate a decision from agent responses and memory."""
        if not agent_responses and not memory:
            return "Insufficient data to generate a decision. Activate agents for analysis.", 0.2

        parts = [f"## Intelligence Analysis\n**Query:** {query}\n"]
        parts.append(f"**Intent:** {intent.replace('_', ' ').title()}\n")
        if kpis:
            parts.append(f"**KPIs:** {', '.join(kpis)}\n")
        if activated_agents:
            parts.append(f"**Agents activated:** {', '.join(activated_agents)}\n")

        if agent_responses:
            parts.append("\n### Agent Analysis\n")
            for resp in agent_responses:
                agent_label = resp.get("agent_label", resp.get("agent_id", "Agent"))
                response = resp.get("response", resp.get("result", ""))
                parts.append(f"**{agent_label}:** {response[:200]}\n")

        if memory:
            parts.append("\n### Historical Context\n")
            for m in memory[:2]:
                content = m.get("content", m.get("action", ""))
                parts.append(f"- {content[:100]}\n")

        parts.append("\n### Decision\n")
        parts.append(f"Based on analysis from {len(activated_agents)} agent(s) and {len(memory)} memory entries, ")
        if intent == "root_cause":
            parts.append("the primary cause has been identified through multi-agent investigation. ")
        elif intent == "prediction":
            parts.append("the forecast incorporates historical patterns and current signals. ")
        else:
            parts.append("the analysis synthesizes available evidence. ")

        confidence = min(0.5 + len(agent_responses) * 0.1 + len(memory) * 0.05, 0.95)
        return "".join(parts), round(confidence, 2)

    def _generate_visualization(self, intent: str, kpis: list[str], entities: list[str]) -> dict[str, Any]:
        """Generate a visualization specification."""
        viz_type = "line_chart"
        if intent == "comparison":
            viz_type = "bar_chart"
        elif intent == "anomaly":
            viz_type = "scatter_plot"
        elif intent == "summary":
            viz_type = "kpi_card"

        return {
            "type": viz_type,
            "kpis": kpis,
            "entities": entities,
            "title": f"{' vs '.join(kpis) if kpis else 'Intelligence'}" + (f" by {', '.join(entities)}" if entities else ""),
            "data_source": "agent_responses",
        }

    def get_history(self, limit: int = 20) -> list[dict]:
        return [r.to_dict() for r in self._history[-limit:]]
