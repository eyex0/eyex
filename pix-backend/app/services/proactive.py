from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from packages.cognitive-kernel.knowledge-graph import KnowledgeGraph, get_knowledge_graph
from packages.cognitive-kernel.memory-engine import VectorMemory, get_vector_memory

logger = logging.getLogger("pix.services.proactive")


@dataclass
class ProactiveInsight:
    type: str  # risk | opportunity | alert | recommendation
    severity: str  # critical | high | medium | low | info
    title: str
    description: str
    source_agent: str = "proactive"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


class ProactiveIntelligenceService:
    """Automatically detects risks, opportunities, and generates alerts.

    Analyzes company knowledge graph and vector memory to surface
    actionable insights without explicit user queries.
    """

    def __init__(
        self,
        kg: KnowledgeGraph | None = None,
        vm: VectorMemory | None = None,
    ):
        self.kg = kg or get_knowledge_graph()
        self.vm = vm or get_vector_memory()

    async def analyze(self, org_id: str = "default") -> list[ProactiveInsight]:
        insights: list[ProactiveInsight] = []
        now = datetime.now(UTC).isoformat()

        # 1. Detect financial risks from metrics
        company = self.kg.get_company_profile(org_id)
        metrics = company.get("metrics", {})
        for name, value in metrics.items():
            insight = self._evaluate_metric(name, value, now)
            if insight:
                insights.append(insight)

        # 2. Scan for critical risks
        existing_risks = self.kg.get_nodes_by_type("risk", org_id)
        for risk in existing_risks:
            severity = risk.properties.get("severity", "medium")
            if severity in ("critical", "high"):
                insights.append(ProactiveInsight(
                    type="alert",
                    severity=severity,
                    title=f"Active Risk: {risk.label}",
                    description=risk.properties.get("description", risk.label),
                    source_agent="risk_monitor",
                    metadata={"node_id": risk.id},
                    created_at=now,
                ))

        # 3. Detect growth opportunities
        opportunities = self.kg.get_nodes_by_type("opportunity", org_id)
        for opp in opportunities:
            confidence = opp.properties.get("confidence", 0.5)
            if isinstance(confidence, (int, float)) and confidence > 0.6:
                insights.append(ProactiveInsight(
                    type="opportunity",
                    severity="medium",
                    title=f"Opportunity: {opp.label}",
                    description=opp.properties.get("description", ""),
                    source_agent="opportunity_scanner",
                    metadata={"node_id": opp.id, "confidence": confidence},
                    created_at=now,
                ))

        # 4. Generate recommendations from knowledge gaps
        profile = self.kg.get_company_profile(org_id)
        if not profile.get("competitors") and profile.get("name"):
            insights.append(ProactiveInsight(
                type="recommendation",
                severity="low",
                title="Complete Competitive Analysis",
                description="No competitors recorded in company knowledge graph. Add competitive intelligence for better strategic recommendations.",
                source_agent="knowledge_gap",
                created_at=now,
            ))

        logger.info("Proactive analysis for org=%s: %d insights generated", org_id, len(insights))
        return insights

    def _evaluate_metric(self, name: str, value: str, now: str) -> ProactiveInsight | None:
        if not value:
            return None
        try:
            num = float(value.replace("$", "").replace("%", "").replace("M", "").replace("K", "").strip())
        except (ValueError, TypeError):
            num = 0

        name_lower = name.lower()

        # Revenue decline detection
        if "revenue" in name_lower and num < 0:
            return ProactiveInsight(
                type="risk",
                severity="high",
                title=f"Revenue Decline Detected: {name}",
                description=f"Revenue metric '{name}' shows negative value ({value}). Needs immediate attention.",
                source_agent="financial_monitor",
                metadata={"metric": name, "value": value},
                created_at=now,
            )

        # Cash flow risk
        if "cash" in name_lower and num < 100000:
            return ProactiveInsight(
                type="risk",
                severity="critical" if num < 50000 else "high",
                title=f"Low Cash Reserve: {name}",
                description=f"Cash flow metric '{name}' is critically low ({value}). Review runway immediately.",
                source_agent="financial_monitor",
                metadata={"metric": name, "value": value},
                created_at=now,
            )

        # Growth opportunity
        if ("growth" in name_lower or "increase" in name_lower) and num > 20:
            return ProactiveInsight(
                type="opportunity",
                severity="medium",
                title=f"Strong Growth Signal: {name}",
                description=f"Positive growth metric detected: {name} = {value}. Consider accelerating investment.",
                source_agent="growth_analyzer",
                metadata={"metric": name, "value": value},
                created_at=now,
            )

        # Churn risk
        if "churn" in name_lower or "attrition" in name_lower:
            threshold = 5
            severity = "high" if num > threshold * 2 else "medium" if num > threshold else "low"
            if num > threshold:
                return ProactiveInsight(
                    type="risk",
                    severity=severity,
                    title=f"Elevated Churn Rate: {name}",
                    description=f"Customer churn rate is {value}. Target is <{threshold}%. Investigate and implement retention strategies.",
                    source_agent="customer_analytics",
                    metadata={"metric": name, "value": value},
                    created_at=now,
                )

        return None

    async def summary(self, org_id: str = "default") -> dict[str, Any]:
        insights = await self.analyze(org_id)
        return {
            "total": len(insights),
            "by_type": {
                t: len([i for i in insights if i.type == t])
                for t in set(i.type for i in insights)
            },
            "by_severity": {
                s: len([i for i in insights if i.severity == s])
                for s in set(i.severity for i in insights)
            },
            "critical_count": len([i for i in insights if i.severity == "critical"]),
            "high_count": len([i for i in insights if i.severity == "high"]),
            "insights": [
                {
                    "type": i.type,
                    "severity": i.severity,
                    "title": i.title,
                    "description": i.description,
                    "source": i.source_agent,
                }
                for i in insights[:20]
            ],
        }


_proactive: ProactiveIntelligenceService | None = None


def get_proactive_service() -> ProactiveIntelligenceService:
    global _proactive
    if _proactive is None:
        _proactive = ProactiveIntelligenceService()
    return _proactive
