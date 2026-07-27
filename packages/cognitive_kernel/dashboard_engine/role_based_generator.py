"""
πX Role-Based Dashboard Generator — Generates role-specific dashboards.

CEO sees strategic KPIs, goals, alerts.
CFO sees financial metrics, forecasts, correlations.
COO sees operations, efficiency, workflows.
CTO sees AI health, knowledge graph, data pipelines.
"""
from __future__ import annotations

from typing import Any

from .composition_engine import DashboardCompositionEngine, DashboardDefinition
from .widget_registry import WidgetRegistry


class RoleBasedDashboardGenerator:
    """Generates dashboards tailored to user roles."""

    ROLES = ["ceo", "cfo", "coo", "cto", "executive", "manager", "analyst"]

    def __init__(
        self,
        composition_engine: DashboardCompositionEngine | None = None,
    ) -> None:
        self.engine = composition_engine or DashboardCompositionEngine()

    def generate(
        self,
        org_id: str,
        profile_context: dict[str, Any],
        role: str,
        user_preferences: dict[str, Any] | None = None,
    ) -> DashboardDefinition:
        """Generate a dashboard for a specific role."""
        role = role.lower()
        if role not in self.ROLES:
            role = "executive"

        return self.engine.compose(
            org_id=org_id,
            profile_context=profile_context,
            role=role,
            user_preferences=user_preferences,
        )

    def generate_all_roles(
        self,
        org_id: str,
        profile_context: dict[str, Any],
    ) -> dict[str, DashboardDefinition]:
        """Generate dashboards for all roles at once."""
        return {
            role: self.generate(org_id, profile_context, role)
            for role in self.ROLES
        }

    def get_role_config(self, role: str) -> dict[str, Any]:
        """Get the configuration for a role — which widget categories to prioritize."""
        role = role.lower()
        configs = {
            "ceo": {
                "label": "Chief Executive Officer",
                "priorities": ["executive", "intelligence"],
                "kpi_limit": 4,
                "show_forecast": False,
                "show_operations": False,
            },
            "cfo": {
                "label": "Chief Financial Officer",
                "priorities": ["executive", "analytics"],
                "kpi_limit": 4,
                "show_forecast": True,
                "show_correlation": True,
            },
            "coo": {
                "label": "Chief Operating Officer",
                "priorities": ["operations", "analytics"],
                "kpi_limit": 3,
                "show_workflow": True,
                "show_distribution": True,
            },
            "cto": {
                "label": "Chief Technology Officer",
                "priorities": ["operations", "intelligence"],
                "kpi_limit": 2,
                "show_agents": True,
                "show_graph": True,
                "show_workflows": True,
            },
            "executive": {
                "label": "Executive",
                "priorities": ["executive", "intelligence"],
                "kpi_limit": 4,
            },
            "manager": {
                "label": "Manager",
                "priorities": ["executive", "operations"],
                "kpi_limit": 3,
            },
            "analyst": {
                "label": "Analyst",
                "priorities": ["analytics", "intelligence"],
                "kpi_limit": 3,
                "show_correlation": True,
                "show_forecast": True,
            },
        }
        return configs.get(role, configs["executive"])
