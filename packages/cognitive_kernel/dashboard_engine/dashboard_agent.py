"""
πX Dashboard Intelligence Agent — AI-powered dashboard recommendations.

Analyzes a company's Intelligence Profile and generates a recommended
dashboard configuration. Uses LLM reasoning to understand what the user
needs based on their role, industry, and company context.

Example reasoning:
  "The CFO of this retail company needs inventory margin visibility"
  → generates dashboard with: Revenue KPI, Margin KPI, Inventory Turnover
  Trend, Sell-out Distribution, 3-Month Revenue Forecast, Cost Correlation Matrix
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .composition_engine import DashboardCompositionEngine, DashboardDefinition
from .role_based_generator import RoleBasedDashboardGenerator
from .widget_registry import WidgetCategory, WidgetType


@dataclass
class DashboardRecommendation:
    """AI-generated dashboard recommendation with reasoning."""
    reasoning: str
    recommended_widgets: list[dict[str, Any]]
    suggested_title: str
    confidence: float
    alternative_roles: list[str]


class DashboardIntelligenceAgent:
    """AI agent that recommends dashboards based on company profile + user role."""

    def __init__(
        self,
        generator: RoleBasedDashboardGenerator | None = None,
    ) -> None:
        self.generator = generator or RoleBasedDashboardGenerator()

    def recommend(
        self,
        org_id: str,
        profile_context: dict[str, Any],
        role: str,
        user_preferences: dict[str, Any] | None = None,
    ) -> DashboardRecommendation:
        """Generate an AI recommendation with reasoning."""
        industry = profile_context.get("industry", "generic")
        kpis = profile_context.get("kpis", [])
        company_name = profile_context.get("company_identity", {}).get("name", "the company")
        ontology = profile_context.get("ontology", {})
        agents = profile_context.get("agents", [])

        # Build reasoning
        reasoning = self._build_reasoning(
            industry=industry,
            role=role,
            company_name=company_name,
            kpis=kpis,
            ontology=ontology,
            agents=agents,
        )

        # Generate dashboard
        dashboard = self.generator.generate(
            org_id=org_id,
            profile_context=profile_context,
            role=role,
            user_preferences=user_preferences,
        )

        # Extract widget recommendations
        recommended_widgets = [
            {
                "id": w.id,
                "type": w.type.value,
                "label": w.label,
                "category": w.category.value,
                "config": w.config,
                "component": DashboardDefinition._component_for(w.type),
            }
            for w in dashboard.layout
        ]

        # Suggest alternative roles that might be useful
        alt_roles = self._suggest_alternative_roles(role, industry, kpis)

        return DashboardRecommendation(
            reasoning=reasoning,
            recommended_widgets=recommended_widgets,
            suggested_title=dashboard.title,
            confidence=self._calculate_confidence(kpis, ontology, agents),
            alternative_roles=alt_roles,
        )

    def _build_reasoning(
        self,
        industry: str,
        role: str,
        company_name: str,
        kpis: list,
        ontology: dict,
        agents: list,
    ) -> str:
        role_labels = {
            "ceo": "Chief Executive Officer",
            "cfo": "Chief Financial Officer",
            "coo": "Chief Operating Officer",
            "cto": "Chief Technology Officer",
            "executive": "Executive",
            "manager": "Manager",
            "analyst": "Analyst",
        }
        role_label = role_labels.get(role.lower(), role)

        parts = [f"As the {role_label} of {company_name}"]

        if industry != "generic":
            parts.append(f"in the {industry} industry")

        kpi_names = [k.get("name", "") for k in kpis if isinstance(k, dict)]
        if kpi_names:
            parts.append(f"tracking {', '.join(kpi_names[:3])}")

        entity_names = list(ontology.get("entities", {}).keys()) if isinstance(ontology, dict) else []
        if entity_names:
            parts.append(f"with key entities: {', '.join(entity_names[:3])}")

        # Role-specific insight
        role_insights = {
            "ceo": "Strategic oversight requires top-level KPIs, goal tracking, and alert monitoring for timely decisions.",
            "cfo": "Financial visibility demands margin tracking, revenue forecasting, and KPI correlation analysis.",
            "coo": "Operational excellence needs efficiency metrics, workflow monitoring, and distribution analysis.",
            "cto": "Technology leadership requires AI agent health, knowledge graph visibility, and pipeline monitoring.",
        }
        insight = role_insights.get(role.lower(), "Balanced view across all intelligence layers.")
        parts.append(insight)

        if agents:
            agent_names = [a.get("name", "") for a in agents if isinstance(a, dict)]
            parts.append(f"Active agents: {', '.join(agent_names[:2])}.")

        return " ".join(parts) + "."

    def _calculate_confidence(self, kpis: list, ontology: dict, agents: list) -> float:
        """Confidence in the recommendation based on available profile data."""
        score = 0.0
        if kpis:
            score += min(len(kpis) / 4, 1.0) * 0.4
        if ontology and isinstance(ontology, dict) and ontology.get("entities"):
            score += 0.3
        if agents:
            score += 0.2
        score += 0.1  # base confidence
        return min(score, 1.0)

    def _suggest_alternative_roles(self, role: str, industry: str, kpis: list) -> list[str]:
        """Suggest other role views that might be useful."""
        all_roles = ["ceo", "cfo", "coo", "cto"]
        alternatives = [r for r in all_roles if r != role.lower()]
        # Prioritize based on industry
        if industry == "finance" and "cfo" in alternatives:
            alternatives.remove("cfo")
            alternatives.insert(0, "cfo")
        elif industry == "manufacturing" and "coo" in alternatives:
            alternatives.remove("coo")
            alternatives.insert(0, "coo")
        elif industry == "saas" and "cto" in alternatives:
            alternatives.remove("cto")
            alternatives.insert(0, "cto")
        return alternatives[:3]
