from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from packages.cognitive-kernel.knowledge-graph import get_knowledge_graph
from app.services.analytics import get_analytics_service
from app.services.proactive import get_proactive_service

logger = logging.getLogger("pix.services.reports")


class BusinessIntelligenceReports:
    """Generates structured business intelligence reports.

    Combines data from knowledge graph, proactive intelligence,
    and customer analytics to produce executive-ready reports.
    """

    async def weekly_executive_report(self, org_id: str = "default") -> dict[str, Any]:
        kg = get_knowledge_graph()
        analytics = get_analytics_service()
        proactive = get_proactive_service()

        profile = kg.get_company_profile(org_id)
        insights = await proactive.analyze(org_id)
        org_stats = analytics.get_org_summary(org_id)

        critical_alerts = [i for i in insights if i.severity in ("critical", "high")]
        opportunities = [i for i in insights if i.type == "opportunity"]

        return {
            "report_type": "weekly_executive_summary",
            "generated_at": datetime.now(UTC).isoformat(),
            "org_id": org_id,
            "company": profile.get("name", "Unknown"),
            "executive_summary": self._generate_exec_summary(profile, org_stats, critical_alerts),
            "key_metrics": profile.get("metrics", {}),
            "top_priorities": [i.title for i in critical_alerts[:5]],
            "opportunities": [
                {"title": o.title, "description": o.description}
                for o in opportunities[:5]
            ],
            "analytics_snapshot": {
                "problems_detected": org_stats["problems_detected"]["total"],
                "recommendations": org_stats["recommendations_generated"]["total"],
                "actions_taken": org_stats["actions_taken"]["total"],
                "time_saved_hours": org_stats["estimated_time_saved_hours"],
                "impact_score": org_stats["business_impact_score"],
            },
            "alerts_count": len(critical_alerts),
            "total_insights": len(insights),
        }

    async def risk_report(self, org_id: str = "default") -> dict[str, Any]:
        kg = get_knowledge_graph()
        proactive = get_proactive_service()

        profile = kg.get_company_profile(org_id)
        insights = await proactive.analyze(org_id)
        risks = [i for i in insights if i.type == "risk"]
        existing_risks = kg.get_nodes_by_type("risk", org_id)

        return {
            "report_type": "risk_assessment",
            "generated_at": datetime.now(UTC).isoformat(),
            "org_id": org_id,
            "company": profile.get("name", "Unknown"),
            "overall_risk_score": self._calculate_risk_score(risks, existing_risks),
            "risk_breakdown": {
                "critical": len([r for r in risks if r.severity == "critical"]),
                "high": len([r for r in risks if r.severity == "high"]),
                "medium": len([r for r in risks if r.severity == "medium"]),
                "low": len([r for r in risks if r.severity == "low"]),
            },
            "identified_risks": [
                {"title": r.title, "description": r.description, "severity": r.severity}
                for r in risks
            ],
            "known_risk_areas": [{"id": n.id, "description": n.label, "severity": n.properties.get("severity", "unknown")} for n in existing_risks],
            "recommended_actions": self._generate_risk_actions(risks),
        }

    async def opportunity_report(self, org_id: str = "default") -> dict[str, Any]:
        kg = get_knowledge_graph()
        proactive = get_proactive_service()

        profile = kg.get_company_profile(org_id)
        insights = await proactive.analyze(org_id)
        opportunities = [i for i in insights if i.type == "opportunity"]
        kg_opportunities = kg.get_nodes_by_type("opportunity", org_id)

        return {
            "report_type": "opportunity_analysis",
            "generated_at": datetime.now(UTC).isoformat(),
            "org_id": org_id,
            "company": profile.get("name", "Unknown"),
            "opportunities_count": len(opportunities) + len(kg_opportunities),
            "ai_detected_opportunities": [
                {"title": o.title, "description": o.description}
                for o in opportunities
            ],
            "known_opportunities": [
                {"description": n.label, "confidence": n.properties.get("confidence", "N/A")}
                for n in kg_opportunities
            ],
            "growth_levers": self._identify_growth_levers(profile),
        }

    async def performance_summary(self, org_id: str = "default") -> dict[str, Any]:
        analytics = get_analytics_service()
        proactive = get_proactive_service()

        org_stats = analytics.get_org_summary(org_id)
        agent_stats = analytics.get_agent_analytics()
        trends = analytics.get_daily_trend(30)
        insights = await proactive.analyze(org_id)

        return {
            "report_type": "performance_summary",
            "generated_at": datetime.now(UTC).isoformat(),
            "org_id": org_id,
            "analytics": org_stats,
            "agent_performance": agent_stats,
            "daily_trends": trends,
            "total_insights_generated": len(insights),
            "active_alerts": len([i for i in insights if i.severity in ("critical", "high")]),
            "recommendation_velocity": self._calculate_velocity(trends),
        }

    def _generate_exec_summary(
        self, profile: dict, stats: dict, alerts: list,
    ) -> str:
        parts = [f"Executive Summary for {profile.get('name', 'Company')}"]
        if stats["problems_detected"]["total"] > 0:
            parts.append(f"Detected {stats['problems_detected']['total']} business problems.")
        if stats["recommendations_generated"]["total"] > 0:
            parts.append(f"Generated {stats['recommendations_generated']['total']} recommendations ({stats['recommendation_to_action_rate']}% action rate).")
        if stats["estimated_time_saved_hours"] > 0:
            parts.append(f"Estimated {stats['estimated_time_saved_hours']} hours saved through AI-driven analysis.")
        if alerts:
            parts.append(f"{len(alerts)} critical/high priority alerts require attention.")
        return " | ".join(parts)

    def _calculate_risk_score(self, risks: list, existing_risks: list) -> float:
        weights = {"critical": 1.0, "high": 0.7, "medium": 0.4, "low": 0.1}
        total = len(risks) + len(existing_risks)
        if total == 0:
            return 0.0
        weighted = sum(
            weights.get(r.severity, 0.3) for r in risks
        ) + sum(
            weights.get(n.properties.get("severity", "medium"), 0.3) for n in existing_risks
        )
        return round(min(1.0, weighted / max(total, 1)), 2)

    def _generate_risk_actions(self, risks: list) -> list[str]:
        actions = []
        for r in risks:
            if r.severity in ("critical", "high"):
                actions.append(f"[IMMEDIATE] {r.title}: {r.description}")
            elif r.severity == "medium":
                actions.append(f"[SCHEDULE] {r.title}: {r.description}")
        return actions[:10]

    def _identify_growth_levers(self, profile: dict) -> list[dict]:
        levers = []
        metrics = profile.get("metrics", {})
        for name, value in metrics.items():
            name_lower = name.lower()
            if "churn" in name_lower:
                levers.append({"area": "Customer Retention", "metric": name, "value": value, "leverage": "high"})
            if "revenue" in name_lower and "growth" in name_lower:
                levers.append({"area": "Revenue Growth", "metric": name, "value": value, "leverage": "high"})
            if "acquisition" in name_lower:
                levers.append({"area": "Customer Acquisition", "metric": name, "value": value, "leverage": "medium"})
        return levers[:5]

    def _calculate_velocity(self, trends: list[dict]) -> dict:
        if not trends:
            return {"daily_avg": 0, "weekly_trend": "stable"}
        recent = trends[-7:]
        avg = sum(t.get("recommendations", 0) for t in recent) / max(len(recent), 1)
        return {"daily_avg": round(avg, 1), "weekly_trend": "increasing" if avg > 3 else "stable"}


_reports: BusinessIntelligenceReports | None = None


def get_reports_service() -> BusinessIntelligenceReports:
    global _reports
    if _reports is None:
        _reports = BusinessIntelligenceReports()
    return _reports
